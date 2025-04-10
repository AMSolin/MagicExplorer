import streamlit as st
import pandas as pd
from utils import *

def get_content():
    display_toasts()
    with st.sidebar:
        players_table = get_players()
        table_container = st.container()
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
                    update_table(
                        'player', col, val, player_id, default_value=player
                    )
                except sqlite3.IntegrityError:
                     table_container.error(f'Player {val} already exist!')
        _ = table_container.data_editor(
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
                        add_new_record('player', new_player, is_default=default_flag)
                        st.rerun()
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
                    delete_record('player', deleted_player)
                    st.rerun()
    st.write('here will be player info coming soon')