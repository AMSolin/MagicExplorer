from __future__ import annotations
import sqlite3
import uuid
import pandas as pd
import requests
import json
import streamlit as st
import datetime
import time
import os
from typing import List, Tuple

sqlite3.register_adapter(uuid.UUID, lambda u: u.bytes_le)
sqlite3.register_converter('guid', lambda b: uuid.UUID(bytes_le=b))

class Db:
    def __init__(self, db: str, detect_types=0):
        self.conn = sqlite3.connect(
            database=db if db == ':memory:' else f'./data/{db}',
            isolation_level=None,
            detect_types=detect_types
        )
        self.csr = self.conn.cursor()

    def execute(self, *args):
        return self.csr.execute(*args)

    def executemany(self, *args):
        return self.csr.executemany(*args)
    
    def executescript(self, sql):
        self.csr.executescript(sql)

    def read_sql(self, query, parse_dates=None):
        return pd.read_sql(query, self.conn, parse_dates=parse_dates)
    
    def close_connect(self):
        self.conn.close()

    def __del__(self):
        self.close_connect()

def display_toasts():
    if 'last_actions' not in st.session_state:
            st.session_state.last_actions = []
    else:
        while st.session_state.last_actions:
            st.toast(st.session_state.last_actions.pop(0))

@st.cache_data
def search_cards(search_params: dict):
    where_clause = []
    if color_list := search_params['color_list']:
        colors = ''.join(sorted(color_list))
        if search_params['multicolor_option'] == 'With a chosen color(s)':
            expr = f"c.colors GLOB '*[{colors}]*'"
        elif search_params['multicolor_option'] == 'Any of the chosen color(s)':
            all_colors = ['B', 'G', 'R', 'U', 'W', 'C', 'X']
            other_colors = ''.join(
                sorted(list(set(all_colors).difference(set(color_list))))
            )
            expr = f"c.colors not GLOB '*[{other_colors}]*'"
        elif search_params['multicolor_option'] == 'All of the chosen color(s)':
            expr = f"c.colors GLOB '{colors}'"
        where_clause.append(expr)
    if rarity_list := search_params['rarity_list']:
        rarity = "', '".join(rarity_list)
        expr = f"c.rarity in ('{rarity}')"
        where_clause.append(expr)
    for key in ['name', 'type', 'text']:
        if value := search_params[f'card_{key}']:
            expr = f'lower_udf(c.{key}) like "%{value}%"'
            where_clause.append(expr)
    for key in ['mana_value', 'power', 'toughness']:
        if value := search_params[f'{key}_val']:
            operator = search_params[f'{key}_op']
            expr = f'c.{key} {operator} {value}'
            where_clause.append(expr)

    query = f"""
        select
            name,
            type,
            mana_cost,
            case
                when power <> ''
                    then (power || ' / ' || toughness)
                else ''
            end as pt
        from (
            select
                name,
                type,
                mana_cost,
                power,
                toughness,
                row_number() over (
                    partition by c.card_common_id
                    order by search_priority
                ) as row_number
            from card_unique_metadata as c
            where {' and '.join(where_clause)}
        ) as t
        where row_number = 1
        order by
            name
    """
    csr = Db('app_data.db')
    def sqlite_lower(value_):
            return value_.lower()
    csr.conn.create_function("lower_udf", 1, sqlite_lower)
    result = csr.read_sql(query).assign(create_ns = str(time.time_ns()))
    return result

def search_cards_in_lc(name):
    csr = Db('user_data.db')
    csr.execute("attach database './data/app_data.db' as ad")
    result = csr.read_sql(
    f"""
        select
            coalesce(fd.name, ca.name) as name,
            li.name as list_name,
            lc.qnty
        from list_content as lc
        left join lists as li
            on lc.list_id = li.list_id
        left join cards as ca
            on lc.card_uuid = ca.card_uuid
        left join foreign_data as fd
            on lc.card_uuid = fd.card_uuid and lc.language = fd.language
        left join sets as se
            on ca.set_code = se.set_code
        left join languages as la
            on lc.language = la.language
        where
            coalesce(fd.name, ca.name) = '{name}'
            and coalesce(ca.side, 'a') = 'a'
        order by ca.name
    """)
    result['create_ns'] = str(time.time_ns())
    return result

