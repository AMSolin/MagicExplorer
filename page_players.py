import streamlit as st
import pandas as pd
from utils import *

def get_content():
    with st.sidebar:
        players_table = get_players()
        def callback():
            changes = [
                (ix, [(col, val) for col, val in pair.items()])
                for ix, pair in st.session_state.players_table['edited_rows'].items()
            ]
            ix, [[col, val]]= changes[0]
            if not ((col == 'is_default_player') and (val is False)):
                player = players_table.iloc[ix].loc['name']
                player_id = players_table.iloc[ix].loc['player_id']
                try:
                    update_player(player, player_id, col, val)
                except sqlite3.IntegrityError:
                     st.session_state.callback_err = val

        _ = st.data_editor(
            players_table, 
            key='players_table',
            hide_index=True,
            disabled=['player_id', 'create_ns'],
            column_config={
                'name': 'Player name',
                'is_default_player': st.column_config.CheckboxColumn('Default player')
            },
            column_order=['name', 'is_default_player'],
            on_change=callback
        )
        
        if st.session_state.get('callback_err'):
            player = st.session_state.pop('callback_err')
            st.sidebar.error(f'Player {player} already exist!')

        if 'changes_players_table' not in st.session_state:
            st.session_state.changes_players_table = False
        
        action = st.radio(
            label='Add / delete player',
                options=('Add', 'Delete'),
                horizontal=True
        )
        if action == 'Add':
            with st.form('add_player', clear_on_submit=True):
                col1, col2 = st.columns((0.7, 0.3))
                new_player = col1.text_input('Enter new player')
                col2.write('')
                col2.write('')
                submitted = col2.form_submit_button('Add')
                default_flag = st.checkbox('Set as default player')
                if submitted and new_player.strip() != '':
                    try:
                        add_new_player(new_player, default_flag)
                        st.session_state.changes_players_table = (
                            action, new_player
                        )
                        st.experimental_rerun()
                    except sqlite3.IntegrityError:
                            st.error(f'Player {new_player} already exist!')

        if (action == 'Delete') and (players_table.shape[0] > 1):
            with st.form('delete_player', clear_on_submit=True):
                col1, col2 = st.columns((0.7, 0.3))
                deleted_player = col1.selectbox(
                        label='Select player to delete',
                        options=players_table['name'].sort_index(ascending=False)
                )
                col2.write('')
                col2.write('')
                submitted = col2.form_submit_button('Drop')
                if submitted:
                    delete_player(deleted_player)
                    st.session_state.changes_players_table = (
                        action, deleted_player
                    )
                    st.experimental_rerun()
        
        if st.session_state.changes_players_table:
            last_action, last_name = st.session_state.changes_players_table
            msg = ' added!' if last_action == 'Add' else ' deleted!'
            st.info(f'Player {last_name} was {msg}', icon='ℹ️')
        st.session_state.changes_players_table = False
    
    st.write('here will be player info coming soon')