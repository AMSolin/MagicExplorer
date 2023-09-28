import streamlit as st
import pandas as pd
from utils import display_toasts, get_lists, get_decks, import_cards

def init_session_variables():
    if 'selection_table' not in st.session_state:
        st.session_state.selection_table = pd.DataFrame(
            data = {
                'Name': pd.Series(dtype='str'),
                'Set code': pd.Series(dtype='str'),
                'Card number': pd.Series(dtype='str'),
                'Language': pd.Series(dtype='str'),
                'Qnty': pd.Series(dtype='int'),
                'Foil': pd.Series(dtype='bool'),
                'Condition': pd.Series(dtype='str'),
                'Deck type': pd.Series(dtype='str'),
                'row_order': pd.Series(dtype='int'),
            })
        st.session_state.counter = 0
    if 'selected_prev_card' not in st.session_state:
        st.session_state.selected_prev_card = ''
    display_toasts()

def export_section():
    list_action = st.radio(
        label='Choose list to add cards',
        options=('Skip', 'Available', 'New'),
        horizontal=True
    )
    deck_action = st.radio(
        label='Choose deck to add cards',
        options=('Skip', 'Available', 'New'),
        horizontal=True
    )

    total_cards = st.session_state.selection_table['Qnty'].sum()
    if not list_action == deck_action == 'Skip' and total_cards > 0:
        with st.form('Import options', clear_on_submit=True):
            if list_action == 'Available':
                list_name = st.selectbox(
                    label='Select list',
                    options=get_lists()['name']
                )
            elif list_action == 'New':
                list_name = st.text_input('Enter new list name')
            else:
                list_name = ''
            if deck_action == 'Available':
                deck_name = st.selectbox(
                    label='Select deck',
                    options=get_decks()['name']
                )
            elif deck_action == 'New':
                deck_name = st.text_input('Enter new deck name')
            else:
                deck_name = ''
            submitted = st.form_submit_button(f'Add {total_cards} card(s)')
            if submitted:
                err_msg = ' Import aborted!'
                if (list_action == 'New') & (list_name.strip() == ''):
                    st.error(f'Enter list name!' + err_msg)
                elif (list_action == 'New') & \
                    (list_name in get_lists()['name'].values):
                    st.error(f'List {list_name} already exist!' + err_msg)
                elif (deck_action == 'New') & (deck_name.strip() == ''):
                    st.error(f'Enter deck name!' + err_msg)
                elif (deck_action == 'New') & \
                    (deck_name in get_decks()['name'].values):
                    st.error(f'Deck {deck_name} already exist!' + err_msg)
                else:
                    import_cards(
                        st.session_state.selection_table,
                        list_action, list_name, deck_action, deck_name
                    )
                    del st.session_state.selection_table
                    st.experimental_rerun()