def to_lower_and_substring_search(substr_card: str):
    return to_lower_and_exact_search(f'%{substr_card}%')

def to_lower_and_exact_search(substr_card: str):
    return search_card_by_name(substr_card.lower())


def search_card_by_name(substr_card: str):
    if len(substr_card) > 0:
        csr = Db('app_data.db')
        def sqlite_lower(value_):
            return value_.lower()
        csr.conn.create_function("lower_udf", 1, sqlite_lower)
        result = csr.read_sql(
        f"""
            select name, language
            from card_names
            where lower_udf(name) like "{substr_card}"
            limit 30
        """
        )
        result = [(row[0] + f' ({row[1]})', row.tolist()) for row in result.values]
    else:
        result = []
    return result

def search_set_by_name(
    card_name: str, card_lang: str, card_uuid: str=None
):
    csr = Db('app_data.db')
    card_name = card_name.replace("'", "''")
    if card_uuid is not None:
        card_condition = f"c.card_uuid = X'{card_uuid}'"
    else:
        card_condition = f"c.name = '{card_name}'"

    if card_lang in ['English', 'Phyrexian']:
        query = f"""
            select
                c.name,
                c.set_code,
                lower(s.keyrune_code) as keyrune_code,
                s.name as set_name,
                c.number as card_number,
                c.language,
                language_code,
                c.card_uuid,
                'NM' as condition_code,
                0 as foil,
                'Main' as deck_type_name,
                0 as is_commander,
                row_number() over (
                    partition by c.set_code order by c.number
                ) as row_number
            from cards as c
            left join sets as s
                on s.set_code = c.set_code
            left join languages as l
                on c.language = l.language
            where
                {card_condition}
                and c.language in ('English', 'Phyrexian')
                and coalesce(c.side, 'a') = 'a'
            order by s.release_date desc, cast(c.number as int)
        """
    else:
        # TODO missing prints, those does not have eng version,
        # like spanish Mana Leak at set Salvat 2011
        query = f"""
            with foreing_cards as (
                select
                    name,
                    language,
                    card_uuid
                from foreign_data as c
                where
                    {card_condition}
                    and language = '{card_lang}'
            )
            select
                coalesce(f.name, c.name) as name,
                c.set_code,
                lower(s.keyrune_code) as keyrune_code,
                s.name as set_name,
                c.number as card_number,
                coalesce(f.language, c.language) as language,
                language_code,
                c.card_uuid,
                'NM' as condition_code,
                0 as foil,
                'Main' as deck_type_name,
                0 as is_commander,
                row_number() over (
                    partition by 
                        c.set_code 
                    order by 
                        case when f.language is not NULL then 0
                            else 1
                        end,
                        c.number
                ) as row_number
            from cards as c
            inner join (
                select distinct ct.name, ct.language
                from cards as ct
                inner join foreing_cards as fct
                    on ct.card_uuid = fct.card_uuid
            ) as t
                on c.name = t.name and c.language = t.language
            left join foreing_cards as f
                on c.card_uuid = f.card_uuid
            left join sets as s
                on s.set_code = c.set_code
            left join languages as l
                on coalesce(f.language, c.language) = l.language
            where
                coalesce(c.side, 'a') = 'a'
                {'' if card_uuid is None else f"and {card_condition}"}
            order by s.release_date desc, cast(c.number as int)
        """
    result = csr.read_sql(query).assign(create_ns = str(time.time_ns()))
    return result

def search_card_numbers(card_uuid, card_language, card_set_code):
    csr = Db('app_data.db')
    result = csr.read_sql(
    f"""
        select distinct
            c.number as card_number,
            c.card_uuid
        from cards as c
        inner join (
            select name
            from cards
            where
                card_uuid = X'{card_uuid}'
                and coalesce(side, 'a') = 'a'
        ) as n
            on c.name = n.name
        left join (
            select
                card_uuid,
                language
            from foreign_data
            where card_uuid = X'{card_uuid}'
        ) as f
            on c.card_uuid = f.card_uuid
        where
            c.set_code = '{card_set_code}'
            and (
                c.language = '{card_language}'
                or f.language = '{card_language}'
            )
            and coalesce(c.side, 'a') = 'a'
        order by cast(c.number as int)
    """)
    return result


