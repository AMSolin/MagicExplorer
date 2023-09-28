import sqlite3
import uuid
import pandas as pd
import requests
import json
import streamlit as st
import time
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

    def read_sql(self, query):
        return pd.read_sql(query, self.conn)
    
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
def search_cards(
    name='', cmc=(0, 15), type='', color=''
):
    cmc_cond = f'c.CMC between {cmc[0]} and {cmc[1]}' if cmc != (0, 15) else '1=1'
    name_cond = f' and c.name like "%{name}%"' if name != '' else ''
    type_cond = f' and c.Type like "%{type}%"' if type != '' else ''
    color_cond = f' and c.Color like "{color}"' if color != '' else ''
    colorless_cond = 'and c.Color is null' if color is None else ''
    query = f"""
    select 
        Name,
        Type,
        cast(CMC as int) as CMC,
        Color,
        Rarity,
        "image url" as "image_url"
    from collection as c
    where
    {cmc_cond + name_cond + type_cond + color_cond + colorless_cond}
    order by
        name
    """
    with sqlite3.connect('./data/mtg.db') as conn:
        result = pd.read_sql(query, conn)
    # symbol_conv = {'{R}': ':fire:', '{U}': ':droplet:'}
    # result['Cost'] = result['Cost'].replace(symbol_conv)
    result['image_url'] = result['image_url'].fillna('https://upload.wikimedia.org/wikipedia/en/thumb/a/aa/Magic_the_gathering-card_back.jpg/220px-Magic_the_gathering-card_back.jpg')
    return result

def to_lower_and_substring_search(substr_card: str):
    return to_lower_and_exact_search(f'%{substr_card}%')

def to_lower_and_exact_search(substr_card: str):
    return search_card_by_name(substr_card.lower())


@st.cache_data
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

@st.cache_data
def search_set_by_name(card_name: str, card_lang: str):
    csr = Db('app_data.db')
    card_name = card_name.replace("'", "''")
    if card_lang in ['English', 'Phyrexian']:
        query = f"""
            select
                c.name,
                c.set_code as set_code,
                lower(s.keyrune_code) as keyrune_code,
                c.number,
                language_code
            from cards as c
            left join sets as s
                on s.set_code = c.set_code
            left join languages as l
                on c.language = l.language
            where
                c.name = '{card_name}'
                and c.language = '{card_lang}'
            order by s.release_date desc, c.number
        """
    else:
        query = f"""
            select
                c.name,
                c.set_code as set_code,
                lower(s.keyrune_code) as keyrune_code,
                c.number,
                l.language_code
            from cards as c
            inner join (
                select
                    card_uuid,
                    language
                from foreign_data
                where 
                    foreign_name = '{card_name}'
                    and language = '{card_lang}'
            ) as f
                on c.card_uuid = f.card_uuid
            left join sets as s
                on s.set_code = c.set_code
            left join languages as l
                on f.language = l.language
            order by s.release_date desc, c.number
        """
    result = csr.read_sql(query)
    return result

@st.cache_data
def generate_set_dict(set_col: pd.Series):
    sets_dict = {}
    for ix, code in set_col.drop_duplicates().items():
        if ix == 0:
            sets_dict['default_code'] = code
        sets_dict[code] = f'<a id="{code}" class="ss ss-{code} ss-2x"></a> '
    return sets_dict

def generate_css_set_icons(sets_dict):
    css = '<link href="//cdn.jsdelivr.net/npm/keyrune@latest/css/keyrune.css" rel="stylesheet" type="text/css" />'
    if ('selected_set' not in st.session_state) or (st.session_state.selected_set not in sets_dict.keys()):
        st.session_state.selected_set = sets_dict.pop('default_code')
    else:
        del sets_dict['default_code']
    for set, set_css in sets_dict.items():
        if set == st.session_state.selected_set:
            set_css = f'<span style="color: orange">{set_css}</span>'
        css+= set_css
    return css

@st.cache_data
def get_image_uris(set_code, card_number, lang):
    api_url = 'https://api.scryfall.com/cards'
    r = requests.get(f'{api_url}/{set_code.lower()}/{card_number}/{lang}').text
    uri = json.loads(r)['image_uris']['normal']
    time.sleep(0.1)
    return uri

