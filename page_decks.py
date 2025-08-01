import streamlit as st
from streamlit_searchbox import st_searchbox
import widgets
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
        result = (st.session_state.get('w_deck_tab_bar') == active_tab) \
        and ((card_info := st.session_state.get(card_key)) is not None) \
        and (selected_set := st.session_state.get('w_selected_deck_set')) \
        and (card_info.loc['set_code'] != selected_set.split(' ')[0]) \
        and (int(card_info.loc['create_ns']) <= int(selected_set.split(' ')[-1]))
        return result
    
    if ('selected_deck_card' not in st.session_state) or \
        (
            (st.session_state.get('selected_deck_card') is not None) and
            (st.session_state.get('w_deck_tab_bar') not in ['Card info', 'Edit card'])
        ):
            st.session_state.selected_deck_card = None
    elif check_match_deck__and_set('Edit card', 'selected_deck_card'):
        _, _, language, card_uuid, _ = st.session_state.w_selected_deck_set.split(' ')
        columns = ['language', 'card_uuid']
        values = [language, uuid.UUID(card_uuid).bytes]
        update_table_content(
            'deck', columns, values, st.session_state.selected_deck_card
        )
        st.session_state.selected_deck_card.rename('need_update', inplace=True)
        del st.session_state.w_selected_deck_set
    elif check_match_deck__and_set('Add cards', 'searched_deck_card'):
        _, _, language, card_uuid, _ = st.session_state.w_selected_deck_set.split(' ')
        st.session_state.searched_deck_card = search_set_by_name(
            'ignore_name', language, card_uuid
        ).iloc[0]
    
    with st.sidebar:
        table_container = st.container()

        def deck_callback():
            changes = [
                (ix, [(col, val) for col, val in pair.items()])
                for ix, pair in st.session_state.w_decks['edited_rows'].items()
            ]
            ix, [[col, val]]= changes[0]

            if col == 'open':
                st.session_state.current_deck_id = df_decks.iloc[ix].loc['deck_id']
            else:
                deck_id = df_decks.iloc[ix].loc['deck_id']
                st.session_state.w_deck_tab_bar = None
                st.session_state.selected_deck_card = None
                try:
                    update_table('deck', col, val, deck_id)
                except sqlite3.IntegrityError:
                        table_container.error(f'Deck {val} already exist!')

        _ = table_container.data_editor(
            df_decks, 
            key='w_decks',
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
                        st.session_state.w_deck_tab_bar = 'Card info'
                    else:
                        st.session_state.selected_deck_card = None
                        st.session_state.w_deck_tab_bar = 'Deck info'
                    if 'w_selected_deck_set' in st.session_state:
                        del st.session_state.w_selected_deck_set
                    return
                elif column == 'deck_type_name':
                    amount, value = move_dict[value]
                    if 'One' in amount:
                        # Сперва добавим одну карту
                        card_id_add = card_id.copy()
                        card_id_add.loc['qnty'] = 1
                        update_table_content('deck', column, value, card_id_add)
                        # Затем обновим значения для вычитания 1 карты
                        column = 'qnty'
                        card_id.loc['qnty'] -= 1
                        value = int(card_id.loc['qnty'])

                update_table_content('deck', column, value, card_id)
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
                    key=f'w_deck_content_{type}',
                    hide_index=True,
                    column_config={
                        'deck_id': None,
                        'card_uuid': None,
                        'language': None,
                        'qnty': st.column_config.NumberColumn(
                            'QNTY', help='Quantity',
                        ),
                        'name': st.column_config.TextColumn(
                            'Name', help='Card name', width='medium'
                        ),
                        'card_number': None,
                        'type': st.column_config.TextColumn(
                            'Type', help='Card type', width='medium'
                        ),
                        'set_code': st.column_config.TextColumn(
                            'Set', help='Set'
                        ),
                        'language_code': None,
                        'rarity': None,
                        'mana_cost': st.column_config.TextColumn(
                            'Cost', help='Mana cost'
                        ),
                        'foil': None,
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
                        'is_commander', 'name','type', 'set_code',
                        'mana_cost', 'deck_type_name', 'qnty', 'open'
                    ],
                    disabled=[
                        col for col in deck_type_content.columns
                        if col not in ['open', 'deck_type_name']
                    ],
                    on_change=update_table_content_wrapper,
                    kwargs={
                        'df_deck_type_content': deck_type_content,
                        'card_id_cols': card_id_cols,
                        'table': f'st.session_state.w_deck_content_{type}'
                    }
                )
            else:
                st.write('')
        render_deck_content_by_type('Main', 'Main Deck')
        render_deck_content_by_type('Side', 'Sideboard')
        render_deck_content_by_type('Maybe', 'Maybeboard')
    with overview_side:

        def update_table_wrapper(**kwargs):
            try:
                update_table(**kwargs)
            except sqlite3.IntegrityError:
                deck_name_container.error(
                    f'Deck {st.session_state.w_deck_name} already exist!'
                )
                st.session_state.w_deck_name = selected_deck['name']
        
        default_args = {
            'entity':'deck', 'callback_function':update_table_wrapper,
            'index_id':st.session_state.current_deck_id,
        }
        selected_deck = df_decks \
            .loc[
                mask_deck,
                ['name', 'creation_date', 'note', 'player_id', 'is_wish']
            ] \
            .iloc[0].to_dict()
        
        
        deck_name_container = st.container()
        render_entity_header(
            deck_name_container, **default_args, **selected_deck
        )

        deck_tabs = ['Deck info', 'Deck builder', 'Add cards']
        default_tab = 'Deck info'
        if st.session_state.selected_deck_card is not None:
            deck_tabs += ['Card info', 'Edit card']
            default_tab = 'Card info'
        deck_active_tab = show_tab_bar(
            deck_tabs,
            tabs_size=[1, 1.2, 1, 1, 1],
            default=default_tab,
            key='w_deck_tab_bar'
        )

        if deck_active_tab == 'Deck info':
            render_entity_prop_tab(**default_args,**selected_deck)

        if deck_active_tab == 'Deck builder':
            color_map = {
                'W': ":material/sunny:",
                'G': ":material/nature:",
                'R': ":material/local_fire_department:",
                'U': ":material/water_drop:",
                'B': ":material/skull:",
                'C': ":material/stat_0:",
                'X': ":material/counter_9:"
            }
            rarity_map = {
                'common': "**:gray-background[C]**",
                'uncommon': "**:blue-background[U]**",
                'rare': "**:orange-background[R]**",
                'mythic': "**:red-background[M]**",
                'special': "**:rainbow-background[S]**"
 
            }
            search_params = {}
            with st.expander(
                'Search options',
                expanded=st.session_state.get('expand_search_form', True),
                icon=":material/manage_search:"
            ):
                search_form = st.form('search_form', border=False)
            pills_col, multicolor_col = search_form.columns([0.5, 0.5])
            search_params['color_list'] = pills_col.pills(
                'Mana cost colors:',
                options=color_map.keys(),
                selection_mode='multi',
                format_func=lambda option_key: color_map[option_key],
                help='White, Green, Red, Blue, Black, Colorless, No color'
            )
            search_params['multicolor_option'] = multicolor_col.selectbox(
                label='Color options:',
                options=[
                    'With a chosen color(s)',
                    'Any of the chosen color(s)',
                    'All of the chosen color(s)'
                ]
            )

            search_params['rarity_list'] = pills_col.segmented_control(
                'Card rarity:',
                options=rarity_map.keys(),
                selection_mode='multi',
                format_func=lambda option_key: rarity_map[option_key],
                help='Common, Uncommon, Rare, Mythic, Special'
            )

            text_col, _, op_col, val_col = search_form \
                .columns([0.48, 0.02, 0.25, 0.25])

            search_params['card_name'] = text_col.text_input('Card name:')
            search_params['card_type'] = text_col.text_input('Card type:')
            search_params['card_text'] = text_col.text_input('Card text:')

            operators = ['>=', '>', '=', '<', '<=']
            search_params['mana_value_op'] = op_col.selectbox(
                'CMC', operators, key='w_mana_value_op'
            )
            search_params['mana_value_val'] = val_col.number_input(
                'value', value=None, step=1, key='w_mana_value_val'
            )
            search_params['power_op'] = op_col.selectbox(
                'Power', operators, key='w_power_op'
            )
            search_params['power_val'] = val_col.number_input(
                'value', value=None, step=1, key='w_power_val'
            )
            search_params['toughness_op'] = op_col.selectbox(
                'Toughness', operators, key='w_toughness_op'
            )
            search_params['toughness_val'] = val_col.number_input(
                'value', value=None, step=1, key='w_toughness_val'
            )
            
            def _close_expander():
                st.session_state.expand_search_form = False

            search_button = search_form.form_submit_button(
                'Search',
                on_click=_close_expander,
                icon=":material/search:"
            )
            
            if search_button or 'search_result_card' in st.session_state:
                df_search_result = search_cards(search_params) \
                    .assign(open=False)
                if 'search_result_card' in st.session_state:
                    mask = (
                        df_search_result['name'] == \
                            st.session_state.search_result_card['name']
                    )
                    df_search_result.loc[mask, 'open'] = True
                def search_result_callback():
                    changes = [
                        (ix, [(col, val) for col, val in pair.items()])
                        for ix, pair in st.session_state.w_search_result['edited_rows'].items()
                    ]
                    ix, [[col, val]]= changes[0]

                    if col == 'open':
                        st.session_state.search_result_card = df_search_result.iloc[ix]
                    else:
                        st.session_state.search_result_card = None

                _ = st.data_editor(
                    df_search_result, 
                    key='w_search_result',
                    hide_index=True,
                    column_config={
                        'name': st.column_config.TextColumn(
                            'Name', width='medium', help='Deck name'
                        ),
                        'type': st.column_config.TextColumn(
                            'Type', width='medium',help='Card type'
                        ),
                        'mana_cost': st.column_config.TextColumn(
                            'Cost', help='Mana cost'
                        ),
                        'pt': st.column_config.TextColumn(
                            'P / T', help='Power / Toughness'
                        ),
                        'create_ns': None,
                        'open': st.column_config.CheckboxColumn(
                            'Open', help="Open collections"
                        )
                    },
                    disabled=[c for c in df_search_result.columns if c != 'open'],
                    on_change=search_result_callback
                )
                if 'search_result_card' in st.session_state:
                    df_lists = search_cards_in_lc(
                        st.session_state.search_result_card['name']
                    )
                    st.dataframe(df_lists.assign(Add=False))

        if deck_active_tab == 'Add cards':
            search_bar, exact_seach_box = st.columns((0.7, 0.3))

            def reset_searchbar():
                del st.session_state.w_searched_deck_card

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
                    key="w_searched_deck_card",
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
                            'deck', 'qnty', qnty,
                            st.session_state.searched_deck_card
                        )
                        st.rerun()

        if deck_active_tab in deck_tabs[3:]:
            img_col, prop_col =  st.columns((0.5, 0.5))
            card_api_key = st.session_state.selected_deck_card \
                .loc[['set_code', 'card_number', 'language_code']] \
                .to_list()
            card_props = get_card_properties(*card_api_key)
            with img_col:
                side_idx = render_card_img_tab(card_props)
            if deck_active_tab == 'Card info':
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
                    key='w_card_deck',
                    on_change=update_table_content_wrapper,
                    kwargs={
                        'entity': 'deck',
                        'column': 'deck_id',
                        'value': 'st.session_state.w_card_deck',
                        'card_id': st.session_state.selected_deck_card
                    }
                )
                with prop_col:
                    render_card_prop_tab(
                        'deck',
                        st.session_state.selected_deck_card,
                        update_table_content_wrapper
                    )