def search_languages_by_card_uuid(card_uuid):
    csr = Db('app_data.db')
    result = csr.read_sql(
    f"""
        select distinct
            language
        from (
            select
                language
            from cards as c
            where card_uuid = X'{card_uuid}'
            union all
            select
                language
            from foreign_data
            where card_uuid = X'{card_uuid}'
        ) as t
    """)
    return result['language'].to_list()

def generate_set_dict(
        entity: str, df_set_codes: pd.DataFrame, selected_card: pd.Series=None
    ):
    sets_dict = {}
    df_set_codes = df_set_codes \
        [df_set_codes['row_number'] == 1] \
        [['set_code', 'keyrune_code', 'card_number', 'language', 'card_uuid', 'create_ns']]
    if selected_card is not None:
        st.session_state[f'w_selected_{entity}_set'] = ' '.join(
            selected_card.loc[['set_code', 'card_number', 'language', 'card_uuid', 'create_ns']] \
                .apply(lambda x: x if isinstance(x, str) else x.hex()).values
        )
    for row in df_set_codes.itertuples():
        idx, set_code, keyrune_code, card_number, language, card_uuid, create_ns = row
        css_id = f'{set_code} {card_number} {language} {card_uuid.hex()} {create_ns}'
        if f'w_selected_{entity}_set' not in st.session_state and idx == 0:
            st.session_state[f'w_selected_{entity}_set'] = css_id
        sets_dict[css_id] = f'<a id="{css_id}" class="ss ss-{keyrune_code} ss-2x"></a> '
    return sets_dict

def generate_css_set_icons(entity, sets_dict):
    css = '<link href="//cdn.jsdelivr.net/npm/keyrune@latest/css/keyrune.css" rel="stylesheet" type="text/css" />'
    for css_id, set_css in sets_dict.items():
        if css_id.split(' ')[0] == st.session_state[f'w_selected_{entity}_set'].split(' ')[0]:
            set_css = f'<span style="color: orange">{set_css}</span>'
        css+= set_css
    return css

@st.cache_data(show_spinner=False)
def get_card_properties(set_code, card_number, lang):
    api_url = 'https://api.scryfall.com/cards'
    r = requests.get(f'{api_url}/{set_code.lower()}/{card_number}/{lang}').text
    card_props = json.loads(r)
    return card_props

def get_card_images(df, selected_set):
    content = ''
    df_filtered = df[df['set_code'] == selected_set.split()[0]] \
        [['set_code', 'card_number', 'language_code']]
    for row in df_filtered.itertuples(index=False):
        set_code, card_number, lang = row
        card_props = get_card_properties(set_code, card_number, lang)
        if card_props.get('card_faces'):
            side = st.radio('_', ['Front', 'Back'], label_visibility='hidden', horizontal=True, key=f'w_import_card_side {set_code} {card_number} {lang}')
            ix = 0 if side == 'Front' else 1
            uri = card_props['card_faces'][ix]['image_uris']['normal'] #TODO add change img with placeholder
        else:
            uri = card_props['image_uris']['normal'] #TODO add change img with placeholder
        content += f'<a href="#" id="{set_code} {card_number} {lang} {time.time_ns()}"><img width="24%" src="{uri}"></a>\n'
    return content

def get_players():
    csr = Db('user_data.db')
    result = csr.read_sql('select * from players order by player_id')
    result['create_ns'] = time.time_ns()
    return result

def get_lists():
    csr = Db('user_data.db')
    result = csr.read_sql(
    """
        select
            l.list_id,
            l.name,
            datetime(l.creation_date, 'unixepoch', 'localtime') as creation_date,
            l.note,
            l.is_default_list,
            l.player_id,
            l.is_wish,
            p.name as owner
        from lists as l
        left join players as p
            on l.player_id = p.player_id
        order by is_default_list desc, l.creation_date
    """,
    parse_dates='creation_date')
    result['create_ns'] = time.time_ns()
    return result

