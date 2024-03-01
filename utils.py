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
import extra_streamlit_components as stx

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
                and coalesce(c.side, 'a') = 'a'
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
                    name = '{card_name}'
                    and language = '{card_lang}'
            ) as f
                on c.card_uuid = f.card_uuid
            left join sets as s
                on s.set_code = c.set_code
            left join languages as l
                on f.language = l.language
            where
                coalesce(c.side, 'a') = 'a'
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
def get_card_properties(set_code, card_number, lang):
    api_url = 'https://api.scryfall.com/cards'
    r = requests.get(f'{api_url}/{set_code.lower()}/{card_number}/{lang}').text
    card_props = json.loads(r)
    return card_props

def get_card_images(df, selected_set):
    content = ''
    df_filtered = df[df['keyrune_code'] == selected_set] \
        .drop(columns=['name', 'keyrune_code'])
    for row in df_filtered.itertuples(index=False):
        set_code, card_number, lang = row
        card_props = get_card_properties(set_code, card_number, lang)
        if card_props.get('card_faces'):
            side = st.radio('_', ['Front', 'Back'], label_visibility='hidden', horizontal=True, key=f'v_import_card_side {set_code} {card_number} {lang}')
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
        where
            list_id = {list_id}
            and coalesce(ca.side, 'a') = 'a'
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

def update_table(entity, id, column, value, default_value=None, db_path='user_data.db'):
    if isinstance(value, str) and 'session_state' in value:
        value = eval(value)
    if isinstance(value, datetime.date):
        value = int(datetime.datetime(
                value.year, value.month, value.day
            ).timestamp()
        )
    csr = Db(db_path)
    if column == f'is_default_{entity}':
        set_default_value(entity, default_value, csr)
    else:
        csr.execute(
        f"""
            update {entity}s
            set {column} = '{value}'
            where {entity}_id = {id}
        """)

def update_table_content(entity, card_id, column, value):
    if isinstance(value, str) and 'session_state' in value:
        value = eval(value)
    card_dict = card_id.to_dict()
    csr = Db('user_data.db')
    if not ((column == 'qnty') and (value > 0)):
        #Если установили qnty = 0 или изменили другое поле
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
        st.session_state.selected_card = None
    if not ((column == 'qnty') and (value == 0)):
        #Если не устанаваливали qnty = 0
        card_dict[column] = value
        if column != 'qnty':
            #В случае конфликта при изменении ключевых полей
            #сложим новое и прежнее значения qnty вместе
            add_method = 'qnty + excluded.qnty'
        else:
            #Иначе в случае конфликта обновим значение qnty
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

def show_tab_bar(tabs: list):
    data = []
    for tab in tabs:
        data.append(stx.TabBarItemData(id=tab, title=tab, description=None))
    tab_bar = stx.tab_bar(data=data, default=tabs[0])
    return tab_bar

def save_to_temp_dir(*args):
    for root, _, files in os.walk('./data/temp'):
        for file in files:
            os.remove(os.path.join(root, file))
    db_paths = []
    for db in args:
        path = os.path.join('./data/temp', db.name)
        db_paths.append(path)
        with open(path, 'wb') as file:
            file.write(db.read())
    return db_paths

def import_delver_lens_cards(dlens_db_path, ut_db_path):
    sqlite3.register_adapter(uuid.UUID, lambda u: u.bytes_le)
    sqlite3.register_converter('guid', lambda b: uuid.UUID(bytes_le=b))
    csr = Db(':memory:', detect_types=sqlite3.PARSE_DECLTYPES)
    csr.executescript(
    f"""
        attach database '{dlens_db_path}' as exp_db;
        attach database '{ut_db_path}' as apk_db;
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
                else NULL
            end as condition_name,
            cards.foil,
            cards.general as is_commander,
            cards.quantity as qnty,
            lists._id as import_list_id,
            lists.name as name,
            case
                when lists.category = 1
                    then 'Collection'
                when lists.category = 2
                    then 'Deck'
                when lists.category = 3
                    then 'Wishlist'
            end as type,
            lists.creation as creation_date
        from exp_db.cards as cards
        left join exp_db.lists as lists
            on cards.list = lists._id
        left join apk_db.cards as apk
            on cards.card = apk._id
    """) \
        .assign(scryfall_id=lambda df: df['scryfall_id'].apply(lambda x:uuid.UUID(x)))
    create_table_ddl = lambda table:(
    f"""
        create table {table} (
            scryfall_id guid,
            language text,
            condition_name text,
            foil integer,
            is_commander integer,
            qnty integer,
            import_list_id integer,
            name text,
            type integer,
            creation_date integer
        )
    """)
    csr.execute(create_table_ddl('import_cards_temp'))
    columns = csr.read_sql('select * from import_cards_temp').columns
    csr.executemany(
        f"""
        insert into import_cards_temp ({', '.join(columns)})
        values ({', '.join('? ' for _ in range(len(columns)))})
        """,
        df_import[columns].values
    )
    csr.executescript(
    f"""
        drop table if exists temp_db.import_lists;
        create table temp_db.import_lists (
            import_list_id integer,
            name text,
            type integer,
            creation_date integer
        );
        create unique index temp_db.idx_list_content
        on import_lists (name, type);
        insert into temp_db.import_lists ({', '.join(columns[-4:])})
        select distinct {', '.join(columns[-4:])}
        from import_cards_temp;
        drop table if exists temp_db.import_cards;
        {create_table_ddl('temp_db.import_cards')};
        insert into temp_db.import_cards ({', '.join(columns[:-3])})
        select {', '.join(columns[:-3])}
        from import_cards_temp;
    """)
def get_import_names():
    csr = Db('temp/temp_db.db', detect_types=sqlite3.PARSE_DECLTYPES)
    result = csr.read_sql(
    """
    select
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

