import streamlit as st
from utils import *

def get_content():
    display_toasts()

    df_lists = get_lists().assign(open=False)
    if 'current_list_id' not in st.session_state:
        st.session_state.current_list_id = df_lists.iloc[0].loc['list_id']
    mask_list = df_lists['list_id'] == st.session_state.current_list_id
    df_lists.loc[mask_list, 'open'] = True

    if 'selected_card' not in st.session_state:
        st.session_state.selected_card = None
        st.session_state.active_expander = 'list_info'
    
    with st.sidebar:
        table_container = st.container()

        def list_callback():
            changes = [
                (ix, [(col, val) for col, val in pair.items()])
                for ix, pair in st.session_state.v_lists['edited_rows'].items()
            ]
            ix, [[col, val]]= changes[0]
            if col == 'open':
                st.session_state.current_list_id = df_lists.iloc[ix].loc['list_id']
            elif not ((col == 'is_default_list') and (val is False)):
                default_list = df_lists.iloc[ix].loc['name']
                list_id = df_lists.iloc[ix].loc['list_id']
                try:
                    update_table(
                        'list', list_id, col, val, default_value=default_list
                    )
                except sqlite3.IntegrityError:
                     table_container.error(f'Collection {val} already exist!')  

        _ = table_container.data_editor(
            df_lists, 
            key='v_lists',
            hide_index=True,
            column_config={
                'name': 'Collection',
                'is_default_list': st.column_config.CheckboxColumn('Default'),
                'open': st.column_config.CheckboxColumn('Open'),
            },
            column_order=['name', 'is_default_list', 'open'],
            on_change=list_callback
        )
        
        action = st.radio(
            label='Add / delete collection',
                options=('Add', 'Delete'),
                horizontal=True
        )
        if action == 'Add':
            with st.form('add_list', clear_on_submit=True):
                col1, col2 = st.columns((0.7, 0.3))
                new_list = col1.text_input('Enter new collection')
                col2.write('')
                col2.write('')
                submitted = col2.form_submit_button('Add')
                default_flag = st.checkbox('Set as default collection')
                if submitted and new_list.strip() != '':
                    try:
                        add_new_record('list', new_list, is_default=default_flag)
                        st.experimental_rerun()
                    except sqlite3.IntegrityError:
                        st.error(f'Collection {new_list} already exist!')
        elif (action == 'Delete') and (df_lists.shape[0] > 1):
            with st.form('delete_list', clear_on_submit=True):
                col1, col2 = st.columns((0.7, 0.3))
                deleted_list = col1.selectbox(
                    label='Select collection to delete',
                    options=df_lists['name'].sort_index(ascending=False)
                )
                col2.write('')
                col2.write('')
                submitted = col2.form_submit_button('Drop')
                st.write('All cards from deleting collection will be also removed!')
                if submitted:
                    delete_record('list', deleted_list)
                    del st.session_state.current_list_id
                    st.experimental_rerun()
    list_side, overview_side = st.columns((0.6, 0.4))

    with list_side:
        df_list_content = get_list_content(st.session_state.current_list_id).assign(open=False)
        card_id_cols = [
            'list_id', 'card_uuid', 'condition_code', 'foil', 'language',
            'qnty', 'name',
            'set_code', 'card_number', 'language_code'
        ]
        if st.session_state.selected_card is not None:
            mask = (df_list_content[card_id_cols[:5]] == st.session_state.selected_card[:5]).all(1)
            df_list_content.loc[mask, 'open'] = True
        
        def update_table_content_wrapper(**kwargs):
            if 'value' not in kwargs:
                # Если функция была вызвана при изменении таблицы
                changes = [
                    (ix, [(column, value) for column, value in pair.items()])
                    for ix, pair in st.session_state.v_list_content['edited_rows'].items()
                ]
                ix, [[column, value]]= changes[0]
                if column == 'open':
                    if value == True:
                        st.session_state.selected_card = df_list_content[
                            card_id_cols
                        ].iloc[ix]
                    else:
                        st.session_state.selected_card = None
                    return
                update_table_content('list', df_list_content.iloc[ix], column, value)
            else:
                # Если фунция была вызвана при изменении виджета
                update_table_content(**kwargs)
        
        _ = st.data_editor(
            df_list_content,
            key='v_list_content',
            height=843,
            hide_index=True,
            column_config={
                'list_id': None,
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

        collection_tabs =[
            'Collection & cards overview', 'Add cards'
        ]
        collection_active_tab = show_tab_bar(collection_tabs)
        if collection_active_tab == collection_tabs[0]:
            list_name, creation_dtm, note, player_id, owner = df_lists \
                .loc[
                    mask_list,
                    ['name', 'creation_date', 'note', 'player_id', 'owner']
                ] \
                .values.ravel()
            col_list_name, col_owner, col_creation_date, col_counter =  \
                st.columns((0.3, 0.3, 0.2, 0.15))
            
            def update_table_wrapper(**kwargs):
                try:
                    update_table(**kwargs)
                except sqlite3.IntegrityError:
                    list_info_container.error(
                        f'Collection {st.session_state.v_list_name} already exist!'
                    )
                    st.session_state.v_list_name = list_name
            
            _ = col_list_name.text_input(
                'Collection name:',
                value=list_name,
                key='v_list_name',
                on_change=update_table_wrapper,
                kwargs={
                    'entity': 'list',
                    'id': st.session_state.current_list_id,
                    'column': 'name',
                    'value': 'st.session_state.v_list_name'
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
                key='v_list_owner',
                placeholder='Choose owner',
                on_change=update_table_wrapper,
                kwargs={
                    'entity': 'list',
                    'id': st.session_state.current_list_id,
                    'column': 'player_id',
                    'value': 'st.session_state.v_list_owner'
                }
            )

            _ = col_creation_date.date_input(
                'Creation date:',
                value=creation_dtm.to_pydatetime(),
                format="DD.MM.YYYY",
                key='v_creation_date',
                on_change=update_table_wrapper,
                kwargs={
                    'entity': 'list',
                    'id': st.session_state.current_list_id,
                    'column': 'creation_date',
                    'value': 'st.session_state.v_creation_date'
                }
            )

            _ = col_counter.text_input(
                'Cards total:',
                value=df_list_content['qnty'].sum(),
                disabled=True
            )

            list_info_container = st.container()
            list_info_container.text_area(
                'Collection note',
                value=note,
                key='v_list_note',
                placeholder='Add your notes here',
                max_chars=256,
                height=10,
                on_change=update_table_wrapper,
                kwargs={
                    'entity': 'list',
                    'id': st.session_state.current_list_id,
                    'column': 'note',
                    'value': 'st.session_state.v_list_note'
                }
            )
        if st.session_state.selected_card is not None:

            card_tabs =['Card overview', 'Edit card']
            card_active_tab = show_tab_bar(card_tabs)
            img_col, prop_col =  st.columns((0.5, 0.5))
            card_api_key = [val for val in st.session_state.selected_card[-3:].values]
            card_props = get_card_properties(*card_api_key)
            img_container = img_col.container()
            if card_props.get('card_faces'):
                labels = ['First', 'Second'] if card_props.get('image_uris') \
                     else ['Front', 'Back']
                side = img_col.radio(
                    'no label',
                    labels,
                    label_visibility='collapsed', 
                    horizontal=True
                )
                ix = 0 if side in ['Front', 'First'] else 1
                img_uri = card_props \
                    .get('card_faces', [{}])[ix] \
                        .get('image_uris', {}) \
                            .get(
                                'normal',
                                card_props.get('image_uris', {}).get('normal')
                            )
                img_container.image(img_uri)
            else:
                ix = -1
                img_container.image(card_props['image_uris']['normal'])
            if card_active_tab == card_tabs[0]:
                def get_card_prop(props_dict, prop_name, side_ix):
                    value = props_dict \
                        .get('card_faces', [{}])[side_ix] \
                            .get(prop_name, props_dict.get(prop_name)
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
                    ('oracle_text', 'Card Text'), ('flavor_text', 'Flavor Text'),
                    ('P/T', 'P/T'), ('rarity', 'Rarity'),
                    ('collector_number', 'Card Number'), ('artist', 'Artist'),
                    ('set_name', 'Set Name'), ('released_at', 'Release'),
                    ('Legalities_only', 'Legalities')
                ]

                text_field = ''
                for property, alias in props_aliases:
                    property_value = get_card_prop(card_props, property, ix)
                    if property_value:
                        if 'Text' in alias:
                            property_value = property_value.replace('\n', '  \n')
                        text_field += f"""**{alias}**:&nbsp;&nbsp;{property_value}  \n"""
                
                prop_col.markdown(text_field)
            if card_active_tab == card_tabs[1]:
                _ = prop_col.selectbox(
                    'Collection:',
                    options=df_lists['list_id'],
                    format_func=lambda x: dict(
                        df_lists[['list_id', 'name']].values
                    )[x],
                    index=int(df_lists[
                        df_lists['list_id'] == st.session_state.current_list_id
                        ].index[0]
                    ),
                    key='v_card_list',
                    on_change=update_table_content_wrapper,
                    kwargs={
                        'entity': 'list',
                        'card_id': st.session_state.selected_card,
                        'column': 'list_id',
                        'value': 'st.session_state.v_card_list',
                    }
                )
                prop_col.text('Set:')
                #TODO panel of set icons
                _ = prop_col.selectbox(
                    'Language:',
                    key='v_card_language',
                    options=search_languages_by_card_name(
                        st.session_state.selected_card.loc['card_uuid'].hex()
                    ),
                    on_change=update_table_content_wrapper,
                    kwargs={
                        'entity': 'list',
                        'card_id': st.session_state.selected_card,
                        'column': 'language',
                        'value': 'st.session_state.v_card_language',
                    }
                )
                #BUG update st.session_state.selected_card
                _ = prop_col.radio(
                    'Card number:',
                    options=[1,2],
                    horizontal=True
                )
                _ = prop_col.toggle('Foil')
                _ = prop_col.selectbox(
                    'Condition:',
                    options=[1,2],
                    key='v_card_condition'
                )