def get_list_content(list_id):
    csr = Db('user_data.db')
    csr.execute("attach database './data/app_data.db' as ad")
    result = csr.read_sql(
    f"""
        select
            lc.list_id,
            lc.card_uuid,
            lc.condition_code,
            lc.language,
            lc.qnty,
            coalesce(fd.name, ca.name) as name,
            ca.number as card_number,
            coalesce(fd.type, ca.type) as type,
            la.language_code,
            ca.set_code,
            lower(se.keyrune_code) as keyrune_code,
            se.name as set_name,
            ca.rarity,
            ca.mana_cost,
            lc.foil
        from list_content as lc
        left join cards as ca
            on lc.card_uuid = ca.card_uuid
        left join foreign_data as fd
            on lc.card_uuid = fd.card_uuid and lc.language = fd.language
        left join sets as se
            on ca.set_code = se.set_code
        left join languages as la
            on lc.language = la.language
        where
            list_id = {list_id}
            and coalesce(ca.side, 'a') = 'a'
        order by ca.name
    """)
    result['create_ns'] = str(time.time_ns())
    return result

def get_deck_content(deck_id):
    csr = Db('user_data.db')
    csr.execute("attach database './data/app_data.db' as ad")
    result = csr.read_sql(
    f"""
        select
            dc.deck_id,
            dc.deck_type_name,
            dc.card_uuid,
            dc.condition_code,
            dc.language,
            dc.qnty,
            dc.is_commander,
            coalesce(fd.name, ca.name) as name,
            ca.number as card_number,
            coalesce(fd.type, ca.type) as type,
            la.language_code,
            se.set_code,
            lower(se.keyrune_code) as keyrune_code,
            se.name as set_name,
            ca.rarity,
            ca.mana_cost,
            dc.foil
        from deck_content as dc
        left join cards as ca
            on dc.card_uuid = ca.card_uuid
        left join foreign_data as fd
            on dc.card_uuid = fd.card_uuid and dc.language = fd.language
        left join sets as se
            on ca.set_code = se.set_code
        left join languages as la
            on dc.language = la.language
        where
            deck_id = {deck_id}
            and coalesce(ca.side, 'a') = 'a'
        order by ca.name
    """)
    result['create_ns'] = str(time.time_ns())
    return result

def get_decks():
    csr = Db('user_data.db')
    result = csr.read_sql(
    """
        select
            deck_id,
            name,
            datetime(creation_date, 'unixepoch', 'localtime') as creation_date,
            note,
            player_id,
            is_wish
        from decks
        order by creation_date
    """,
    parse_dates='creation_date')
    result['create_ns'] = time.time_ns()
    return result

def set_default_value(entity, name: str, cursor=None):
    csr = Db('user_data.db') if cursor is None else cursor
    csr.execute(
    f"""
        update {entity}s
        set is_default_{entity} = case
            when name = '{name}'
                then 1
            else 0 end
    """)

def add_new_record(
        entity: str, name: str, creation_date: int=None, is_default: bool=False,
        cursor: Db=None
    ):
    csr = cursor if cursor else Db('user_data.db')
    creation_date = creation_date if creation_date else r"strftime('%s','now')"
    if entity == 'player':
        csr.execute(
        f"""
            insert into players (name, is_default_player)
            values ('{name}', {int(is_default)})
        """)
    elif entity == 'list':
        csr.execute(
        f"""
            insert into lists (
                name, creation_date, is_default_list
            )
            values (
                '{name}', {creation_date}, {int(is_default)}
            )
        """)
    elif entity == 'deck':
        csr.execute(
        f"""
            insert into decks (name, creation_date)
            values ('{name}', {creation_date})
        """)
    else:
        raise ValueError(f'Unknown {entity} entity!')
    if is_default:
        set_default_value(entity, name, csr)
    st.session_state.last_actions.append(
            f'{entity.capitalize()} {name} was added!'
        )

