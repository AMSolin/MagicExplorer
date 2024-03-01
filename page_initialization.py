import streamlit as st
from init_app import *

def get_content():
    tables_list = [
        ('players', 'user_data.db', reset_table_players),
        ('lists', 'user_data.db', reset_table_lists),
        ('list_content', 'user_data.db', reset_table_list_content),
        ('decks', 'user_data.db', reset_table_decks),
        ('deck_content', 'user_data.db', reset_table_deck_content),
        
        ('card_condition', 'app_data.db', reset_table_card_condition),
        ('deck_types', 'app_data.db', reset_table_deck_types),
        ('card_names', 'app_data.db', reset_table_card_names),
        ('sets', 'app_data.db', reset_table_sets),
        ('languages', 'app_data.db', reset_table_languages),
        ('cards', 'app_data.db', reset_table_cards),
        ('foreign_data', 'app_data.db', reset_table_foreign_data),
    ]
    for table in tables_list:
        check_table(*table)