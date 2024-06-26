import streamlit as st
from st_click_detector import click_detector
from streamlit_searchbox import st_searchbox
from utils import *
import uuid

def get_content():
    display_toasts()

    df_lists = get_lists().assign(open=False)
    if 'current_list_id' not in st.session_state:
        st.session_state.current_list_id = df_lists.iloc[0].loc['list_id']
    mask_list = df_lists['list_id'] == st.session_state.current_list_id
    df_lists.loc[mask_list, 'open'] = True

    def check_match_selected_card_and_set(active_tab, card_key):
        card_key_cols = ['set_code', 'card_number', 'language', 'card_uuid']
        result = (st.session_state.get('v_tab_bar', None) == active_tab) \
        and ('selected_set' in st.session_state) \
        and (
            st.session_state[card_key].loc[card_key_cols] \
                .apply(lambda x: x if isinstance(x, str) else x.hex()) \
                .values != st.session_state.selected_set.split(' ')
        ).any()
        return result
            
    if 'selected_card' not in st.session_state:
        st.session_state.selected_card = None
    elif check_match_selected_card_and_set('Edit card', 'selected_card'):
        _, _, language, card_uuid = st.session_state.selected_set.split(' ')
        columns = ['language', 'card_uuid']
        values = [language, uuid.UUID(card_uuid).bytes]
        update_table_content('list', st.session_state.selected_card, columns, values)
    elif check_match_selected_card_and_set('Add cards', 'searched_card'):
        mask = (
            st.session_state.df_set_codes[
                ['set_code', 'card_number', 'language', 'card_uuid']
            ] \
            .assign(
                card_uuid=st.session_state.df_set_codes['card_uuid']
                    .apply(lambda x: x.hex())
            ) \
            .values == st.session_state.selected_set.split(' ')
        ).all(1)
        st.session_state.searched_card = st.session_state.df_set_codes \
            .loc[mask].iloc[0]
        st.session_state.searched_card['list_id'] = st.session_state.current_list_id
    
    with st.sidebar:
        table_container = st.container()

        def list_callback():
            changes = [
                (ix, [(col, val) for col, val in pair.items()])
                for ix, pair in st.session_state.v_lists['edited_rows'].items()
            ]
            ix, [[col, val]]= changes[0]
            if col == 'open':
                st.session_state.current_list_id = df_lists.iloc[ix].loc['list_id']
                st.session_state.v_tab_bar = None
                st.session_state.selected_card = None
            elif not ((col == 'is_default_list') and (val is False)):
                default_list = df_lists.iloc[ix].loc['name']
                list_id = df_lists.iloc[ix].loc['list_id']
                try:
                    update_table(
                        'list', list_id, col, val, default_value=default_list
                    )
                except sqlite3.IntegrityError:
                     table_container.error(f'Collection {val} already exist!')  

        _ = table_container.data_editor(
            df_lists, 
            key='v_lists',
            hide_index=True,
            column_config={
                'name': 'Collection',
                'is_default_list': st.column_config.CheckboxColumn('Default'),
                'open': st.column_config.CheckboxColumn('Open'),
            },
            column_order=['name', 'is_default_list', 'open'],
            on_change=list_callback
        )
        
        action = st.radio(
            label='Add / delete collection',
                options=('Add', 'Delete'),
                horizontal=True
        )
        if action == 'Add':
            with st.form('add_list', clear_on_submit=True):
                col1, col2 = st.columns((0.7, 0.3))
                new_list = col1.text_input('Enter new collection')
                col2.write('')
                col2.write('')
                submitted = col2.form_submit_button('Add')
                default_flag = st.checkbox('Set as default collection')
                if submitted and new_list.strip() != '':
                    try:
                        add_new_record('list', new_list, is_default=default_flag)
                        st.experimental_rerun()
                    except sqlite3.IntegrityError:
                        st.error(f'Collection {new_list} already exist!')
        elif (action == 'Delete') and (df_lists.shape[0] > 1):
            with st.form('delete_list', clear_on_submit=True):
                col1, col2 = st.columns((0.7, 0.3))
                deleted_list = col1.selectbox(
                    label='Select collection to delete',
                    options=df_lists['name'].sort_index(ascending=False)
                )
                col2.write('')
                col2.write('')
                submitted = col2.form_submit_button('Drop')
                st.write('All cards from deleting collection will be also removed!')
                if submitted:
                    delete_record('list', deleted_list)
                    del st.session_state.current_list_id
                    st.experimental_rerun()
    list_side, overview_side = st.columns((0.6, 0.4))

    with list_side:
        df_list_content = get_list_content(st.session_state.current_list_id).assign(open=False)
        card_id_cols = [
            'list_id', 'card_uuid', 'condition_code', 'foil', 'language',
            'qnty', 'name', 'keyrune_code', 'set_name',
            'set_code', 'card_number', 'language_code'
        ]
        if st.session_state.selected_card is not None:
            mask = (df_list_content[card_id_cols[:5]] == st.session_state.selected_card[:5]).all(1)
            df_list_content.loc[mask, 'open'] = True
            if st.session_state.selected_card.name == 'need_update':
                st.session_state.selected_card.name = ''
                st.session_state.selected_card = df_list_content \
                    [card_id_cols].loc[mask].iloc[0]
        
        def update_table_content_wrapper(**kwargs):
            if 'value' not in kwargs:
                # Если функция была вызвана при изменении таблицы
                changes = [
                    (ix, [(column, value) for column, value in pair.items()])
                    for ix, pair in st.session_state.v_list_content['edited_rows'].items()
                ]
                ix, [[column, value]]= changes[0]
                if column == 'open':
                    if value == True:
                        st.session_state.selected_card = df_list_content[
                            card_id_cols
                        ].iloc[ix]
                    else:
                        st.session_state.selected_card = None
                    if 'selected_set' in st.session_state:
                        del st.session_state.selected_set
                    del st.session_state.v_tab_bar
                    return
                update_table_content('list', df_list_content.iloc[ix], column, value)
            else:
                # Если фунция была вызвана при изменении виджета
                update_table_content(**kwargs)
        
        _ = st.data_editor(
            df_list_content,
            key='v_list_content',
            height=843,
            hide_index=True,
            column_config={
                'list_id': None,
                'card_uuid': None,
                'language': None,
                'qnty': st.column_config.NumberColumn(
                    'Qnty', min_value=0, max_value=99, step=1
                ),
                'name':'Name',
                'card_number': None,
                'type': 'Type',
                'language_code': None,
                'set_name': None,
                'keyrune_code': None,
                'rarity': None,
                'mana_cost': 'Cost',
                'foil': st.column_config.CheckboxColumn('Foil'),
                'condition_code': None,
                'create_ns': None,
                'open': st.column_config.CheckboxColumn('Open'),
            },
            disabled=[
                'name', 'type', 'language_code', 'set_code', 'rarity', 
                'mana_cost', 'foil', 'condition_code']
            ,
            on_change=update_table_content_wrapper,
            kwargs={
                'df_list_content': df_list_content, 'card_id_cols': card_id_cols
            }
        )
    with overview_side:

        list_name, creation_dtm, note, player_id, owner = df_lists \
            .loc[
                mask_list,
                ['name', 'creation_date', 'note', 'player_id', 'owner']
            ] \
            .values.ravel()
        
        def update_table_wrapper(**kwargs):
            try:
                update_table(**kwargs)
            except sqlite3.IntegrityError:
                list_name_container.error(
                    f'Collection {st.session_state.v_list_name} already exist!'
                )
                st.session_state.v_list_name = list_name
        
        list_name_container = st.container()
        col_list_name, col_counter = list_name_container.columns((0.8, 0.2))
        _ = col_list_name.text_input(
            'Collection name:',
            value=list_name,
            key='v_list_name',
            on_change=update_table_wrapper,
            kwargs={
                'entity': 'list',
                'id': st.session_state.current_list_id,
                'column': 'name',
                'value': 'st.session_state.v_list_name'
            }
        )

        _ = col_counter.text_input(
            'Cards total:',
            value=df_list_content['qnty'].sum(),
            disabled=True
        )

        collection_tabs = ['Collection info', 'Add cards']
        default_tab = 'Collection info'
        if st.session_state.selected_card is not None:
            default_tab = 'Card overview'
            collection_tabs += ['Card overview', 'Edit card']
        collection_active_tab = show_tab_bar(
            collection_tabs,
            tabs_size=[1.2, 1, 1, 0.8],
            default=default_tab,
            key='v_tab_bar'
        )
        
        def render_card_prop_tab(selected_card):
            if isinstance(selected_card, list):
                selected_card_name = selected_card[0]
                selected_card_language = selected_card[1]
            else:
                selected_card_name = selected_card['name']
                selected_card_language = selected_card['language']
            st.session_state.df_set_codes = search_set_by_name(
                selected_card_name,
                selected_card_language
            )
            if isinstance(selected_card, list):
                selected_card = st.session_state.searched_card = \
                    st.session_state.df_set_codes.iloc[0]
                selected_card['list_id'] = st.session_state.current_list_id
            sets_dict = generate_set_dict(
                st.session_state.df_set_codes,
                selected_card=selected_card
            )
            css = generate_css_set_icons(sets_dict)
            _ = click_detector(css, key='selected_set')
 
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
                on_change=update_table_content_wrapper,
                kwargs={
                    'entity': 'list',
                    'card_id': selected_card,
                    'column': 'language',
                    'value': 'st.session_state.v_card_language',
                }
            )

            df_numbers = search_all_numbers_by_card_number(
                selected_card.loc['card_number'],
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
                update_table_content(**kwargs)
            
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
                on_change=update_table_content_wrapper,
                kwargs={
                    'entity': 'list',
                    'card_id':selected_card,
                    'column': 'foil',
                    'value': 'st.session_state.v_foil_toggle',
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
                on_change=update_table_content_wrapper,
                kwargs={
                    'entity': 'list',
                    'card_id':selected_card,
                    'column': 'condition_code',
                    'value': 'st.session_state.v_card_condition',
                }
            )
        
        if collection_active_tab == 'Collection info':
            col_owner, col_creation_date = st.columns([0.8, 0.2])

            df_players = get_players()[['player_id', 'name']]
            if owner is not None:
                idx = int(
                    df_players[
                        df_players['player_id'] == player_id
                    ].index[0]
                )
            else:
                idx = None
            _ = col_owner.selectbox(
                'Owner:',
                options=df_players['player_id'],
                format_func=lambda x: dict(df_players.values)[x],
                index=idx,
                key='v_list_owner',
                placeholder='Choose owner',
                on_change=update_table_wrapper,
                kwargs={
                    'entity': 'list',
                    'id': st.session_state.current_list_id,
                    'column': 'player_id',
                    'value': 'st.session_state.v_list_owner'
                }
            )
            _ = col_creation_date.date_input(
                'Creation date:',
                value=creation_dtm.to_pydatetime(),
                format="DD.MM.YYYY",
                key='v_creation_date',
                on_change=update_table_wrapper,
                kwargs={
                    'entity': 'list',
                    'id': st.session_state.current_list_id,
                    'column': 'creation_date',
                    'value': 'st.session_state.v_creation_date'
                }
            )

            st.text_area(
                'Collection note',
                value=note,
                key='v_list_note',
                placeholder='Add your notes here',
                max_chars=256,
                height=10,
                on_change=update_table_wrapper,
                kwargs={
                    'entity': 'list',
                    'id': st.session_state.current_list_id,
                    'column': 'note',
                    'value': 'st.session_state.v_list_note'
                }
            )
        
        if collection_active_tab == 'Add cards':
            st.session_state.selected_card = None
            search_bar, exact_seach_box = st.columns((0.7, 0.3))
            def reset_searchbar():
                del st.session_state.v_searched_card
            exact_match = exact_seach_box.checkbox(
                'Exact match',
                value=False,
                on_change=reset_searchbar
            )
            searh_function = to_lower_and_exact_search if exact_match \
                else to_lower_and_substring_search
            with search_bar:
                searched_card_name = st_searchbox(
                    search_function=searh_function,
                    placeholder="Enter card name",
                    key="v_searched_card",
                    clearable=True
                )
            img_col, prop_col =  st.columns((0.5, 0.5))
            if searched_card_name:
                if 'searched_card' in st.session_state and \
                    searched_card_name == st.session_state.searched_card.loc[['name', 'language']].to_list():
                    searched_card_name = st.session_state.searched_card
                with prop_col:
                    render_card_prop_tab(searched_card_name)
                with img_col:
                    pass

        if collection_active_tab in collection_tabs[2:]:
            img_col, prop_col =  st.columns((0.5, 0.5))
            card_api_key = [val for val in st.session_state.selected_card[-3:].values]
            card_props = get_card_properties(*card_api_key)
            img_container = img_col.container()
            if card_props.get('card_faces'):
                labels = ['First', 'Second'] if card_props.get('image_uris') \
                     else ['Front', 'Back']
                side = img_col.radio(
                    'no label',
                    labels,
                    label_visibility='collapsed', 
                    horizontal=True
                )
                ix = 0 if side in ['Front', 'First'] else 1
                img_uri = card_props \
                    .get('card_faces', [{}])[ix] \
                        .get('image_uris', {}) \
                            .get(
                                'normal',
                                card_props.get('image_uris', {}).get('normal')
                            )
                img_container.image(img_uri)
            else:
                ix = -1
                img_container.image(card_props['image_uris']['normal'])
            if collection_active_tab == 'Card overview':
                def get_card_prop(props_dict, prop_name, side_ix):
                    value = props_dict \
                        .get('card_faces', [{}])[side_ix] \
                        .get(prop_name, props_dict.get(prop_name))
                    return value
                if get_card_prop(card_props, 'power', ix):
                    power = get_card_prop(card_props, 'power', ix)
                    toughness = get_card_prop(card_props, 'toughness', ix)
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
                    property_value = get_card_prop(card_props, property, ix)
                    if skip_next_property:
                        skip_next_property = False
                        continue
                    elif property_value:
                        if 'printed' in property:
                            skip_next_property = True
                        if 'Text' in alias:
                            property_value = property_value.replace('\n', '  \n')
                        text_field += f"""**{alias}**:&nbsp;&nbsp;{property_value}  \n"""
                
                prop_col.markdown(text_field)
            if collection_active_tab == 'Edit card':
                _ = prop_col.selectbox(
                    'Collection:',
                    options=df_lists['list_id'],
                    format_func=lambda x: dict(
                        df_lists[['list_id', 'name']].values
                    )[x],
                    index=int(df_lists[
                        df_lists['list_id'] == st.session_state.current_list_id
                        ].index[0]
                    ),
                    key='v_card_list',
                    on_change=update_table_content_wrapper,
                    kwargs={
                        'entity': 'list',
                        'card_id': st.session_state.selected_card,
                        'column': 'list_id',
                        'value': 'st.session_state.v_card_list',
                    }
                )
                with prop_col:
                    render_card_prop_tab(st.session_state.selected_card)





