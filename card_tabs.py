import streamlit as st
from st_click_detector import click_detector

from utils import *

def render_card_prop_tab(selected_card, callback_function):
    if isinstance(selected_card, list):
        selected_card_name = selected_card[0]
        selected_card_language = selected_card[1]
    else:
        selected_card_name = selected_card['name']
        selected_card_language = selected_card['language']
    df_set_codes = st.session_state.df_set_codes = search_set_by_name(
        selected_card_name,
        selected_card_language
    )
    if isinstance(selected_card, list):
        selected_card = st.session_state.searched_card = \
            df_set_codes[
                (df_set_codes['name'] == selected_card_name) &
                (df_set_codes['language'] == selected_card_language)
            ].iloc[0]

    sets_dict = generate_set_dict(df_set_codes, selected_card)

    css = generate_css_set_icons(sets_dict)

    _ = click_detector(css, key='v_selected_set')

    st.markdown(
        f"Set:&nbsp;&nbsp;**{selected_card['set_name']}**"
    )

    list_of_languages = search_languages_by_card_uuid(
        selected_card.loc['card_uuid'].hex()
    )
    current_language = list_of_languages.index(
        selected_card['language']
    )
    _ = st.selectbox(
        'Language:',
        key='v_card_language',
        options=list_of_languages,
        index=current_language,
        on_change=callback_function,
        kwargs={
            'entity': 'list',
            'card_id': selected_card,
            'column': 'language',
            'value': 'st.session_state.v_card_language',
        }
    )

    df_numbers = search_card_numbers(
        selected_card.loc['card_uuid'].hex(),
        selected_card.loc['language'],
        selected_card.loc['set_code']
    )
    current_number = int(
        df_numbers[
            df_numbers['card_number'] == selected_card['card_number']
        ].index[0]
    )

    def card_number_to_uuid(**kwargs):
        """
        Workaround for cases, when user select set with same 
        card number(s) as in previous set, which lead to unexpected 
        trigger card number widget with build-in format function.
        """
        kwargs['value'] = dict(df_numbers.values)[
            st.session_state.v_card_number
        ]
        callback_function(**kwargs)
    
    _ = st.radio(
        'Card number:',
        horizontal=True,
        key='v_card_number',
        options=df_numbers['card_number'],
        index=current_number,
        on_change=card_number_to_uuid,
        kwargs={
            'entity': 'list',
            'card_id':selected_card,
            'column': 'card_uuid'
        }
    )

    _ = st.toggle(
        '**:rainbow-background[Foil]**',
        key='v_foil_toggle',
        on_change=callback_function,
        kwargs={
            'entity': 'list',
            'card_id':selected_card,
            'column': 'foil',
            'value': 'int(st.session_state.v_foil_toggle)',
        }
    )

    list_of_conditions = ['NM', 'SP', 'MP', 'HP', 'D']
    current_condition_id = list_of_conditions.index(
        selected_card['condition_code']
    )
    _ = st.selectbox(
        'Condition:',
        options=list_of_conditions,
        index=current_condition_id,
        key='v_card_condition',
        on_change=callback_function,
        kwargs={
            'entity': 'list',
            'card_id':selected_card,
            'column': 'condition_code',
            'value': 'st.session_state.v_card_condition',
        }
    )

def render_card_img_tab(card_props):
    if card_props.get('card_faces'):
        labels = ['First', 'Second'] if card_props.get('image_uris') \
            else ['Front', 'Back']
        side = st.radio(
            'no label',
            labels,
            label_visibility='collapsed', 
            horizontal=True
        )
        side_idx = 0 if side in ['Front', 'First'] else 1
        img_uri = card_props \
            .get('card_faces', [{}])[side_idx] \
                .get('image_uris', {}) \
                    .get(
                        'normal',
                        card_props.get('image_uris', {}).get('normal')
                    )
        st.image(img_uri)
    else:
        side_idx = -1
        st.image(card_props['image_uris']['normal'])
    return side_idx