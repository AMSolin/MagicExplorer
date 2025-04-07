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
            button_block = False if dlens_db and ut_db else True
            submitted = st.button('Import', disabled=button_block)
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
                    for ix, pair in st.session_state.v_delver_lists['edited_rows'].items()
                ]
                ix, [[col, val]]= changes[0]
                if col == 'open':
                    st.session_state.current_list_id = df_delver_lists \
                        .iloc[ix].loc['import_list_id']
                else:
                    list_id = df_delver_lists.iloc[ix].loc['import_list_id']
                    update_table(
                        'import_list', list_id, col, int(val), db_path='temp/temp_db.db'
                    )
            table_container = st.container()
            st.session_state.df_delver_lists = table_container.data_editor(
                df_delver_lists,
                key='v_delver_lists',
                hide_index=True,
                column_config={
                    'selected': st.column_config.CheckboxColumn(
                        '✔', help='check for import to collection / deck'
                    ),
                    'name': st.column_config.TextColumn(
                        'Name', width='medium', help='Collection / deck name'
                    ),
                    'open': st.column_config.CheckboxColumn(
                        'Open', help='Open collection / deck '
                    ),
                },
                column_order=['selected', 'name', 'open'],
                on_change=list_callback
            )
            col1, col2 = st.columns(2)
            discard_button = col2.button('Discard import', type='primary')
            if discard_button:
                del st.session_state.s_selected_lists
                st.rerun()
            import_button = col1.button('Import')
            if import_button:
                msg = check_for_duplicates()
                if len(msg) > 0:
                    table_container.error(msg)
                else:
                    import_delver_lens_cards()
                    st.rerun()
    
    table_side, overview_side = st.columns((0.6, 0.4))
    with table_side:
        df_import_content = get_import_content(
            st.session_state.current_list_id
        )
        _ = st.dataframe(
                    df_delver_lists.drop(columns=['create_ns']),
                    # key=f'w_import_content',
                    hide_index=True,
                    use_container_width=False,
                    # column_order=['name','qnty'],
                )
        _ = st.dataframe(
                    df_import_content,
                    key=f'w_import_content',
                    hide_index=True,
                    use_container_width=False,
                    column_order=['name','qnty'],
                )
    with overview_side:

        import_list_id, name, type, owner, parent_list, \
            creation_date =  df_delver_lists \
            .loc[
                mask_list,
                [
                    'import_list_id', 'name', 'type', 'owner', 'parent_list',
                    'creation_date'
                ]
            ] \
            .values.ravel()
        
        entity_map = {
            'Collection': ['list', 0],
            'Wish list': ['list', 0],
            'Deck': ['deck', 0],
            'Wish deck': ['deck', 0]
        }
        entity, is_wished = entity_map[type]
        
        def update_table_wrapper(**kwargs):
            try:
                update_table(**kwargs)
            except sqlite3.IntegrityError:
                deck_name_container.error(
                    f'{type} {st.session_state.w_import_name} already exist!'
                )
                st.session_state.w_import_name = name
        
        deck_name_container = st.container()
        _ = deck_name_container.text_input(
            'Name:',
            value=name,
            key='w_import_name',
            on_change=update_table_wrapper,
            kwargs={
                'entity': 'import_list',
                'id': import_list_id,
                'column': 'name',
                'value': 'st.session_state.w_import_name',
                'db_path': 'temp/temp_db.db'
            }
        )

        # deck_tabs = ['Deck info', 'Deck builder', 'Add cards']
        # default_tab = 'Deck info'
        # if st.session_state.selected_deck_card is not None:
        #     deck_tabs += ['Card info', 'Edit card']
        #     default_tab = 'Card info'
        # deck_active_tab = show_tab_bar(
        #     deck_tabs,
        #     tabs_size=[1, 1.2, 1, 1, 1],
        #     default=default_tab,
        #     key='v_deck_tab_bar'
        # )

        # if deck_active_tab == 'Deck info':
        #     col_owner, col_creation_date, col_wish_deck = \
        #         st.columns([0.4, 0.3, 0.3])
        #     df_players = get_players()[['player_id', 'name']]
        #     if owner is not None:
        #         idx = int(
        #             df_players[
        #                 df_players['player_id'] == player_id
        #             ].index[0]
        #         )
        #     else:
        #         idx = None
        #     _ = col_owner.selectbox(
        #         'Owner:',
        #         options=df_players['player_id'],
        #         format_func=lambda x: dict(df_players.values)[x],
        #         index=idx,
        #         key='v_deck_owner',
        #         placeholder='Choose owner',
        #         on_change=update_table_wrapper,
        #         kwargs={
        #             'entity': 'deck',
        #             'default_value': None,
        #             'id': st.session_state.current_deck_id,
        #             'column': 'player_id',
        #             'value': 'st.session_state.v_deck_owner'
        #         }
        #     )

        #     _ = col_creation_date.date_input(
        #         'Creation date:',
        #         value=creation_dtm.to_pydatetime(),
        #         format="DD.MM.YYYY",
        #         key='v_deck_creation_date',
        #         on_change=update_table_wrapper,
        #         kwargs={
        #             'entity': 'deck',
        #             'default_value': None,
        #             'id': st.session_state.current_deck_id,
        #             'column': 'creation_date',
        #             'value': 'st.session_state.v_deck_creation_date'
        #         }
        #     )

        #     col_wish_deck.write('')
        #     col_wish_deck.write('')
        #     _ = col_wish_deck.checkbox(
        #         'Mark as wish deck',
        #         value=is_wish_deck,
        #         key='v_is_wish_deck',
        #         on_change=update_table_wrapper,
        #         kwargs={
        #             'entity': 'deck',
        #             'id': st.session_state.current_deck_id,
        #             'column': 'is_wish_deck',
        #             'value': 'int(st.session_state.v_is_wish_deck)'
        #         }
        #     )

        #     _ = st.text_area(
        #         'Deck note',
        #         value=note,
        #         key='v_deck_note',
        #         placeholder='Add your notes here',
        #         max_chars=256,
        #         height=68,
        #         on_change=update_table_wrapper,
        #         kwargs={
        #             'entity': 'deck',
        #             'id': st.session_state.current_deck_id,
        #             'column': 'note',
        #             'value': 'st.session_state.v_deck_note'
        #         }
        #     )