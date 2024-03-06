import streamlit as st
from utils import *

def get_content():
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
            button_state = False if dlens_db and ut_db else True
            submitted = st.button('Import', disabled=button_state)
            if submitted and dlens_db and ut_db:
                dlens_db_path, ut_db_path = save_to_temp_dir(dlens_db, ut_db)
                import_delver_lens_cards(dlens_db_path, ut_db_path)
                st.session_state.s_selected_lists = True
                st.rerun()
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
                    for ix, pair in st.session_state.v_delver_lists['edited_rows'].items()
                ]
                ix, [[col, val]]= changes[0]
                if col == 'open':
                    st.session_state.current_list_id = df_delver_lists \
                        .iloc[ix].loc['import_list_id']
                else:
                    list_id = df_delver_lists.iloc[ix].loc['import_list_id']
                    try:
                        val = int(val) if col == 'selected' else val
                        update_table(
                            'import_list', list_id, col, val, db_path='temp/temp_db.db'
                        )
                    except sqlite3.IntegrityError:
                        if col == 'type':
                            type = val
                            name = df_delver_lists.iloc[ix].loc['name']
                        else:
                            type = df_delver_lists.iloc[ix].loc['type']
                            name = val
                        table_container.error(f'{type} "{name}" already exist!')
            table_container = st.container()
            st.session_state.df_delver_lists = table_container.data_editor(
                df_delver_lists,
                key='v_delver_lists',
                hide_index=True,
                column_config={
                    'selected': st.column_config.CheckboxColumn("✔"),
                    'type': st.column_config.SelectboxColumn(
                        'Type', options=['Collection', 'Deck', 'Wishlist'],
                        required=True,  width='small'
                    ),
                    'name': st.column_config.TextColumn('Name', width='medium'),
                    'open': st.column_config.CheckboxColumn('Open'),
                },
                column_order=['selected', 'name', 'type', 'open'],
                on_change=list_callback
            )
            col1, col2 = st.columns(2)
            discard_button = col2.button('Discard import')
            if discard_button:
                del st.session_state.s_selected_lists
                st.rerun()
            import_button = col1.button('Import')
            if import_button:
                msg = check_for_duplicates()
                if len(msg) > 0:
                    table_container.error(msg)