def delete_record(entity: str, name: str):
    csr = Db('user_data.db')
    csr.executescript(
    f"""
        PRAGMA foreign_keys=ON;
        delete from {entity}s 
        where name = '{name}'
    """)
    if entity in ['list', 'player']:
        default_value, is_default = csr.execute(
        f"""
            select name, is_default_{entity}
            from {entity}s
            order by is_default_{entity} desc, {entity}_id
        """).fetchone()
        if is_default == 0:
            set_default_value(entity, default_value, csr)
    st.session_state.last_actions.append(
            f'{entity.capitalize()} {name} was deleted!'
        )

def update_table(
        entity, column, value=None, id=None, default_value=None,
        db_path=None
    ):
    if isinstance(value, str) and 'session_state' in value:
        value = eval(value)
    if isinstance(value, datetime.date):
        value = int(
            datetime.datetime(value.year, value.month, value.day) \
                .timestamp()
        )
    csr = Db(db_path if db_path else 'user_data.db')
    if column == f'is_default_{entity}':
        set_default_value(entity, default_value, csr)
    else:
        condition = f'where {entity}_id = {id}' if id else ''
        csr.execute(
        f"""
            update {entity}s
            set {column} = '{value}'
            {condition}
        """)

def update_table_content(entity, column, value, card_id):
    if isinstance(value, str) and 'session_state' in value:
        value = eval(value)
    csr = Db('user_data.db')
    if not ((column == 'qnty') and (value > 0)):
        #Если установили qnty = 0 или изменили другое поле
        csr.execute(
        f"""
            delete from {entity}_content
            where
                {entity}_id = {card_id[f'{entity}_id']}
                and card_uuid = X'{card_id['card_uuid'].hex()}'
                and condition_code = '{card_id['condition_code']}'
                and foil = {card_id['foil']}
                and language = '{card_id['language']}'
        """
        + (
                f"and deck_type_name = '{card_id['deck_type_name']}'"
                if entity == 'deck' else ""
            )
        )

        if isinstance(column, list):
            for i in range(len(column)):
                card_id[column[i]] = value[i]
        else:
            card_id[column] = value
    if not ((column == 'qnty') and (value == 0)):
        card_dict = card_id.to_dict()
        #Если не устанаваливали qnty = 0
        if column != 'qnty':
            #В случае конфликта при изменении ключевых полей
            #сложим новое и прежнее значения qnty вместе
            add_method = 'qnty + excluded.qnty'
        else:
            #Иначе в случае конфликта обновим значение qnty
            add_method = 'excluded.qnty'
            card_dict[column] = value
        columns = csr.read_sql(f'select * from {entity}_content limit 1').columns
        primary_key = [col for col in columns if col not in ['qnty', 'is_commander']] 
        csr.execute(
        f"""
            insert into {entity}_content ({', '.join(columns)}) 
            values({', '.join('? ' for _ in range(len(columns)))})
            on conflict ({', '.join(primary_key)})
            do update set qnty = {add_method}
        """, 
        [card_dict[value] for value in columns]
        )

