import streamlit as st
from utils import *

def get_content():
    display_toasts()

    df_decks = get_decks().assign(open=False)
    if 'current_deck_id' not in st.session_state:
        st.session_state.current_deck_id = df_decks.iloc[0].loc['deck_id']
    mask_list = df_decks['deck_id'] == st.session_state.current_deck_id
    df_decks.loc[mask_list, 'open'] = True

    if 'selected_deck_card' not in st.session_state:
        st.session_state.selected_deck_card = None
    
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
                try:
                    update_table('deck', None, deck_id, col, val)
                except sqlite3.IntegrityError:
                        table_container.error(f'Deck {val} already exist!')

        _ = table_container.data_editor(
            df_decks, 
            key='v_decks',
            hide_index=True,
            column_config={
                'name': 'Deck',
                'open': st.column_config.CheckboxColumn('Open')
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
                if submitted and new_deck.strip() != '':
                    try:
                        add_new_record('deck', new_deck)
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
                if submitted:
                    delete_record('list', deck_to_delete)
                    del st.session_state.current_deck_id
                    st.rerun()
    list_side, overview_side = st.columns((0.6, 0.4))

    with list_side:
        df_deck_content = get_deck_content(st.session_state.current_deck_id) \
            .assign(open=False)
        card_cols = [
            'deck_id', 'card_uuid', 'condition_code', 'foil', 'language', 'deck_type_name'
            'qnty',
            'set_code', 'card_number', 'language_code'
        ]
        card_id_cols = card_cols[:6]
        card_api_cols = card_cols[-3:]
        if st.session_state.selected_deck_card is not None:
            mask = (df_deck_content[card_id_cols] == st.session_state.selected_deck_card).all(1)
            df_deck_content.loc[mask, 'open'] = True
        
        def update_table_content_wrapper(**kwargs):
            if 'value' not in kwargs:
                # Если функция была вызвана при изменении таблицы
                changes = [
                    (ix, [(column, value) for column, value in pair.items()])
                    for ix, pair in st.session_state.v_deck_content['edited_rows'].items()
                ]
                ix, [[column, value]]= changes[0]
                if column == 'open':
                    if value == True:
                        st.session_state.selected_deck_card = df_deck_content[
                            card_id_cols
                        ].iloc[ix]
                    else:
                        st.session_state.selected_deck_card = None
                    return
                update_table_content('deck', df_deck_content.iloc[ix], column, value)
            else:
                # Если фунция была вызвана при изменении виджета
                update_table_content(**kwargs)
        
        _ = st.data_editor(
            df_deck_content,
            key='v_deck_content',
            hide_index=True,
            column_config={
                'deck_id': None,
                'deck_type_name': 'Deck type',
                'card_uuid': None,
                'language': None,
                'qnty': st.column_config.NumberColumn(
                    'Qnty', min_value=0, max_value=99, step=1
                ),
                'name': 'Name', #TODO display in native card language
                'card_number': None,
                'type': 'Type', #TODO display in native card language
                'language_code': None,
                'set_code': None,
                'rarity': None,
                'mana_cost': 'Cost',
                'foil': st.column_config.CheckboxColumn('Foil'),
                'condition_code': 'Cond',
                'create_ns': None,
                'open': st.column_config.CheckboxColumn('Open'),
            },
            disabled=[
                'name', 'type', 'language_code', 'set_code', 'rarity', 
                'mana_cost', 'foil', 'condition_code']
            ,
            on_change=update_table_content_wrapper
        )
    with overview_side:
        deck_tabs =['Deck & cards overview', 'Add cards']
        deck_active_tab = show_tab_bar(deck_tabs)
        if deck_active_tab == deck_tabs[0]:
            deck_name, creation_dtm, note, player_id, owner = df_decks \
                .loc[
                    mask_list,
                    ['name', 'creation_date', 'note', 'player_id', 'owner']
                ] \
                .values.ravel()
            col_deck_name, col_owner, col_creation_date, col_counter =  \
                st.columns((0.3, 0.3, 0.2, 0.15))
            
            def update_table_wrapper(**kwargs):
                try:
                    update_table(**kwargs)
                except sqlite3.IntegrityError:
                    deck_info_container.error(
                        f'Deck {st.session_state.v_deck_name} already exist!'
                    )
                    st.session_state.v_deck_name = deck_name
            
            _ = col_deck_name.text_input(
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

            _ = col_counter.text_input(
                'Cards total:',
                value=df_deck_content['qnty'].sum(),
                disabled=True
            )

            deck_info_container = st.container()
            deck_info_container.text_area(
                'Deck note',
                value=note,
                key='v_deck_note',
                placeholder='Add your notes here',
                max_chars=256,
                height=10,
                on_change=update_table_wrapper,
                kwargs={
                    'entity': 'deck',
                    'default_value': None,
                    'id': st.session_state.current_deck_id,
                    'column': 'note',
                    'value': 'st.session_state.v_deck_note'
                }
            )
        if st.session_state.selected_deck_card is not None:

            card_tabs =['Card overview', 'Edit card']
            card_active_tab = show_tab_bar(card_tabs)
            img_col, prop_col =  st.columns((0.5, 0.5))
            card_api_key = [val for val in st.session_state.selected_deck_card[6:].values]
            card_props = get_card_properties(*card_api_key)
            img_container = img_col.container()
            if card_props.get('card_faces'):
                side = img_col.radio(
                    'no label',
                    ['Front', 'Back'],
                    label_visibility='collapsed', 
                    horizontal=True
                )
                ix = 0 if side == 'Front' else 1
                img_container.image(card_props['card_faces'][ix]['image_uris']['normal'])
            else:
                ix = -1
                img_container.image(card_props['image_uris']['normal'])
            if card_active_tab == card_tabs[0]:
                def get_card_prop(props_dict, prop_name, side_ix):
                    value = props_dict.get(
                        prop_name, 
                        card_props.get('card_faces', [{}])[side_ix].get(prop_name, None)
                    )
                    return value
                if get_card_prop(card_props, 'power', ix):
                    power = get_card_prop(card_props, 'power', ix)
                    toughness = get_card_prop(card_props, 'toughness', ix)
                    card_props['P/T'] =  \
                        f'{power}/{toughness}'
                list_legalities = [
                    'standard', 'pioneer', 'modern', 'legacy', 
                    'vintage', 'commander', 'pauper', 'historic', 'alchemy'
                ]
                legalities = ''
                for legality in list_legalities:
                    if card_props['legalities'][legality] == 'legal':
                        legalities += (f'{legality}, '.capitalize())
                card_props['Legalities_only'] = legalities[:-2]
                props_aliases = [
                    ('name', 'Card Name'), ('mana_cost', 'Mana Cost'),
                    ('cmc', 'Mana Value'), ('type_line', 'Types'),
                    ('oracle_text', 'Card text'), ('flavor_text', 'Flavor Text'),
                    ('P/T', 'P/T'), ('rarity', 'Rarity'),
                    ('collector_number', 'Card Number'), ('artist', 'Artist'),
                    ('set_name', 'Set Name'), ('released_at', 'Release'),
                    ('Legalities_only', 'Legalities')
                ]

                text_field = ''
                for property, alias in props_aliases:
                    property_value = get_card_prop(card_props, property, ix)
                    if property_value:
                        text_field += f"""**{alias}**:&nbsp;&nbsp;{property_value}  \n"""
                
                prop_col.markdown(text_field)
            if card_active_tab == card_tabs[1]:
                _ = prop_col.selectbox(
                    'Collection:',
                    options=df_decks['deck_id'],
                    format_func=lambda x: dict(
                        df_decks[['deck_id', 'name']].values
                    )[x],
                    index=int(df_decks[
                        df_decks['deck_id'] == st.session_state.current_deck_id
                        ].index[0]
                    ),
                    key='v_card_list',
                    on_change=update_table_content_wrapper,
                    kwargs={
                        'entity': 'deck',
                        'card_id': st.session_state.selected_deck_card,
                        'column': 'deck_id',
                        'value': 'st.session_state.v_card_list',

                    }
                )
                _ = prop_col.selectbox(
                    'Language:',
                    key='v_card_language'
                )
                prop_col.text('Set:')
                #TODO panel of set icons
                _ = prop_col.radio(
                    'Card number:',
                    horizontal=True
                )
                _ = prop_col.toggle('Foil')
                _ = prop_col.selectbox(
                    'Condition:',
                    key='v_card_condition'
                )





