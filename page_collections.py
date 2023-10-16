import streamlit as st
import pandas as pd
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
                    update_table('list', default_list, list_id, col, val)
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
                        add_new_record('list', new_list, default_flag)
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
    list_side, overview_side = st.columns((0.5, 0.5))

    with list_side:
        df_list_content = get_list_content(st.session_state.current_list_id).assign(open=False)
        card_id_cols = [
            'card_uuid', 'condition_id', 'foil', 'language',
            'set_code', 'card_number', 'language_code'
        ]
        if st.session_state.selected_card:
            mask = (df_list_content[card_id_cols[:4]] == st.session_state.selected_card[:4]).all(1)
            df_list_content.loc[mask, 'open'] = True
        
        def list_content_callback():
            changes = [
                (ix, [(col, val) for col, val in pair.items()])
                for ix, pair in st.session_state.v_list_content['edited_rows'].items()
            ]
            ix, [[col, val]]= changes[0]
            if col == 'open':
                st.session_state.selected_card = df_list_content[
                    card_id_cols
                ].iloc[ix].tolist()
            else:
                card_dict = df_list_content.iloc[ix].to_dict()
                card_dict['list_id'] = int(st.session_state.current_list_id)
                try:
                    update_table_content('list', card_dict, col, val)
                except sqlite3.IntegrityError:
                     table_container.error(f'Collection {val} already exist!')
        _ = st.data_editor(
            df_list_content,
            key='v_list_content',
            hide_index=True,
            column_config={
                'card_uuid': None,
                'condition_id': None,
                'language': None,
                'qnty': st.column_config.NumberColumn(
                    'Qnty', min_value=0, max_value=99, step=1
                ),
                'name': 'Name',
                'card_number': None,
                'type': 'Type',
                'language_code': 'Lang',
                'set_code': 'Set',
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
            on_change=list_content_callback
        )
    with overview_side:
        expand_check =  st.session_state.active_expander == 'list_info'
        e_list_info = st.expander(
            'Collection info',
            expanded=st.session_state.active_expander == 'list_info'
        )
        if expand_check:
            list_name, creation_dtm, note, player_id, owner = df_lists \
                .loc[
                    mask_list,
                    ['name', 'creation_date', 'note', 'player_id', 'owner']
                ] \
                .values.ravel()
            with e_list_info:
                col_list_name, col_owner, col_creation_date =  \
                    st.columns((0.4, 0.4, 0.2))
                
                def update_table_wrapper(**kwargs):
                    try:
                        update_table(**kwargs)
                    except sqlite3.IntegrityError:
                        e_list_info_container.error(
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
                        'default_value': None,
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
                col_owner.selectbox(
                    'Owner:',
                    options=df_players['player_id'],
                    format_func=lambda x: dict(df_players.values)[x],
                    index=idx,
                    key='v_list_owner',
                    placeholder='Choose owner',
                    on_change=update_table_wrapper,
                    kwargs={
                        'entity': 'list',
                        'default_value': None,
                        'id': st.session_state.current_list_id,
                        'column': 'player_id',
                        'value': 'st.session_state.v_list_owner'
                    }
                )

                col_creation_date.date_input(
                    'Creation date:',
                    value=creation_dtm.to_pydatetime(),
                    format="DD.MM.YYYY",
                    key='v_creation_date',
                    on_change=update_table_wrapper,
                    kwargs={
                        'entity': 'list',
                        'default_value': None,
                        'id': st.session_state.current_list_id,
                        'column': 'creation_date',
                        'value': 'st.session_state.v_creation_date'
                    }
                )

                e_list_info_container = st.container()
                e_list_info_container.empty()
                e_list_info.text_area(
                    'Collection note',
                    value=note,
                    key='v_list_note',
                    placeholder='Add your notes here',
                    max_chars=256,
                    on_change=update_table_wrapper,
                    kwargs={
                        'entity': 'list',
                        'default_value': None,
                        'id': st.session_state.current_list_id,
                        'column': 'note',
                        'value': 'st.session_state.v_list_note'
                    }
                )

        if st.session_state.selected_card:
            img_col, description_col =  st.columns((0.4, 0.6))
            img_col.image(get_image_uris(*st.session_state.selected_card[4:]))




