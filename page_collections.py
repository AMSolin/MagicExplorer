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
    list_side, overview_side = st.columns((0.7, 0.3))

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
                'rarity': 'Rarity',
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
            list_name, creation_dtm, note, owner = df_lists \
                .loc[mask_list, ['name', 'creation_date', 'note', 'owner']] \
                .values.ravel()
            e_list_info.write(list_name)
            e_list_info.write(f'Creation_date: {creation_dtm}')
            e_list_info.selectbox(
                'List owner',
                ['you', 'me']
            )
            e_list_info.text_area(
                'Collection note',
                'here will be \n'
                'your notes \n'
                'about this collection'
            )

        if st.session_state.selected_card:
            st.image(get_image_uris(*st.session_state.selected_card[4:]))




