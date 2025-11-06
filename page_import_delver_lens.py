import streamlit as st
from utils import *
from card_tabs import *

def get_content():
    display_toasts()
    with st.sidebar:
        if 's_selected_lists' not in st.session_state:
            dlens_db = st.file_uploader(
                'Choose dlens file:',
                key='v_dlens_db_uploader',
                type='dlens'
                )
            ut_db = st.file_uploader(
                'Choose ut.db file:',
                key='v_ut_db_uploader',
                type='db'
                )
            button_disable = False if dlens_db and ut_db else True
            submitted = st.button('Load', disabled=button_disable)
            if submitted and dlens_db and ut_db:
                dlens_db_path, ut_db_path = save_to_temp_dir(dlens_db, ut_db)
                temp_import_delver_lens_cards(dlens_db_path, ut_db_path)
                check_for_tokens()
                st.session_state.s_selected_lists = True
                st.rerun()
            else:
                return
        else:
            df_delver_lists = get_import_names() \
                .assign(open=False)
            if 'current_import_list_id' not in st.session_state:
                st.session_state.current_import_list_id = df_delver_lists.iloc[0].loc['import_list_id']
            mask_list = df_delver_lists['import_list_id'] == st.session_state.current_import_list_id
            df_delver_lists.loc[mask_list, 'open'] = True

            def list_callback():
                changes = [
                    (ix, [(col, val) for col, val in pair.items()])
                    for ix, pair in st.session_state.w_delver_lists['edited_rows'].items()
                ]
                ix, [[col, val]]= changes[0]
                if col == 'open':
                    st.session_state.current_import_list_id = df_delver_lists \
                        .iloc[ix].loc['import_list_id']
                else:
                    list_id = df_delver_lists.iloc[ix].loc['import_list_id']
                    update_table(
                        'import_list', col, int(val), list_id,
                        db_path='temp/temp_db.db'
                    )
                    st.session_state.w_select_all_lists = False
            table_container = st.container()
            st.session_state.df_delver_lists = table_container.data_editor(
                df_delver_lists,
                key='w_delver_lists',
                hide_index=True,
                column_config={
                    'selected': st.column_config.CheckboxColumn(
                        '✔', help='Сheck to import into collections / decks'
                    ),
                    'name': st.column_config.TextColumn(
                        'Name', width='medium', help='Collection / deck name'
                    ),
                    'open': st.column_config.CheckboxColumn(
                        'Open', help='Open collection / deck '
                    ),
                },
                disabled=['name'],
                column_order=['selected', 'name', 'open'],
                on_change=list_callback
            )
            _, col_checkbox = st.columns([0.04, 0.96])
            _ = col_checkbox.checkbox(
                'Select all',
                key='w_select_all_lists',
                on_change=update_table,
                kwargs={
                    'entity': 'import_list',
                    'column': 'selected',
                    'value': 'int(st.session_state.w_select_all_lists)',
                    'db_path': 'temp/temp_db.db'
                }
            )
            col_import_btn, col_discard_brn = st.columns(2)
            discard_button = col_discard_brn.button('Discard import', type='primary')
            if discard_button:
                del st.session_state.s_selected_lists, st.session_state.current_import_list_id
                st.rerun()
            import_button = col_import_btn.button('Import')
            if import_button:
                msg = check_for_duplicates()
                if len(msg) > 0:
                    table_container.error(msg)
                else:
                    import_delver_lens_cards()
                    st.rerun()
    
    table_side, overview_side = st.columns((0.6, 0.4))
    with overview_side:
        
        def update_table_wrapper(**kwargs):
            try:
                update_table(**kwargs)
            except sqlite3.IntegrityError:
                header_container.error(
                    f'{st.session_state.w_import_list_type} {st.session_state.w_import_list_name} already exist!'
                )
                st.session_state.w_import_list_type = selected_import_list['entity_type']
                st.session_state.w_import_list_name = selected_import_list['name']

        default_args = {
            'entity':'import_list', 'callback_function':update_table_wrapper,
            'index_id':st.session_state.current_import_list_id, 'db_path':'temp/temp_db.db'
        }

        selected_import_list =  df_delver_lists \
            .loc[
                mask_list,
                [
                    'name', 'entity_type', 'note', 'player_id', 'parent_list', 
                    'creation_date', 'is_wish'
                ]
            ] \
            .iloc[0].to_dict()
        
        header_container = st.container()
        render_entity_header(
            header_container, **default_args, **selected_import_list
        )

        import_tabs = ['Options']
        default_tab = 'Options'
        # if st.session_state.selected_import_card is not None:
        #     import_tabs += ['Card info', 'Edit card']
        #     default_tab = 'Card info'
        deck_active_tab = show_tab_bar(
            import_tabs,
            tabs_size=[1.2, 1, 1, 0.8],
            default=default_tab,
            key='w_delver_import_tab_bar'
        )


        if deck_active_tab == 'Options':
            render_entity_prop_tab(**default_args,**selected_import_list)
           