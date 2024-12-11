import streamlit as st
from streamlit_searchbox import st_searchbox
from utils import *
from card_tabs import *

def get_content():
    display_toasts()
    df_decks = get_decks().assign(open=False)
    if 'current_deck_id' not in st.session_state:
        st.session_state.current_deck_id = df_decks.iloc[0].loc['deck_id']
    mask_deck = df_decks['deck_id'] == st.session_state.current_deck_id
    df_decks.loc[mask_deck, 'open'] = True

    def check_match_deck__and_set(active_tab, card_key):
        result = (st.session_state.get('v_deck_tab_bar') == active_tab) \
        and ((card_info := st.session_state.get(card_key)) is not None) \
        and (selected_set := st.session_state.get('v_selected_deck_set')) \
        and (card_info.loc['set_code'] != selected_set.split(' ')[0]) \
        and (int(card_info.loc['create_ns']) <= int(selected_set.split(' ')[-1]))
        return result
    
    if ('selected_deck_card' not in st.session_state) or \
        (
            (st.session_state.get('selected_deck_card') is not None) and
            (st.session_state.get('v_deck_tab_bar') not in ['Card overview', 'Edit card'])
        ):
            st.session_state.selected_deck_card = None
    elif check_match_deck__and_set('Edit card', 'selected_deck_card'):
        _, _, language, card_uuid, _ = st.session_state.v_selected_deck_set.split(' ')
        columns = ['language', 'card_uuid']
        values = [language, uuid.UUID(card_uuid).bytes]
        update_table_content(
            'deck', st.session_state.selected_deck_card, columns, values
        )
        st.session_state.selected_deck_card.rename('need_update', inplace=True)
        del st.session_state.v_selected_deck_set
    elif check_match_deck__and_set('Add cards', 'searched_deck_card'):
        _, _, language, card_uuid, _ = st.session_state.v_selected_deck_set.split(' ')
        st.session_state.searched_deck_card = search_set_by_name(
            'ignore_name', language, card_uuid
        ).iloc[0]
    
    with st.sidebar:
        table_container = st.container()

        def deck_callback():
            changes = [
                (ix, [(col, val) for col, val in pair.items()])
                for ix, pair in st.session_state.v_decks['edited_rows'].items()
            ]
            ix, [[col, val]]= changes[0]

            if col == 'open':
                st.session_state.current_deck_id = df_decks.iloc[ix].loc['deck_id']
            else:
                deck_id = df_decks.iloc[ix].loc['deck_id']
                st.session_state.v_deck_tab_bar = None
                st.session_state.selected_deck_card = None
                try:
                    update_table('deck', deck_id, col, val)
                except sqlite3.IntegrityError:
                        table_container.error(f'Deck {val} already exist!')

        _ = table_container.data_editor(
            df_decks, 
            key='v_decks',
            hide_index=True,
            column_config={
                'name': st.column_config.TextColumn(
                    'Deck', width='medium', help='Deck name'
                ),
                'open': st.column_config.CheckboxColumn(
                    'Open', help="Open deck"
                )
            },
            column_order=['name', 'open'],
            on_change=deck_callback
        )
        
        action = st.radio(
            label='Manage decks',
                options=('Add', 'Delete', 'Merge'),
                horizontal=True
        )
        if action == 'Add':
            with st.form('add_deck', clear_on_submit=True):
                col1, col2 = st.columns((0.7, 0.3))
                new_deck = col1.text_input('Enter new deck')
                col2.write('')
                col2.write('')
                submitted = col2.form_submit_button('Add')
                default_flag = st.checkbox('Mark as primary deck')
                if submitted and new_deck.strip() != '':
                    try:
                        add_new_record('deck', new_deck, is_default=default_flag)
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error(f'Deck {new_deck} already exist!')
        elif (action == 'Delete') and (df_decks.shape[0] > 1):
            with st.form('delete_deck', clear_on_submit=True):
                col1, col2 = st.columns((0.7, 0.3))
                deck_to_delete = col1.selectbox(
                    label='Select deck to delete',
                    options=df_decks['name'].sort_index(ascending=False)
                )
                col2.write('')
                col2.write('')
                submitted = col2.form_submit_button('Drop')
                st.warning(
                    'All cards from deleting deck will be also removed!',
                    icon='⚠️'
                )
                if submitted:
                    delete_record('deck', deck_to_delete)
                    del st.session_state.current_deck_id
                    st.rerun()
        elif (action == 'merge') and (df_decks.shape[0] > 1):
            pass #TODO merge
    
    deck_side, overview_side = st.columns((0.6, 0.4))

    with deck_side:
        df_deck_content = get_deck_content(st.session_state.current_deck_id) \
            .assign(open=False)
        card_id_cols = [
            'deck_id', 'card_uuid', 'condition_code', 'foil', 'language',
            'deck_type_name',
            'qnty', 'is_commander', 'name', 'keyrune_code', 'set_name',
            'set_code', 'card_number', 'language_code', 'create_ns'
        ]

        move_dict = {
            'Move One to Main Deck': ['One', 'Main'],
            'Move All to Main Deck': ['All', 'Main'],
            'Move One to Sideboard': ['One', 'Side'],
            'Move All to Sideboard': ['All', 'Side'],
            'Move One to Maybeboard': ['One', 'Maybe'],
            'Move All to Maybeboard': ['All', 'Maybe']
        }
        
        if st.session_state.selected_deck_card is not None:
            mask = (
                df_deck_content[card_id_cols[:6]] == \
                    st.session_state.selected_deck_card[:6]
            ).all(1)
            df_deck_content.loc[mask, 'open'] = True
            if st.session_state.selected_deck_card.name == 'need_update':
                st.session_state.selected_deck_card.name = ''
                st.session_state.selected_deck_card = df_deck_content \
                    [card_id_cols].loc[mask].iloc[0]
        
        def update_table_content_wrapper(**kwargs):
            if 'value' not in kwargs:
                # Если функция была вызвана при изменении таблицы
                table_key = eval(kwargs['table'])
                changes = [
                    (ix, [(column, value) for column, value in pair.items()])
                    for ix, pair in table_key['edited_rows'].items()
                ]
                ix, [[column, value]]= changes[0]
                card_id = kwargs['df_deck_type_content'].iloc[ix]
                if column == 'open':
                    if value == True:
                        st.session_state.selected_deck_card = card_id \
                            [card_id_cols]
                        st.session_state.v_deck_tab_bar = 'Card overview'
                    else:
                        st.session_state.selected_deck_card = None
                        st.session_state.v_deck_tab_bar = 'Deck info'
                    if 'v_selected_deck_set' in st.session_state:
                        del st.session_state.v_selected_deck_set
                    return
                elif column == 'deck_type_name':
                    amount, value = move_dict[value]
                    if 'One' in amount:
                        # Сперва добавим одну карту
                        card_id_add = card_id.copy()
                        card_id_add.loc['qnty'] = 1
                        update_table_content(
                            'deck', card_id_add, column, value
                        )
                        # Затем обновим значения для вычитания 1 карты
                        column = 'qnty'
                        card_id.loc['qnty'] -= 1
                        value = int(card_id.loc['qnty'])

                update_table_content('deck', card_id, column, value)
                if (card_id['open']) and (column == 'qnty') and (value == 0):
                    st.session_state.selected_deck_card = None
            else:
                # Если фунция была вызвана при изменении виджета
                update_table_content(**kwargs)
                if kwargs['card_id'] is st.session_state.get('selected_deck_card'):
                    st.session_state.selected_deck_card \
                        .rename('need_update', inplace=True)

        df_deck_type_info = df_deck_content \
            .groupby('deck_type_name') \
            .agg(
                total_cards=pd.NamedAgg('qnty', sum),
                distinct_cards=pd.NamedAgg('name', lambda s: s.nunique()),
                has_commander=pd.NamedAgg('is_commander', sum),
            )
        cmdr_col = st.column_config.CheckboxColumn('Cmdr', help='Commander') \
            if df_deck_type_info['has_commander'].sum() > 0 \
            else None
        def render_deck_content_by_type(type: str, alias: str):
            try:
                total_cards, distinct_cards = df_deck_type_info \
                    .loc[type].loc[['total_cards', 'distinct_cards']].to_list()
            except:
                total_cards =  distinct_cards  = 0
            
            if total_cards > 0:
                st.subheader(
                    f"{alias} - {total_cards} cards, " +
                    f"{distinct_cards} distinct",
                    divider='red'
                )
                move_options = [
                    action for action in move_dict.keys() if alias not in action
                ]
                deck_type_content = df_deck_content \
                    .loc[df_deck_content['deck_type_name'] == type]
                _ = st.data_editor(
                    deck_type_content,
                    key=f'v_deck_content_{type}',
                    hide_index=True,
                    column_config={
                        'deck_id': None,
                        'card_uuid': None,
                        'language': None,
                        'qnty': st.column_config.NumberColumn(
                            'Q', min_value=0, step=1, help='Quantity'
                        ),
                        'name': st.column_config.TextColumn(
                            'Name', help='Card name'
                        ), #TODO display in native card language
                        'card_number': None,
                        'type': st.column_config.TextColumn(
                            'Type', help='Card type'),
                        #TODO display in native card language
                        'set_code': st.column_config.TextColumn(
                            'Set', help='Set'
                        ),
                        'language_code': None,
                        'rarity': None,
                        'mana_cost': st.column_config.TextColumn(
                            'Cost', help='Mana cost'
                        ),
                        'foil': st.column_config.CheckboxColumn(
                            'Foil', help='Foil'
                        ),
                        'is_commander': cmdr_col,
                        'condition_code': None,
                        'create_ns': None,
                        'deck_type_name': st.column_config.SelectboxColumn(
                            'Move to', options=move_options, help='Move card'
                        ),
                        'open': st.column_config.CheckboxColumn(
                            'Open', help='Open card'
                        )
                    },
                    column_order=[
                        'qnty', 'is_commander', 'name','type', 'set_code',
                        'mana_cost', 'foil', 'deck_type_name', 'open'
                    ],
                    disabled=[
                        'name', 'type', 'language_code', 'set_code', 'rarity', 
                        'mana_cost', 'foil', 'is_commander', 'condition_code'
                    ],
                    on_change=update_table_content_wrapper,
                    kwargs={
                        'df_deck_type_content': deck_type_content,
                        'card_id_cols': card_id_cols,
                        'table': f'st.session_state.v_deck_content_{type}'
                    }
                )
            else:
                st.write('')
        render_deck_content_by_type('Main', 'Main Deck')
        render_deck_content_by_type('Side', 'Sideboard')
        render_deck_content_by_type('Maybe', 'Maybeboard')
    with overview_side:

        deck_name, creation_dtm, note, player_id, owner, \
        is_wish_deck = df_decks \
            .loc[
                mask_deck,
                [
                    'name', 'creation_date', 'note', 'player_id', 'owner',
                    'is_wish_deck'
                ]
            ] \
            .values.ravel()
        
        def update_table_wrapper(**kwargs):
            try:
                update_table(**kwargs)
            except sqlite3.IntegrityError:
                deck_name_container.error(
                    f'Deck {st.session_state.v_deck_name} already exist!'
                )
                st.session_state.v_deck_name = deck_name
        
        deck_name_container = st.container()
        _ = deck_name_container.text_input(
            'Deck name:',
            value=deck_name,
            key='v_deck_name',
            on_change=update_table_wrapper,
            kwargs={
                'entity': 'deck',
                'default_value': None,
                'id': st.session_state.current_deck_id,
                'column': 'name',
                'value': 'st.session_state.v_deck_name'
            }
        )

        deck_tabs = ['Deck info', 'Add cards']
        default_tab = 'Deck info'
        if st.session_state.selected_deck_card is not None:
            deck_tabs += ['Card overview', 'Edit card']
            default_tab = 'Card overview'
        deck_active_tab = show_tab_bar(
            deck_tabs,
            tabs_size=[1, 1, 1, 1],
            default=default_tab,
            key='v_deck_tab_bar'
        )

        if deck_active_tab == 'Deck info':
            col_owner, col_creation_date, col_wish_deck = \
                st.columns([0.4, 0.3, 0.3])
            df_players = get_players()[['player_id', 'name']]
            if owner is not None:
                idx = int(
                    df_players[
                        df_players['player_id'] == player_id
                    ].index[0]
                )
            else:
                idx = None
            _ = col_owner.selectbox(
                'Owner:',
                options=df_players['player_id'],
                format_func=lambda x: dict(df_players.values)[x],
                index=idx,
                key='v_deck_owner',
                placeholder='Choose owner',
                on_change=update_table_wrapper,
                kwargs={
                    'entity': 'deck',
                    'default_value': None,
                    'id': st.session_state.current_deck_id,
                    'column': 'player_id',
                    'value': 'st.session_state.v_deck_owner'
                }
            )

            _ = col_creation_date.date_input(
                'Creation date:',
                value=creation_dtm.to_pydatetime(),
                format="DD.MM.YYYY",
                key='v_deck_creation_date',
                on_change=update_table_wrapper,
                kwargs={
                    'entity': 'deck',
                    'default_value': None,
                    'id': st.session_state.current_deck_id,
                    'column': 'creation_date',
                    'value': 'st.session_state.v_deck_creation_date'
                }
            )

            col_wish_deck.write('')
            col_wish_deck.write('')
            _ = col_wish_deck.checkbox(
                'Mark as wish deck',
                value=is_wish_deck,
                key='v_is_wish_deck',
                on_change=update_table_wrapper,
                kwargs={
                    'entity': 'deck',
                    'id': st.session_state.current_deck_id,
                    'column': 'is_wish_deck',
                    'value': 'int(st.session_state.v_is_wish_deck)'
                }
            )

            _ = st.text_area(
                'Deck note',
                value=note,
                key='v_deck_note',
                placeholder='Add your notes here',
                max_chars=256,
                height=10,
                on_change=update_table_wrapper,
                kwargs={
                    'entity': 'deck',
                    'id': st.session_state.current_deck_id,
                    'column': 'note',
                    'value': 'st.session_state.v_deck_note'
                }
            )

        if deck_active_tab == 'Add cards':
            search_bar, exact_seach_box = st.columns((0.7, 0.3))

            def reset_searchbar():
                del st.session_state.v_searched_deck_card

            exact_match = exact_seach_box.checkbox(
                'Exact match',
                value=False,
                on_change=reset_searchbar
            )
            searh_function = to_lower_and_exact_search if exact_match \
                else to_lower_and_substring_search
            with search_bar:
                searched_deck_card = st_searchbox(
                    search_function=searh_function,
                    placeholder="Enter card name",
                    key="v_searched_deck_card",
                    clearable=True
                )
            
            img_col, prop_col = st.columns((0.5, 0.5))
            if searched_deck_card:
                # Workaround for realize callback function in serchbox
                # We want to know, when widget value has changed
                is_new_search = False
                if st.session_state.get('prev_searched_deck_card', []) != searched_deck_card:
                    is_new_search = True
                    st.session_state.prev_searched_deck_card = searched_deck_card
                
                with prop_col:
                    if ('searched_deck_card' in st.session_state and
                        not is_new_search):
                        render_card_prop_tab(
                            'deck',
                            st.session_state.searched_deck_card,
                            update_searched_card
                        )
                    else:
                        render_card_prop_tab(
                            'deck',
                            searched_deck_card,
                            update_searched_card
                        )
                    add_cards_form = st.form('add cards')
                
                with img_col:
                    card_api_key = st.session_state.searched_deck_card \
                        .loc[['set_code', 'card_number', 'language_code']] \
                        .to_list()
                    card_props = get_card_properties(*card_api_key)
                    _ = render_card_img_tab(card_props)
                
                with add_cards_form:
                    card_uuid, deck_type_name, \
                    condition_code, foil, language = \
                        st.session_state.searched_deck_card \
                            .loc[['card_uuid', 'deck_type_name',
                                    'condition_code', 'foil', 'language']]
                    
                    current_qnty = df_deck_content[
                            (df_deck_content['card_uuid'] == card_uuid) &
                            (df_deck_content['deck_type_name'] == deck_type_name) &
                            (df_deck_content['condition_code'] == condition_code) &
                            (df_deck_content['foil'] == foil) &
                            (df_deck_content['language'] == language)
                        ] \
                        ['qnty'].sum()
                    
                    qnty = st.number_input(
                        label='Enter quantity:',
                        value=max(current_qnty, 1),
                        min_value=1, max_value=99, step=1
                    )
                    st.write('')
                    if st.form_submit_button('Update deck'):
                        st.session_state.searched_deck_card['deck_id'] = \
                            st.session_state.current_deck_id
                        st.session_state.searched_deck_card['qnty'] = qnty
                        update_table_content(
                            'deck', st.session_state.searched_deck_card,
                            'qnty', qnty
                        )
                        st.rerun()

        if deck_active_tab in deck_tabs[2:]:
            img_col, prop_col =  st.columns((0.5, 0.5))
            card_api_key = st.session_state.selected_deck_card \
                .loc[['set_code', 'card_number', 'language_code']] \
                .to_list()
            card_props = get_card_properties(*card_api_key)
            with img_col:
                side_idx = render_card_img_tab(card_props)
            if deck_active_tab == 'Card overview':
                text_field = get_card_description(card_props, side_idx)
                prop_col.markdown(text_field)
            if deck_active_tab == 'Edit card':
                _ = prop_col.selectbox(
                    'Deck:',
                    options=df_decks['deck_id'],
                    format_func=lambda x: dict(
                        df_decks[['deck_id', 'name']].values
                    )[x],
                    index=int(df_decks[
                        df_decks['deck_id'] == st.session_state.current_deck_id
                        ].index[0]
                    ),
                    key='v_card_deck',
                    on_change=update_table_content_wrapper,
                    kwargs={
                        'entity': 'deck',
                        'card_id': st.session_state.selected_deck_card,
                        'column': 'deck_id',
                        'value': 'st.session_state.v_card_deck',
                    }
                )
                with prop_col:
                    render_card_prop_tab(
                        'deck',
                        st.session_state.selected_deck_card,
                        update_table_content_wrapper
                    )





