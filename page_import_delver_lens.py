import streamlit as st
from utils import *

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
            submitted = st.button('Import', disabled=button_disable)
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
            if 'current_list_id' not in st.session_state:
                st.session_state.current_list_id = df_delver_lists.iloc[0].loc['import_list_id']
            mask_list = df_delver_lists['import_list_id'] == st.session_state.current_list_id
            df_delver_lists.loc[mask_list, 'open'] = True

            def list_callback():
                changes = [
                    (ix, [(col, val) for col, val in pair.items()])
                    for ix, pair in st.session_state.w_delver_lists['edited_rows'].items()
                ]
                ix, [[col, val]]= changes[0]
                if col == 'open':
                    st.session_state.current_list_id = df_delver_lists \
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
                del st.session_state.s_selected_lists, st.session_state.current_list_id
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
                    f'{st.session_state.w_import_type} {st.session_state.w_import_name} already exist!'
                )
                st.session_state.w_import_type = import_type
                st.session_state.w_import_name = name
        
        header_container = st.container()
        col_name, col_type = header_container.columns([0.7, 0.3])
        
        if 'w_import_name' not in st.session_state:
            st.session_state.w_import_name = name
        _ = col_name.text_input(
            'Name:',
            key='w_import_name',
            on_change=update_table_wrapper,
            kwargs={
                'entity': 'import_list',
                'column': 'name',
                'value': 'st.session_state.w_import_name',
                'id': import_list_id,
                'db_path': 'temp/temp_db.db'
            }
        )

        if 'w_import_type' not in st.session_state:
            st.session_state.w_import_type = import_type
        type_options = ['Deck', 'Collection']
        _ = col_type.selectbox(
            'Type:',
            options=type_options,
            key='w_import_type',
            placeholder='Choose type',
            on_change=update_table_wrapper,
            kwargs={
                'entity': 'import_list',
                'column': 'type',
                'value': 'st.session_state.w_import_type',
                'id': import_list_id,
                'db_path': 'temp/temp_db.db'
            }
        )

        import_tabs = [f'{import_type} info']
        default_tab = f'{import_type} info'
