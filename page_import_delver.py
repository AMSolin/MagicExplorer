import streamlit as st
import pandas as pd
import time
from utils import *
from import_utils import *

def get_content():
    if 'v_delver_lists' not in st.session_state:
        df_delver_lists = get_delver_lists_names() \
            .assign(selected=True) \
            .assign(open=False) \
            .assign(type=lambda df: df.category.replace(
                {1: 'Coll.', 2: 'Deck'}
            ))
    else:
        df_delver_lists = st.session_state.df_delver_lists.assign(open=False)
    if 'current_d_list_id' in st.session_state:
        mask = (df_delver_lists['delver_list_id'] == st.session_state.current_d_list_id)
        df_delver_lists.loc[mask,'open'] = True
    with st.sidebar:
        def list_callback():
            changes = [
                (ix, [(col, val) for col, val in pair.items()])
                for ix, pair in st.session_state.v_delver_lists['edited_rows'].items()
            ]
            ix, [[col, val]]= changes[0]
            if col == 'open':
                if val is True:
                    st.session_state.current_d_list_id = df_delver_lists \
                        .iloc[ix].loc['delver_list_id']
                else:
                    del st.session_state.current_d_list_id
            # elif not ((col == 'is_default_list') and (val is False)):
            #     default_list = df_delver_lists.iloc[ix].loc['name']
            #     list_id = df_delver_lists.iloc[ix].loc['list_id']
            #     try:
            #         update_table('list', default_list, list_id, col, val)
            #     except sqlite3.IntegrityError:
            #         pass
            #          table_container.error(f'Collection {val} already exist!')
        st.session_state.df_delver_lists = st.data_editor(
            df_delver_lists.assign(create_ns=time.time_ns()), 
            key='v_delver_lists',
            hide_index=True,
            column_config={
                # 'selected': st.column_config.CheckboxColumn("🎲",),
                'selected': st.column_config.CheckboxColumn("s",),
                'delver_list_id': None,
                'category': None,
                'type': st.column_config.SelectboxColumn(
                    'Type', options=['Deck', 'Coll.'],
                     required=True,  width='small'
                ),
                'name': 'Name',
                'creation': None,
                'open': st.column_config.CheckboxColumn('Open'),
            },
            column_order=['selected', 'name', 'type', 'open'],
            on_change=list_callback
        )
    st.write(st.session_state.df_delver_lists)
    10
        
        
        # action = st.radio(
        #     label='Add / delete collection',
        #         options=('Add', 'Delete'),
        #         horizontal=True
        # )
        # if action == 'Add':
        #     with st.form('add_list', clear_on_submit=True):
        #         col1, col2 = st.columns((0.7, 0.3))
        #         new_list = col1.text_input('Enter new collection')
        #         col2.write('')
        #         col2.write('')
        #         submitted = col2.form_submit_button('Add')
        #         default_flag = st.checkbox('Set as default collection')
        #         if submitted and new_list.strip() != '':
        #             try:
        #                 add_new_record('list', new_list, default_flag)
        #                 st.experimental_rerun()
        #             except sqlite3.IntegrityError:
        #                 st.error(f'Collection {new_list} already exist!')
        # elif (action == 'Delete') and (df_delver_lists.shape[0] > 1):
        #     with st.form('delete_list', clear_on_submit=True):
        #         col1, col2 = st.columns((0.7, 0.3))
        #         deleted_list = col1.selectbox(
        #             label='Select collection to delete',
        #             options=df_delver_lists['name'].sort_index(ascending=False)
        #         )
        #         col2.write('')
        #         col2.write('')
        #         submitted = col2.form_submit_button('Drop')
        #         st.write('All cards from deleting collection will be also removed!')
        #         if submitted:
        #             delete_record('list', deleted_list)
        #             del st.session_state.current_list_id
        #             st.experimental_rerun()