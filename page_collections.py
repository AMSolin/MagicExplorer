import streamlit as st
from streamlit_searchbox import st_searchbox
from utils import *
import widgets
from card_tabs import *
import uuid

def get_content():
    display_toasts()
    df_lists = get_lists().assign(open=False)
    if 'current_list_id' not in st.session_state:
        st.session_state.current_list_id = df_lists.iloc[0].loc['list_id']
    mask_list = df_lists['list_id'] == st.session_state.current_list_id
    df_lists.loc[mask_list, 'open'] = True

    def check_match_selected_card_and_set(active_tab, card_key):
        result = (st.session_state.get('w_list_tab_bar') == active_tab) \
        and ((card_info := st.session_state.get(card_key)) is not None) \
        and (selected_set := st.session_state.get('w_selected_list_set')) \
        and (card_info.loc['set_code'] != selected_set.split(' ')[0]) \
        and (int(card_info.loc['create_ns']) <= int(selected_set.split(' ')[-1]))
        return result
    
    if ('selected_list_card' not in st.session_state) or \
        (
            (st.session_state.get('selected_list_card') is not None) and
            (st.session_state.get('w_list_tab_bar') not in ['Card info', 'Edit card'])
        ):
            st.session_state.selected_list_card = None
    elif check_match_selected_card_and_set('Edit card', 'selected_list_card'):
        _, _, language, card_uuid, _ = st.session_state.w_selected_list_set.split(' ')
        columns = ['language', 'card_uuid']
        values = [language, uuid.UUID(card_uuid).bytes]
        update_table_content(
            'list', columns, values, st.session_state.selected_list_card
        )
        st.session_state.selected_list_card.rename('need_update', inplace=True)
        del st.session_state.w_selected_list_set
    elif check_match_selected_card_and_set('Add cards', 'searched_list_card'):
        _, _, language, card_uuid, _ = st.session_state.w_selected_list_set.split(' ')
        st.session_state.searched_list_card = search_set_by_name(
            'ignore_name', language, card_uuid
        ).iloc[0]
    
    with st.sidebar:
        table_container = st.container()

        def list_callback():
            changes = [
                (ix, [(col, val) for col, val in pair.items()])
                for ix, pair in st.session_state.w_lists['edited_rows'].items()
            ]
            ix, [[col, val]]= changes[0]
            if col == 'open':
                st.session_state.current_list_id = df_lists.iloc[ix].loc['list_id']
                st.session_state.w_list_tab_bar = None
                st.session_state.selected_list_card = None
            else:
                list_id = df_lists.iloc[ix].loc['list_id']
                try:
                    update_table('list', col, val, list_id)
                except sqlite3.IntegrityError:
                     table_container.error(f'Collection {val} already exist!')  

        _ = table_container.data_editor(
            df_lists, 
            key='w_lists',
            hide_index=True,
            column_config={
                'name': st.column_config.TextColumn(
                    'Collection', width='medium', help='Collection name'
                ),
                'open': st.column_config.CheckboxColumn(
                    'Open', help='Open collection'
                )
            },
            column_order=['name', 'open'],
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
                default_flag = st.checkbox('Mark as primary collection')
                if submitted and new_list.strip() != '':
                    try:
                        add_new_record('list', new_list, is_default=default_flag)
                        st.rerun()
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
                st.warning(
                    'All cards from deleting collection will be also removed!',
                    icon='⚠️'
                )
                if submitted:
                    delete_record('list', deleted_list)
                    del st.session_state.current_list_id
                    st.rerun()
    
    list_side, overview_side = st.columns((0.6, 0.4))

    with list_side:
        df_list_content = get_list_content(st.session_state.current_list_id) \
            .assign(open=False)
        card_id_cols = [
            'list_id', 'card_uuid', 'condition_code', 'foil', 'language',
            'qnty', 'name', 'keyrune_code', 'set_name',
            'set_code', 'card_number', 'language_code', 'create_ns'
        ]
        if st.session_state.selected_list_card is not None:
            mask = (
                df_list_content[card_id_cols[:5]] == \
                    st.session_state.selected_list_card[:5]
            ).all(1)
            df_list_content.loc[mask, 'open'] = True
            if st.session_state.selected_list_card.name == 'need_update':
                st.session_state.selected_list_card.name = ''
                st.session_state.selected_list_card = df_list_content \
                    [card_id_cols].loc[mask].iloc[0]
        
        def update_table_content_wrapper(**kwargs):
            if 'value' not in kwargs:
                # Если функция была вызвана при изменении таблицы
                changes = [
                    (ix, [(column, value) for column, value in pair.items()])
                    for ix, pair in st.session_state.w_list_content['edited_rows'].items()
                ]
                ix, [[column, value]]= changes[0]
                card_id = df_list_content.iloc[ix]
                if column == 'open':
                    if value == True:
                        st.session_state.selected_list_card = card_id \
                            [card_id_cols]
                        st.session_state.w_list_tab_bar = 'Card info'
                    else:
                        st.session_state.selected_list_card = None
                        st.session_state.w_list_tab_bar = 'Collection info'
                    if 'w_selected_list_set' in st.session_state:
                        del st.session_state.w_selected_list_set
                    return
                update_table_content('list', column, value, card_id)
                if (card_id['open']) and (column == 'qnty') and (value == 0):
                    st.session_state.selected_list_card = None
            else:
                # Если фунция была вызвана при изменении виджета
                update_table_content(**kwargs)
                if kwargs['card_id'] is st.session_state.get('selected_list_card'):
                    st.session_state.selected_list_card \
                        .rename('need_update', inplace=True)
        
        _ = st.data_editor(
            df_list_content,
            key='w_list_content',
            height=843,
            hide_index=True,
            column_config={
                'list_id': None,
                'card_uuid': None,
                'language': None,
                'qnty': st.column_config.NumberColumn(
                    'Q', min_value=0, step=1, help='Quantity'
                ),
                'name': st.column_config.TextColumn(
                    'Name', help='Card name', width='medium'
                ),
                'card_number': None,
                'type': st.column_config.TextColumn(
                    'Type', help='Card type', width='medium'
                ),
                'set_code': st.column_config.TextColumn(
                    'Set', help='Set'
                ),
                'language_code': None,
                'set_name': None,
                'keyrune_code': None,
                'rarity': None,
                'mana_cost': st.column_config.TextColumn(
                    'Cost', help='Mana cost'
                ),
                'foil': None,
                'condition_code': None,
                'create_ns': None,
                'open': st.column_config.CheckboxColumn(
                    'Open',  help='Open card'
                )
            },
            disabled=[
                'name', 'type', 'language_code', 'set_code', 'rarity', 
                'mana_cost', 'condition_code']
            ,
            on_change=update_table_content_wrapper,
            kwargs={
                'df_list_content': df_list_content, 'card_id_cols': card_id_cols
            }
        )
    with overview_side:
        
        def update_table_wrapper(**kwargs):
            try:
                update_table(**kwargs)
            except sqlite3.IntegrityError:
                list_name_container.error(
                    f'Collection {st.session_state.w_list_name} already exist!'
                )
                st.session_state.w_list_name = selected_list['name']
        
        default_args = {
            'entity':'list', 'callback_function':update_table_wrapper,
            'index_id':st.session_state.current_list_id,
        }

        selected_list = df_lists \
            .loc[
                mask_list,
                [
                    'name', 'creation_date', 'note', 'player_id',
                    'owner', 'is_default_list', 'is_wish'
                ]
            ] \
            .iloc[0].to_dict()
        
        list_name_container = st.container()
        render_entity_header(
            list_name_container, counter=df_list_content['qnty'].sum(),
            **default_args, **selected_list
        )

        collection_tabs = ['Collection info', 'Add cards']
        default_tab = 'Collection info'
        if st.session_state.selected_list_card is not None:
            collection_tabs += ['Card info', 'Edit card']
            default_tab = 'Card info'
        collection_active_tab = show_tab_bar(
            collection_tabs,
            tabs_size=[1.2, 1, 1, 0.8],
            default=default_tab,
            key='w_list_tab_bar'
        )

        if collection_active_tab == 'Collection info':
            render_entity_prop_tab(**default_args,**selected_list)

        if collection_active_tab == 'Add cards':
            search_bar, exact_seach_box = st.columns((0.7, 0.3))

            def reset_searchbar():
                del st.session_state.w_searched_list_card

            exact_match = exact_seach_box.checkbox(
                'Exact match',
                value=False,
                on_change=reset_searchbar
            )
            searh_function = to_lower_and_exact_search if exact_match \
                else to_lower_and_substring_search
            with search_bar:
                searched_list_card = st_searchbox(
                    search_function=searh_function,
                    placeholder="Enter card name",
                    key="w_searched_list_card",
                    clearable=True
                )
            
            img_col, prop_col =  st.columns((0.5, 0.5))
            if searched_list_card:
                # Workaround for realize callback function in serchbox
                # We want to know, when widget value has changed
                is_new_search = False
                if st.session_state.get('prev_searched_list_card', []) != searched_list_card:
                    is_new_search = True
                    st.session_state.prev_searched_list_card = searched_list_card
                
                with prop_col:
                    if ('searched_list_card' in st.session_state and
                        not is_new_search):
                        render_card_prop_tab(
                            'list',
                            st.session_state.searched_list_card,
                            update_searched_card
                        )
                    else:
                        render_card_prop_tab(
                            'list',
                            searched_list_card,
                            update_searched_card
                        )
                    
                    with st.form('add card submit form'):
                        card_uuid, condition_code, foil, language = \
                            st.session_state.searched_list_card \
                                .loc[['card_uuid', 'condition_code',
                                      'foil', 'language']]
                        
                        current_qnty = df_list_content[
                                (df_list_content['card_uuid'] == card_uuid) &
                                (df_list_content['condition_code'] == condition_code) &
                                (df_list_content['foil'] == foil) &
                                (df_list_content['language'] == language)
                            ] \
                            ['qnty'].sum()
                        
                        qnty = st.number_input(
                            label='Enter quantity:',
                            value=current_qnty,
                            min_value=0, max_value=99, step=1
                        )
                        st.write('')
                        if st.form_submit_button('Update collection'):
                            st.session_state.searched_list_card['list_id'] = \
                                st.session_state.current_list_id
                            st.session_state.searched_list_card['qnty'] = qnty
                            update_table_content(
                                'list', 'qnty', qnty,
                                st.session_state.searched_list_card
                            )
                            st.rerun()
                
                with img_col:
                    card_api_key = st.session_state.searched_list_card \
                        .loc[['set_code', 'card_number', 'language_code']] \
                        .to_list()
                    card_props = get_card_properties(*card_api_key)
                    side_idx = render_card_img_tab(card_props)
                

        if collection_active_tab in collection_tabs[2:]:
            img_col, prop_col =  st.columns((0.5, 0.5))
            card_api_key = st.session_state.selected_list_card \
                .loc[['set_code', 'card_number', 'language_code']] \
                .to_list()
            card_props = get_card_properties(*card_api_key)
            with img_col:
                side_idx = render_card_img_tab(card_props)
            if collection_active_tab == 'Card info':
                text_field = get_card_description(card_props, side_idx)
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
                    key='w_card_list',
                    on_change=update_table_content_wrapper,
                    kwargs={
                        'entity': 'list',
                        'column': 'list_id',
                        'value': 'st.session_state.w_card_list',
                        'card_id': st.session_state.selected_list_card
                    }
                )
                with prop_col:
                    render_card_prop_tab(
                        'list',
                        st.session_state.selected_list_card,
                        update_table_content_wrapper
                    )