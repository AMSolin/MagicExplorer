import streamlit as st
from st_click_detector import click_detector

from utils import *
import widgets

def update_searched_card(entity, card_id, column, value):
    """
    Callback fucntion for update searching card in
    "Add cards" tab
    """
    if isinstance(value, str) and 'session_state' in value:
        card_id[column] = eval(value)
    else:
        card_id[column] = value
    if column not in ['foil', 'condition_code']:
        # When card_uuid is changed
        st.session_state[f'searched_{entity}_card'] = search_set_by_name(
                'ignore_name',
                card_id['language'],
                card_id['card_uuid'].hex()
            ).iloc[0]
        
def render_entity_header(
        container, name, entity_type=None, counter=None, **default_args
    ):
    if default_args['entity'] == 'deck':
        col_left = container
    else:
        col_left, col_right = container.columns((0.7, 0.3))

    widgets.name_textbox(
        name=name, st_column=col_left, **default_args
    )

    if default_args['entity'] == 'list':
        _ = col_right.text_input(
            'Cards total:', value=counter, disabled=True
        )
    elif default_args['entity'] == 'import_list':
        widgets.entity_type_selectbox(
            entity_type=entity_type, st_column=col_right, **default_args
        )

def render_entity_prop_tab(
        player_id, creation_date, is_wish, note, is_default_list=None,
        **default_args
    ):

        col_left, col_right = st.columns([0.6, 0.4])

        widgets.owner_selectbox(
            player_id=player_id, st_column=col_left,**default_args
        )

        widgets.creation_datebox(
            creation_date=creation_date, st_column=col_right,**default_args
        )
        if default_args['entity'] == 'list':
            widgets.primary_checkbox(
                is_default_list=is_default_list, st_column=col_left,**default_args
            )
        widgets.wish_checkbox(
            is_wish=is_wish, st_column=col_right, **default_args
        )

        widgets.note_textbox(
            note=note,**default_args
        )

def render_card_prop_tab(entity, selected_card, callback_function):
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
        selected_card = st.session_state[f'searched_{entity}_card'] = \
            df_set_codes[
                (df_set_codes['name'] == selected_card_name) &
                (df_set_codes['language'] == selected_card_language)
            ].iloc[0]

    sets_dict = generate_set_dict(entity, df_set_codes, selected_card)

    css = generate_css_set_icons(entity, sets_dict)

    _ = click_detector(css, key=f'w_selected_{entity}_set')

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
        key='w_card_language',
        options=list_of_languages,
        index=current_language,
        on_change=callback_function,
        kwargs={
            'entity': entity,
            'column': 'language',
            'value': 'st.session_state.w_card_language',
            'card_id': selected_card
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
            st.session_state.w_card_number
        ]
        callback_function(**kwargs)
    
    _ = st.radio(
        'Card number:',
        horizontal=True,
        key='w_card_number',
        options=df_numbers['card_number'],
        index=current_number,
        on_change=card_number_to_uuid,
        kwargs={
            'entity': entity,
            'card_id':selected_card,
            'column': 'card_uuid'
        }
    )

    _ = st.toggle(
        '**:rainbow-background[Foil]**',
        key='w_foil_toggle',
        on_change=callback_function,
        kwargs={
            'entity': entity,
            'column': 'foil',
            'value': 'int(st.session_state.w_foil_toggle)',
            'card_id': selected_card
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
        key='w_card_condition',
        on_change=callback_function,
        kwargs={
            'entity': entity,
            'column': 'condition_code',
            'value': 'st.session_state.w_card_condition',
            'card_id': selected_card
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

def get_card_description(card_props, side_idx):

    def get_card_prop(props_dict, prop_name, side_idx):
        value = props_dict \
            .get('card_faces', [{}])[side_idx] \
            .get(prop_name, props_dict.get(prop_name))
        return value
    
    if power := get_card_prop(card_props, 'power', side_idx):
        toughness = get_card_prop(card_props, 'toughness', side_idx)
        card_props['P/T'] =  \
            f'{power}/{toughness}'.replace("*", " ★ ")
    list_legalities = [
        'standard', 'pioneer', 'modern', 'legacy', 
        'vintage', 'commander', 'pauper', 'historic', 'alchemy'
    ]
    legalities = ''
    for legality in list_legalities:
        if card_props['legalities'][legality] == 'legal':
            legalities += (f'{legality}, '.capitalize())
    card_props['Legalities_only'] = legalities[:-2]
    props_aliases = [
        ('printed_name', 'Card Name'), ('name', 'Card Name'),
        ('mana_cost', 'Mana Cost'), ('cmc', 'Mana Value'),
        ('printed_type_line', 'Types'), ('type_line', 'Types'),
        ('printed_text', 'Card Text'), ('oracle_text', 'Card Text'),
        ('flavor_text', 'Flavor Text'), 
        ('P/T', 'P/T'), ('rarity', 'Rarity'),
        ('collector_number', 'Card Number'), ('artist', 'Artist'),
        ('set_name', 'Set Name'), ('released_at', 'Release'),
        ('Legalities_only', 'Legalities')
    ]

    text_field = ''
    skip_next_property = False
    for property, alias in props_aliases:
        property_value = get_card_prop(card_props, property, side_idx)
        if skip_next_property:
            skip_next_property = False
            continue
        elif property_value:
            if 'printed' in property:
                skip_next_property = True
            if 'Text' in alias:
                property_value = property_value.replace('\n', '  \n')
            text_field += f"""**{alias}**:&nbsp;&nbsp;{property_value}  \n"""
    return text_field