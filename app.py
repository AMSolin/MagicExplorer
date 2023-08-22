import streamlit as st
# from streamlit_searchbox import st_searchbox
# from st_click_detector import click_detector
# import pandas as pd
import page_import, page_card_base, page_players, page_initialization
from utils import *

st.set_page_config(
    page_title="Magic explorer",
    page_icon="🎲",
    layout="wide",
    initial_sidebar_state="expanded",
    # menu_items={} 
)
padding_top = 0
st.markdown(
        f"""
			<style>
			.appview-container .main .block-container{{
					padding-top: {padding_top}rem;    }}
			</style>
			""",
        unsafe_allow_html=True,
    )

def main():

	st.title('Magic explorer')
	menu = ['Init', 'Cards', 'Import', 'Players','Lists','Decks']
	choice = st.sidebar.selectbox('Menu',menu)
	if choice == 'Init':
		page_initialization.get_content()
	if choice == 'Cards':
		page_card_base.get_content()
	if choice == 'Players':
		page_players.get_content()
	if choice == 'Import':
		page_import.get_content()
main()

