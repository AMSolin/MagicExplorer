import streamlit as st
import pandas as pd
from utils import get_players

def name_textbox(
    entity, callback_function, name, index_id, st_column=st, db_path=None,
    **kwargs
):
    st.session_state[f'w_{entity}_name'] = name
    _ = st_column.text_input(
        'Name:',
        key=f'w_{entity}_name',
        on_change=callback_function,
        kwargs={
            'entity': entity,
            'id': index_id,
            'column': 'name',
            'value': f'st.session_state.w_{entity}_name',
            'db_path': db_path
        }
    )

def owner_selectbox(
    entity, callback_function, player_id, index_id, st_column=st, db_path=None,
    **kwargs
):
    df_players = get_players()[['player_id', 'name']]
    player_id = int(player_id) if pd.notnull(player_id) else None
    st.session_state[f'w_{entity}_owner'] = player_id
    _ = st_column.selectbox(
        'Owner:',
        options=df_players['player_id'].to_list(),
        format_func=lambda x: dict(df_players.values)[x],
        key=f'w_{entity}_owner',
        placeholder='Choose owner',
        on_change=callback_function,
        kwargs={
            'entity': entity,
            'id': index_id,
            'column': 'player_id',
            'value': f'st.session_state.w_{entity}_owner',
            'db_path': db_path
        }
    )

def entity_type_selectbox(
    entity, callback_function, type, index_id, st_column=st, db_path=None,
    **kwargs
):
    st.session_state.w_import_list_type = type
    _ = st_column.selectbox(
        'Type:',
        options=['Deck', 'Collection'],
        key='w_import_list_type',
        placeholder='Choose type',
        on_change=callback_function,
        kwargs={
            'entity': entity,
            'id': index_id,
            'column': 'type',
            'value': f'st.session_state.w_import_list_type',
            'db_path': db_path
        }
    )

def creation_datebox(
    entity, callback_function, creation_date, index_id, st_column=st, db_path=None,
    **kwargs
):
    _ = st_column.date_input(
        'Creation date:',
        format="DD.MM.YYYY",
        key=f'w_{entity}_creation_date',
        value=creation_date.to_pydatetime(),
        on_change=callback_function,
        kwargs={
            'entity': entity,
            'id': index_id,
            'column': 'creation_date',
            'value': f'st.session_state.w_{entity}_creation_date',
            'db_path': db_path
        }
    )

def wish_checkbox(
    entity, callback_function, is_wish, index_id, st_column=st, entity_type=None,
    db_path=None, **kwargs
):
    entity_type = entity if entity_type is None else entity_type
    st.session_state[f'w_is_wish_{entity}'] = is_wish
    _ = st_column.checkbox(
        f'Mark as wish {entity_type}',
        key=f'w_is_wish_{entity}',
        on_change=callback_function,
        kwargs={
            'entity': entity,
            'id': index_id,
            'column': 'is_wish',
            'value': f'int(st.session_state.w_is_wish_{entity})',
            'db_path': db_path
        }
    )

def primary_checkbox(
    entity, callback_function, is_default_list, name, index_id, st_column=st,
    **kwargs
):
    st.session_state['w_is_default_list'] = is_default_list
    _ = st_column.checkbox(
        'Mark as primary collection',
        disabled=bool(is_default_list),
        key='w_is_default_list',
        on_change=callback_function,
        kwargs={
            'entity': entity,
            'id': index_id,
            'column': 'is_default_list',
            'default_value': name
        }
    )

def note_textbox(
    entity, callback_function, note, index_id, st_column=st, entity_type=None,
    db_path=None, **kwargs
):
    entity_type = entity if entity_type is None else entity_type
    st.session_state[f'w_{entity}_note'] = note
    _ = st_column.text_area(
        f'{entity_type.capitalize()} note',
        key=f'w_{entity}_note',
        placeholder='Add your notes here',
        max_chars=256,
        height=68,
        on_change=callback_function,
        kwargs={
            'entity': entity,
            'id': index_id,
            'column': 'note',
            'value': f'st.session_state.w_{entity}_note',
            'db_path': db_path
        }
    )
