import streamlit as st
from streamlit_searchbox import st_searchbox
from st_click_detector import click_detector
import pandas as pd
from utils import *
from import_utils import *

def get_content():
    init_session_variables()
    exact_search = st.checkbox('Точный поиск')
    searh_func = to_lower_and_exact_search if exact_search else to_lower_and_substring_search
    searched_card_name = st_searchbox(
        search_function=searh_func,
            placeholder="Enter card name",
            key="search_card_by_name",
            clearable=True
        )

    if searched_card_name:
        card_name, card_lang = searched_card_name
        df_card_prints = search_set_by_name(card_name, card_lang)
        sets_dict = generate_set_dict(df_card_prints['keyrune_code'])
        css = generate_css_set_icons(sets_dict)

        selected_set = click_detector(css, key='selected_set')
        selected_card = click_detector(
            get_card_images(df_card_prints, selected_set),
            key='selected_card_detector'
        )
        if selected_card != '' and selected_card != st.session_state.selected_prev_card:
            st.session_state.selected_prev_card = selected_card
            row = [card_name] + selected_card.split(' ')[:-1] + [False, 'NM', 'main']
            cond = (st.session_state.selection_table.drop(columns=['Qnty', 'row_order']) == row).all(1)
            if cond.any():
                st.session_state.selection_table.loc[cond, 'Qnty'] += 1
            else:
                st.session_state.counter += 1
                st.session_state.selection_table = pd.concat([
                        pd.DataFrame(
                            data = {
                                'Name': row[0],
                                'Set code': row[1],
                                'Card number': row[2],
                                'Language': row[3],
                                'Qnty': [1],
                                'Foil': [False],
                                'Condition': ['NM'],
                                'Deck type': ['main'],
                                'row_order': [st.session_state.counter]
                            }
                        ),
                        st.session_state.selection_table
                    ],
                    ignore_index=True
            )
    with st.sidebar:
        with st.expander('Configure table'):
            visible_cols = st.multiselect(
                label='Configure table',
                options= [
                    'Set code',
                    'row_order',# 'Card number',
                    'Language',
                    'Foil',
                    'Condition',
                    'Deck type'
                ],
                default = None,
                label_visibility='hidden'
            )
            visible_cols = ['Name', 'Qnty'] + visible_cols
        hidden_columns = set(st.session_state.selection_table) - set(visible_cols)
        column_config={
            'Name': 'Name',
            'Set code': 'Set',
            'Card number': None,#'Num.',
            'Language': 'Lang.',
            'Qnty': st.column_config.NumberColumn(
                'Q.', min_value=0, max_value=60, step=1, width='small'
            ),
            'Foil': st.column_config.CheckboxColumn('F.', width='small'),
            'Condition': st.column_config.SelectboxColumn(
                'Cond.', options=['NM', 'SP', 'MP', 'HP', 'D'],
                required=True, default='NM', width='small'
            ),
            'Deck type': st.column_config.SelectboxColumn(
                'Deck type', options=['main', 'sideboard', 'maybe'],
                required=True, default='main', width='small'
            ),
            'row_order': 'row_order'#None
        }
        for col in hidden_columns:
            column_config[col] = None
        edited_table = st.data_editor(
            st.session_state.selection_table,
            key='cards_editor',
            hide_index=True,
            column_config=column_config,
            disabled=['Name', 'Set code', 'Card number', 'Language'],
            column_order=visible_cols,
            use_container_width=True
        )

        if not st.session_state.selection_table.equals(edited_table):
            st.session_state.selection_table = edited_table[edited_table['Qnty'] > 0] \
                .groupby([col for col in edited_table.columns if col not in ['Qnty', 'row_order']]) \
                .agg(Qnty=('Qnty','sum'), row_order=('row_order', 'min')) \
                .reset_index().sort_values(by='row_order', ascending=False)
            st.rerun()

        export_section()