def get_card_images(df, selected_set):
    content = ''
    df_filtered = df[df['keyrune_code'] == selected_set] \
        .drop(columns=['name', 'keyrune_code'])
    for row in df_filtered.itertuples(index=False):
        set_code, card_number, lang = row
        uri = get_image_uris(set_code, card_number, lang)
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
            p.name as owner
        from lists as l
        left join players as p
            on l.player_id = p.player_id
        order by is_default_list desc, l.creation_date
    """)
    result['create_ns'] = time.time_ns()
    return result

def get_list_content(list_id):
    csr = Db('user_data.db')
    csr.execute("attach database './data/app_data.db' as ad")
    result = csr.read_sql(
    f"""
        select
            lc.card_uuid,
            lc.condition_id,
            lc.language,
            lc.qnty,
            ca.name, --#TODO change name according language
            ca.number as card_number,
            ca.type,
            la.language_code,
            se.set_code,
            --se.keyrune_code, #TODO add keyrune symbol
            ca.rarity,
            ca.mana_cost,
            lc.foil,
            co.code as condition_code
        from list_content as lc
        left join cards as ca
            on lc.card_uuid = ca.card_uuid
        left join card_condition as co
            on lc.condition_id = co.condition_id
        left join sets as se
            on ca.set_code = se.set_code
        left join languages as la
            on lc.language = la.language
        where list_id = {list_id}
        order by ca.name
    """)
    result['create_ns'] = time.time_ns()
    return result

def get_decks():
    csr = Db('user_data.db')
    result = csr.read_sql('select * from decks order by deck_id')
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

def add_new_record(entity: str, name: str, is_default: bool=False):
    csr = Db('user_data.db')
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
                '{name}', strftime('%s','now'), {int(is_default)}
            )
        """)
    elif entity == 'deck':
        csr.execute(
        f"""
            insert into decks (name, creation_date)
            values ('{name}', strftime('%s','now'))
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

def update_table(entity, default_value, id, column, value):
    csr = Db('user_data.db')
    if column == f'is_default_{entity}':
        set_default_value(entity, default_value, csr)
    else:
        csr.execute(
        f"""
            update {entity}s
            set {column} = '{value}'
            where {entity}_id = {id}
        """)

def update_table_content(entity, card_dict, column, value):
    csr = Db('user_data.db')
    if not ((column == 'qnty') and (value > 0)):
        csr.execute(
        f"""
            delete from {entity}_content
            where
                list_id = {card_dict['list_id']}
                and card_uuid = X'{card_dict['card_uuid'].hex()}'
                and condition_id = {card_dict['condition_id']}
                and foil = {card_dict['foil']}
                and language = '{card_dict['language']}'
        """)
    if not ((column == 'qnty') and (value == 0)):
        card_dict[column] = value
        if column != 'qnty':
            add_method = 'qnty + excluded.qnty'
        else:
            add_method = 'excluded.qnty'
        csr.execute(
        f"""
            insert into {entity}_content (
                list_id, card_uuid, condition_id, foil, language, qnty
            ) 
            values(?, ?, ?, ?, ?, ?)
            on conflict (
                list_id, card_uuid, condition_id, foil, language
            ) do update set qnty = {add_method}
        """, 
        (card_dict['list_id'], (card_dict['card_uuid']), card_dict['condition_id'],
            card_dict['foil'], card_dict['language'], card_dict['qnty'])
        )

def columns_conversation(df):
    csr = Db('user_data.db')
    for col in df.columns:
        if col == 'Foil':
            df[col] = df[col].astype(int)
        elif col == 'Condition':
            df_conv = csr.read_sql(
                'select condition_id, code from card_condition'
            )
        elif col == 'Deck type':
            df_conv = csr.read_sql(
                'select deck_type_id, name from deck_types'
            )
        dict_conv = {row[1]: row[0] for row in df_conv.values}
        df[col] = df[col].replace(dict_conv).astype(int)
    return df

def import_cards(
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
        csr.execute(
        f"""
            insert into lists (name, creation_date)
            values ('{list_name}', strftime('%s','now'))
        """)
        st.session_state.last_actions.append(
            f'List {list_name} was added!'
        )
    if deck_action == 'New':
        csr.execute(
        f"""
            insert into decks (name, creation_date)
            values ('{deck_name}', strftime('%s','now'))
        """)
        st.session_state.last_actions.append(
            f'Deck {deck_name} was added!'
        )
    if list_action != 'Skip':
        csr.execute(
        f"""
            insert into list_content (
                list_id,
                card_uuid,
                condition_id,
                foil,
                language,
                qnty
            )
            select
                li.list_id,
                ca.card_uuid,
                co.condition_id,
                ci.foil,
                la.language,
                ci.qnty
            from card_import as ci
            left join lists as li
                on ci.list_name = li.name
            left join ad.cards as ca
                on ci.set_code = ca.set_code
                and ci.number = ca.number
            left join card_condition as co
                on ci.condition_code = co.code
            left join languages as la
                on ci.language_code = la.language_code
            on conflict (
                list_id, card_uuid, condition_id,
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
            insert into deck_content
            select
                de.deck_id,
                ca.card_uuid,
                co.condition_id,
                dt.deck_type_id,
                ci.qnty,
                ci.foil,
                la.language
            from card_import as ci
            left join decks as de
                on ci.deck_name = de.name
            left join ad.cards as ca
                on ci.set_code = ca.set_code
                and ci.number = ca.number
            left join card_condition as co
                on ci.condition_code = co.code
            left join deck_types as dt
                on ci.deck_type_name = dt.name
            left join languages as la
                on ci.language_code = la.language_code
        """)
        st.session_state.last_actions.append(
            f'{df["Qnty"].sum()} cards added to deck {deck_name}'
        )