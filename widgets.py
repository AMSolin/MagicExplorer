import streamlit as st
from utils import get_players

def owner_selectbox(
    entity, callback_function, player_id, id, db_path=None, column=st
):
    df_players = get_players()[['player_id', 'name']]
    player_id = player_id if isinstance(player_id, int) else None
    st.session_state[f'w_{entity}_owner'] = player_id
    _ = column.selectbox(
        'Owner:',
        options=df_players['player_id'].to_list(),
        format_func=lambda x: dict(df_players.values)[x],
        key=f'w_{entity}_owner',
        placeholder='Choose owner',
        on_change=callback_function,
        kwargs={
            'entity': entity,
            'id': id,
            'column': 'player_id',
            'value': f'st.session_state.w_{entity}_owner',
            'db_path': db_path
        }
    )