import streamlit as st
import pandas as pd
import time
from utils import *
from import_utils import *

def get_content():
    if 'v_delver_lists' not in st.session_state:
        df_delver_lists = get_delver_lists_names()
        df_delver_lists = df_delver_lists \
            .assign(selected=True) \
            .assign(open=False) \
            .assign(type=lambda df: df.category.replace(
                {1: 'List', 2: 'Deck'}
            ))
        st.session_state.s_selected_lists = df_delver_lists['selected']
    else:
        df_delver_lists = st.session_state.df_delver_lists \
            .assign(open=False) \
            .assign(selected=st.session_state.s_selected_lists)
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
            if col == 'selected':
                st.session_state.s_selected_lists \
                    .iloc[ix] = val
        
        st.session_state.df_delver_lists = st.data_editor(
            df_delver_lists,
            key='v_delver_lists',
            hide_index=True,
            column_config={
                'selected': st.column_config.CheckboxColumn("✔",),
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
            disabled=['name', 'type'],
            on_change=list_callback
        )