def manual_import_cards_to_user_data(
    df, list_action, list_name, deck_action, deck_name
):
    df = df.assign(list_name=list_name, deck_name=deck_name)
    csr = Db(':memory:', detect_types=sqlite3.PARSE_DECLTYPES)
    csr.execute("attach database './data/user_data.db' as ud")
    csr.execute("attach database './data/app_data.db' as ad")
    csr.execute(
    """
        create table card_import (
            set_code text,
            number text,
            language_code text,
            qnty integer,
            foil integer,
            condition_code text,
            deck_type_name text,
            list_name text,
            deck_name text
        )
    """)
    csr.executemany(
        """
        insert into card_import
        values (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        df[[
            'Set code',
            'Card number',
            'Language',
            'Qnty',
            'Foil',
            'Condition',
            'Deck type',
            'list_name',
            'deck_name'
        ]].values
    )
    if list_action == 'New':
        add_new_record('list', list_name, cursor=csr)
    if deck_action == 'New':
        add_new_record('deck', deck_name, cursor=csr)
    if list_action != 'Skip':
        csr.execute(
        f"""
            insert into list_content (
                list_id,
                card_uuid,
                condition_code,
                foil,
                language,
                qnty
            )
            select
                li.list_id,
                ca.card_uuid,
                ci.condition_code,
                ci.foil,
                la.language,
                ci.qnty
            from card_import as ci
            left join lists as li
                on ci.list_name = li.name
            left join ad.cards as ca
                on ci.set_code = ca.set_code
                and ci.number = ca.number
            left join languages as la
                on ci.language_code = la.language_code
            on conflict (
                list_id, card_uuid, condition_code,
                foil, language
            ) do update set
                qnty = qnty + excluded.qnty
        """)
        st.session_state.last_actions.append(
            f'{df["Qnty"].sum()} cards added to list {list_name}'
        )
    if deck_action != 'Skip':
        csr.execute(
        f"""
            insert into deck_content ( --#TODO add commander column 
                deck_id,
                card_uuid,
                condition_code,
                deck_type_name,
                qnty,
                foil,
                language
            )
            select
                de.deck_id,
                ca.card_uuid,
                ci.condition_code,
                ci.deck_type_name,
                ci.qnty,
                ci.foil,
                la.language
            from card_import as ci
            left join decks as de
                on ci.deck_name = de.name
            left join ad.cards as ca
                on ci.set_code = ca.set_code 
                    and ci.number = ca.number
            left join languages as la
                on ci.language_code = la.language_code
        """)
        st.session_state.last_actions.append(
            f'{df["Qnty"].sum()} cards added to deck {deck_name}'
        )

def show_tab_bar(
        labels: list[str], key: str, default: str | None = None, max_size: int = 6,
        tabs_size: list[float | int] | None = None
    ) -> str:
    """
    Group of buttons with the given labels. Return the selected label.
    """
    if key not in st.session_state or st.session_state[key] is None:
        st.session_state[key] = default or labels[0]

    if tabs_size:
        cols = st.columns(tabs_size)
    else:
        cols = st.columns([1] * len(labels) + [max_size - len(labels)])

    def _set_label(label: str) -> None:
        st.session_state.update(**{key: label})
    selected_label = st.session_state[key]

    for col, label in zip(cols, labels):
        btn_type = "primary" if selected_label == label else "secondary"
        col.button(label, on_click=_set_label, args=(label,), use_container_width=True, type=btn_type)
    return selected_label

def save_to_temp_dir(*args):
    if os.path.exists(temp_folder := './data/temp'):
        for root, _, files in os.walk(temp_folder):
            for file in files:
                os.remove(os.path.join(root, file))
    else:
        os.makedirs(temp_folder)
    
    db_paths = []
    for db in args:
        path = os.path.join(temp_folder, db.name)
        db_paths.append(path)
        with open(path, 'wb') as file:
            file.write(db.read())
    return db_paths

def temp_import_delver_lens_cards(dlens_db_path, ut_db_path):
    sqlite3.register_adapter(uuid.UUID, lambda u: u.bytes_le)
    sqlite3.register_converter('guid', lambda b: uuid.UUID(bytes_le=b))
    csr = Db(':memory:', detect_types=sqlite3.PARSE_DECLTYPES)
    csr.executescript(
    f"""
        attach database '{dlens_db_path}' as exp_db;
        attach database '{ut_db_path}' as apk_db;
        attach database './data/app_data.db' as app_db;
        attach database './data/temp/temp_db.db' as temp_db;
    """)
    df_import = csr.read_sql(
    """
        select
            case
                when apk.scryfall_id is NULL and cards.card = 62663
                    then '320fdf89-e158-41c5-b0bf-fee9dec36a75'
                else apk.scryfall_id
            end as scryfall_id,
            case
                when cards.language <> ''
                    then cards.language
                else 'English'
            end as language,
            case
                when cards.condition <> ''
                    then cards.condition
                else 'Near Mint'
            end as condition_name,
            cards.foil,
            cards.general as is_commander,
            case
                when cards.tab = 0
                    then 'Main'
                when cards.tab = 1
                    then 'Side'
                when cards.tab = 2
                    then 'Maybe'
            end as deck_type_name,
            cards.quantity as qnty,
            lists._id as import_list_id,
            lists.name as name,
            case
                when lists.category = 1
                    then 'Collection'
                when lists.category = 2
                    then 'Deck'
                when lists.category = 3
                    then 'Wish list'
            end as type,
            cast(substr(lists.creation, 1, 10) as integer) as creation_date
        from exp_db.cards as cards
        left join exp_db.lists as lists
            on cards.list = lists._id
        left join apk_db.cards as apk
            on cards.card = apk._id
    """) \
        .assign(scryfall_id=lambda df: df['scryfall_id'].apply(lambda x:uuid.UUID(x)))
    csr.execute(
    f"""
        create table import_cards_temp (
            scryfall_id guid,
            language text,
            condition_name text,
            foil integer,
            is_commander integer,
            deck_type_name text,
            qnty integer,
            import_list_id integer,
            name text,
            type integer,
            creation_date integer
        )
    """)
    columns_temp = csr.read_sql('select * from import_cards_temp').columns
    csr.executemany(
        f"""
        insert into import_cards_temp ({', '.join(columns_temp)})
        values ({', '.join('? ' for _ in range(len(columns_temp)))})
        """,
        df_import[columns_temp].values
    )
    csr.executescript(
    f"""
        drop table if exists temp_db.import_cards;
        create table temp_db.import_cards (
            card_uuid guid,
            language text,
            condition_code text,
            foil integer,
            is_commander integer,
            deck_type_name text,
            qnty integer,
            import_list_id integer
        );
    """)
    columns = csr.read_sql('select * from import_cards').columns
    csr.executescript(
    f"""
        insert into temp_db.import_cards ({', '.join(columns)})
        select 
            ca.card_uuid,
            t.language,
            cc.code as condition_code,
            t.foil,
            t.is_commander,
            t.deck_type_name,
            sum(t.qnty) as qnty,
            t.import_list_id
        from import_cards_temp as t
        left join app_db.cards as ca
            on t.scryfall_id = ca.scryfall_id
        left join app_db.tokens as tk
            on t.scryfall_id = tk.scryfall_id
        left join app_db.card_condition as cc
            on t.condition_name = cc.name
        where
           tk.scryfall_id is Null
           and coalesce(ca.side, 'a') = 'a'
        group by
            ca.card_uuid, t.language, condition_code, t.foil, t.is_commander,
            t.deck_type_name, t.import_list_id
        ;
        drop table if exists temp_db.import_tokens;
        create table temp_db.import_tokens (
            type text,
            list_name text,
            token_name text,
            qnty integer
        );
        insert into temp_db.import_tokens (type, list_name, token_name, qnty)
        select
            t.type,
            t.name,
            tk.name,
            sum(t.qnty) as qnty
        from import_cards_temp as t
        inner join app_db.tokens as tk
            on t.scryfall_id = tk.scryfall_id
        group by
            t.type, t.name, tk.name
        ;
        drop table if exists temp_db.import_lists;
        create table temp_db.import_lists (
            import_list_id integer,
            name text,
            type text,
            selected integer default 1,
            creation_date integer
        );
        create unique index temp_db.idx_list_content
        on import_lists (name, type);
        insert into temp_db.import_lists ({', '.join(columns_temp[-4:])})
        select distinct {', '.join(columns_temp[-4:])}
        from import_cards_temp;
    """)

def check_for_tokens():
    csr = Db('temp/temp_db.db')
    result = csr.execute(
    """
    select
        type,
        list_name,
        token_name,
        qnty
    from import_tokens
    order by list_name
    """
    ).fetchall()
    if len(result) > 0:
        for row in result:
            st.session_state.last_actions.append(
            f'Skipped {row[3]} token {row[2]} in {row[1]} {(row[0]).lower()}'
        )

def get_import_names():
    csr = Db('temp/temp_db.db')
    result = csr.read_sql(
    """
    select
        selected,
        import_list_id,
        name,
        type,
        creation_date
    from import_lists
    order by import_list_id
    """
    )
    result['create_ns'] = time.time_ns()
    return result

def check_for_duplicates():
    csr = Db('temp/temp_db.db')
    msg = ''
    result = csr.execute(
    """
    select
        count(*) as cnt_dups,
        type,
        name
    from import_lists
    group by
        type,
        name
    having cnt_dups > 1
    """
    ).fetchall()
    for row in result:
        msg += f'Found {row[0]} {row[1]}s with same name: {row[2]}  \n'
    if len(msg) > 0:
        msg += 'Rename theys before proceed. Import aborted!'
        return msg
    
    csr.execute("attach database './data/user_data.db' as ud")
    result = csr.execute(
    """
    select name
    from import_lists
    where
        type = 'Collection'
        and selected = 1
    intersect
    select name
    from ud.lists
    """
    ).fetchall()
    for row in result:
        msg += f'Collection {row[0]} already exists!  \n'
    
    result = csr.execute(
    """
    select name
    from import_lists
    where
        type = 'Deck'
        and selected = 1
    intersect
    select name
    from ud.decks
    """
    ).fetchall()
    for row in result:
        msg += f'Deck {row[0]} already exists!  \n'
    msg += 'Import aborted!' if len(msg) > 0 else ''
    return msg

def import_delver_lens_cards(list_for_duplicate: str=None):
    csr = Db('temp/temp_db.db')
    csr.execute("attach database './data/user_data.db' as ud")
    csr.execute("attach database './data/app_data.db' as ad")
    get_list_id_by_name = lambda name: csr.execute(
            f"select list_id from ud.lists where name = '{name}'"
        ) \
        .fetchone()[0]
    insert_exported_list_content = lambda list_id, import_list_id: csr.execute(
    f"""
        insert into list_content (
            list_id,
            card_uuid,
            condition_code,
            foil,
            language,
            qnty
        )
        select
            {list_id},
            ic.card_uuid,
            ic.condition_code,
            ic.foil,
            ic.language,
            ic.qnty
        from import_cards as ic
        where
            ic.import_list_id = {import_list_id}
        on conflict (
            list_id, card_uuid, condition_code,
            foil, language
        ) do update set
            qnty = qnty + excluded.qnty
    """)
    result = csr.execute(
    """
        select name, creation_date, import_list_id, type
        from import_lists
        where
            type in ('Collection', 'Wish list')
            and selected = 1
    """
    ).fetchall()
    for name, creation_date, import_list_id, type in result:
        add_new_record('list', name, creation_date=creation_date)
        list_id = get_list_id_by_name(name)
        if type == 'Wish list':
            update_table('list', list_id, 'is_wish_list', 1)
        insert_exported_list_content(list_id, import_list_id)
        count = csr.execute(
            f"""
                select sum(qnty)
                from ud.list_content
                where list_id = {list_id}
            """).fetchall()[0][0]
        st.session_state.last_actions[-1] = \
            st.session_state.last_actions[-1][:-1] \
            + f' with {count} cards'
    
    result = csr.execute(
    """
        select name, creation_date, import_list_id, type
        from import_lists
        where
            type in ('Deck', 'Wish deck')
            and selected = 1
    """
    ).fetchall()
    for name, creation_date, import_list_id, type in result:
        add_new_record('deck', name, creation_date=creation_date)
        deck_id = csr.execute(
                f"select deck_id from ud.decks where name = '{name}'"
            ) \
            .fetchone()[0]
        if type == 'Wish deck':
            update_table('deck', deck_id, 'is_wish_deck', 1)
        csr.execute(
        f"""
            insert into deck_content (
                deck_id,
                card_uuid,
                is_commander,
                condition_code,
                foil,
                language,
                deck_type_name,
                qnty
            )
            select
                {deck_id},
                ic.card_uuid,
                ic.is_commander,
                ic.condition_code,
                ic.foil,
                ic.language,
                ic.deck_type_name,
                ic.qnty
            from import_cards as ic
            where
                ic.import_list_id = {import_list_id}
            on conflict (
                deck_id, card_uuid, condition_code,
                foil, language, deck_type_name
            ) do update set
                qnty = qnty + excluded.qnty
        """)
        if list_for_duplicate is not None:
            list_id = get_list_id_by_name(list_for_duplicate)
            insert_exported_list_content(list_id, import_list_id)

        count = csr.execute(
            f"""
                select sum(qnty)
                from ud.deck_content
                where deck_id = {deck_id}
            """).fetchall()[0][0]
        st.session_state.last_actions[-1] = \
            st.session_state.last_actions[-1][:-1] \
            + f' with {count} cards'