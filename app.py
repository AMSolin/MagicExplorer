import streamlit as st
import page_import, page_collections, page_players, page_initialization, page_import_delver_lens
from utils import *

st.set_page_config(
    page_title="Magic explorer",
    page_icon="🎲",
    layout="wide",
    initial_sidebar_state="expanded",
    # menu_items={} 
)
padding_top = 2
st.markdown(
        f"""
			<style>
			.appview-container .main .block-container{{
					padding-top: {padding_top}rem;
					padding-right: {1}rem;
					padding-left: {1}rem;
					}}
			</style>
			""",
        unsafe_allow_html=True,
    )

def main():

	# st.title('Magic explorer') #TODO return after multi-page version
	menu = ['Init', 'Cards', 'Import', 'Delver Lens', 'Players', 'Collections', 'Decks']
	choice = st.sidebar.selectbox('Menu',menu)
	if choice == 'Init':
		page_initialization.get_content()
	if choice == 'Players':
		page_players.get_content()
	if choice == 'Collections':
		page_collections.get_content()
	if choice == 'Import':
		page_import.get_content()
	if choice == 'Delver':
		page_import_delver_lens.get_content()
main()

