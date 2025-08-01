import sqlite3
import uuid
import streamlit as st
from utils import Db

def check_table(
    table_name, db_file, reset_table_func
):
    tbl_names_col, rows_cnt_col, btn_col, _, = st.columns((0.2, 0.15, 0.15, 0.5))
    tbl_names_col.text(db_file[:-2] + table_name)
    rows_cnt_col.text(f"rows: {get_rows_count(db_file, table_name)}")
    reset_table_btn = btn_col.button('Reset table', key=f'reset_{table_name}_btn')
    if reset_table_btn:
        reset_table_func()
        st.rerun()

def get_rows_count(db_name: str, table_name: str):
    csr = Db(db_name)
    try:
        result = csr.execute(
        f"""
            select count(*)
            from {table_name}
        """).fetchone()[0]
    except sqlite3.OperationalError:
        result = '-'
    return result

def reset_table_players():
    csr = Db('user_data.db')
    csr.executescript(
    """
        drop table if exists players;
        create table players (
            player_id integer primary key,
            name text not null unique,
            is_default_player integer default 0
        );
        insert into players (name, is_default_player)
        values
            ('Player', 1),
            ('Opponent', 0);
    """)

def reset_table_card_condition():
    csr = Db('app_data.db')
    csr.executescript(
    """
        drop table if exists card_condition;
        create table card_condition (
            condition_id integer primary key,
            code text not null,
            name text not null unique
        );
        insert into card_condition (condition_id, code, name)
        values 
            (1, 'NM', 'Near Mint'), 
            (2, 'SP', 'Slightly Played'),
            (3, 'MP', 'Moderately Played'),
            (4, 'HP', 'Heavily Played'),
            (5, 'D', 'Damaged');
    """)

def reset_table_deck_types():
    csr = Db('app_data.db')
    csr.executescript(
    """
        drop table if exists deck_types;
        create table deck_types (
            deck_type_id integer primary key,
            name text not null unique
        );
        insert into deck_types (deck_type_id, name)
        values (0, 'main'), (1, 'side'), (2, 'maybe');
    """)

def reset_table_lists():
    csr = Db('user_data.db')
    csr.executescript(
    """
        drop table if exists lists;
        create table lists (
            list_id integer primary key,
            name text not null unique,
            player_id integer,
            creation_date integer not null,
            note text default '',
            is_default_list integer default 0,
            is_wish integer default 0,
            foreign key (player_id) references players(player_id) on delete set null on update cascade
        );
        insert into lists (name, creation_date, is_default_list)
        values ('My list', strftime('%s','now'), 1)
        ;
    """)

def reset_table_list_content():
    #NOTE https://stackoverflow.com/questions/50376345/python-insert-uuid-value-in-sqlite3
    sqlite3.register_adapter(uuid.UUID, lambda u: u.bytes_le)
    sqlite3.register_converter('guid', lambda b: uuid.UUID(bytes_le=b))
    csr = Db('user_data.db', detect_types=sqlite3.PARSE_DECLTYPES)
    csr.executescript(
    """
        drop table if exists list_content;
        create table list_content (
            list_id integer,
            card_uuid guid,
            condition_code text,
            foil integer,
            language text,
            qnty integer,
            foreign key (list_id)
                references lists (list_id) on update cascade on delete cascade
        );
        create unique index idx_list_content
        on list_content (
            list_id, card_uuid, condition_code, foil, language
        );
    """)

def reset_table_decks():
    csr = Db('user_data.db')
    csr.executescript(
    """
        drop table if exists decks;
        create table decks (
            deck_id integer primary key,
            name text not null unique,
            player_id integer,
            creation_date integer not null,
            note text default '',
            is_wish integer default 0,
            foreign key (player_id) references players(player_id)
                on update cascade on delete set null
        );
        insert into decks (name, creation_date)
        values ('Default deck', strftime('%s','now'))
        ;
    """)

def reset_table_deck_content():
    #NOTE https://stackoverflow.com/questions/50376345/python-insert-uuid-value-in-sqlite3
    sqlite3.register_adapter(uuid.UUID, lambda u: u.bytes_le)
    sqlite3.register_converter('guid', lambda b: uuid.UUID(bytes_le=b))
    csr = Db('user_data.db', detect_types=sqlite3.PARSE_DECLTYPES)
    csr.executescript(
    """
        drop table if exists deck_content;
        create table deck_content (
            deck_id integer,
            card_uuid guid,
            is_commander integer,
            condition_code text,
            foil integer,
            language text,
            deck_type_name text,
            qnty integer,
            foreign key (deck_id)
              references decks(deck_id) on update cascade on delete cascade
        );
        create unique index idx_deck_content
        on deck_content (
            deck_id, card_uuid, condition_code, foil, language, deck_type_name
        );
    """)

def reset_table_card_names():
    csr = Db('app_data.db')
    csr.execute("attach database './import/AllPrintings.sqlite' as ap")
    csr.executescript(
    """
        drop table if exists card_names;
        create table card_names (
            name text not null collate nocase,
            language text
        );
        insert into card_names (
            name, language
        )
        select distinct
            name,
            case
                when language = 'Portuguese (Brazil)'
                    then 'Portuguese'
                else language
            end as language
        from (
            select name, language
            from ap.cards
            union all
            select name, language
            from ap.cardForeignData
        ) as unioned_cards
    """)

def reset_table_sets():
    csr = Db('app_data.db')
    csr.execute("attach database './import/AllPrintings.sqlite' as ap")
    csr.executescript(
    """
        drop table if exists main.sets;
        create table sets (
            set_code text primary key,
            name text,
            keyrune_code text,
            release_date integer
        );
        insert into sets (
            set_code, name, keyrune_code, release_date
        )
        select code, name, keyrunecode, strftime('%s', releasedate)
        from ap.sets
    """)

def reset_table_languages():
    csr = Db('app_data.db')
    csr.executescript(
    """
        drop table if exists languages;
        create table languages (
            language text not null primary key,
            language_code text not null
        );
        insert into languages (language, language_code)
        values
            ('English', 'en'),
            ('Spanish', 'es'),
            ('French', 'fr'),
            ('German', 'de'),
            ('Italian', 'it'),
            ('Portuguese', 'pt'),
            ('Japanese', 'ja'),
            ('Korean', 'ko'),
            ('Russian', 'ru'),
            ('Chinese Simplified', 'zhs'),
            ('Chinese Traditional', 'zht'),
            ('Hebrew', 'he'),
            ('Latin', 'la'),
            ('Ancient Greek', 'grc'),
            ('Arabic', 'ar'),
            ('Sanskrit', 'sa'),
            ('Phyrexian', 'ph');
    """)

def _color_extractor(mana_cost: str):
    if mana_cost is not None:
        colors = []
        mana_cost = mana_cost[1:] \
            .replace('}', '') \
            .replace('/', '{') \
            .split('{')
        for symbol in set(mana_cost):
            if symbol in ['B', 'G', 'R', 'U', 'W', 'C']:
                colors.append(symbol)
        if (len(colors) == 0) & ((symbol == 'X') | (symbol.isdigit())):
            colors.append('X')
        colors = ''.join(sorted(colors))
    else:
        colors = ''
    return colors

def reset_table_card_unique_metadata():
    #NOTE https://stackoverflow.com/questions/50376345/python-insert-uuid-value-in-sqlite3
    sqlite3.register_adapter(uuid.UUID, lambda u: u.bytes_le)
    sqlite3.register_converter('guid', lambda b: uuid.UUID(bytes_le=b))
    csr = Db(':memory:', detect_types=sqlite3.PARSE_DECLTYPES)
    csr.executescript(
    """
        attach database './import/AllPrintings.sqlite' as ap;
        attach database './data/app_data.db' as ad;
    """)
    df_import = csr.read_sql(
    """
        select distinct
            c1.name,
            i1.scryfallOracleId as card_common_id,
            c1.manacost as mana_cost,
            c1.manavalue as mana_value,
            c1.type,
            c1.rarity,
            c1.power,
            c1.toughness,
            c1.text,
            1 as search_priority
        from
            ap.cards as c1
        inner join ap.cardidentifiers as i1 on c1.uuid = i1.uuid
        union all
        select distinct
            f.name,
            i2.scryfallOracleId as card_common_id,
            c2.manacost as mana_cost,
            c2.manavalue as mana_value,
            f.type,
            c2.rarity,
            c2.power,
            c2.toughness,
            f.text,
            2 as search_priority
        from
            ap.cardForeignData as f
        inner join ap.cards as c2 on f.uuid = c2.uuid
        inner join ap.cardidentifiers as i2 on f.uuid = i2.uuid
    """) \
        .assign(colors=lambda df: df['mana_cost'].apply(lambda x:_color_extractor(x))) \
        .assign(card_common_id=lambda df: df['card_common_id'].apply(lambda x:uuid.UUID(x))) \
        .assign(power=lambda df: df['power'].str.replace('*', '★')) \
        .assign(toughness=lambda df: df['toughness'].str.replace('*', '★')) \
        .fillna('')

    create_table_ddl = lambda table_name: (
    f"""
        create table {table_name} (
            name text,
            card_common_id guid,
            mana_cost text,
            mana_value real,
            type text,
            rarity text,
            colors text,
            power text,
            toughness text,
            text text,
            search_priority integer
        )
    """)
    table_name = 'card_unique_metadata'
    temp_table_name = table_name + '_temp'
    csr.execute(create_table_ddl(temp_table_name))
    columns = csr.read_sql(f'select * from {temp_table_name}').columns
    csr.executemany(
        f"""
            insert into {temp_table_name} ({', '.join(columns)})
            values ({', '.join('? ' for _ in range(len(columns)))})
        """,
        df_import[columns].values
    )
    csr.executescript(
    f"""
        drop table if exists ad.{table_name};
        {create_table_ddl(f'ad.{table_name}')};
        insert into ad.{table_name} ({', '.join(columns)})
        select {', '.join(columns)}
        from {temp_table_name}
    """)

def reset_table_cards():
    #NOTE https://stackoverflow.com/questions/50376345/python-insert-uuid-value-in-sqlite3
    sqlite3.register_adapter(uuid.UUID, lambda u: u.bytes_le)
    sqlite3.register_converter('guid', lambda b: uuid.UUID(bytes_le=b))
    csr = Db(':memory:', detect_types=sqlite3.PARSE_DECLTYPES)
    csr.executescript(
    """
        attach database './import/AllPrintings.sqlite' as ap;
        attach database './data/app_data.db' as ad;
    """)
    df_import = csr.read_sql(
    """
        select
            c.uuid as card_uuid,
            c.name,
            c.number,
            c.setcode as set_code,
            i.scryfallOracleId as card_common_id,
            i.scryfallid as scryfall_id,
            c.side,
            c.language,
            c.manacost as mana_cost,
            c.type,
            c.rarity
        from
            ap.cards as c
            join ap.cardidentifiers as i on c.uuid = i.uuid
    """) \
        .assign(card_uuid=lambda df: df['card_uuid'].apply(lambda x:uuid.UUID(x))) \
        .assign(card_common_id=lambda df: df['card_common_id'].apply(lambda x:uuid.UUID(x))) \
        .assign(scryfall_id=lambda df: df['scryfall_id'].apply(lambda x:uuid.UUID(x)))

    create_table_ddl = lambda table: (
    f"""
        create table {table} (
            card_uuid guid primary key,
            name text,
            number text,
            set_code text,
            card_common_id guid,
            scryfall_id guid,
            side text,
            language text,
            mana_cost text,
            type text,
            rarity text
        )
    """)
    csr.execute(create_table_ddl('cards_temp'))
    columns = csr.read_sql('select * from cards_temp').columns
    csr.executemany(
    f"""
        insert into cards_temp ({', '.join(columns)})
        values ({', '.join('? ' for _ in range(len(columns)))})
    """,
        df_import[columns].values
        )
    csr.executescript(
    f"""
        drop table if exists ad.cards;
        {create_table_ddl('ad.cards')};
        insert into ad.cards ({', '.join(columns)})
        select {', '.join(columns)}
        from cards_temp
    """)

def reset_table_tokens():
    #NOTE https://stackoverflow.com/questions/50376345/python-insert-uuid-value-in-sqlite3
    sqlite3.register_adapter(uuid.UUID, lambda u: u.bytes_le)
    sqlite3.register_converter('guid', lambda b: uuid.UUID(bytes_le=b))
    csr = Db(':memory:', detect_types=sqlite3.PARSE_DECLTYPES)
    csr.executescript(
    """
        attach database './import/AllPrintings.sqlite' as ap;
        attach database './data/app_data.db' as ad;
    """)
    df_import = csr.read_sql(
    """
        select
            t.uuid as token_uuid,
            i.scryfallid as scryfall_id,
            t.name
        from
            ap.tokens as t
            join ap.tokenidentifiers as i on t.uuid = i.uuid
    """) \
        .assign(token_uuid=lambda df: df['token_uuid'].apply(lambda x:uuid.UUID(x))) \
        .assign(scryfall_id=lambda df: df['scryfall_id'].apply(lambda x:uuid.UUID(x)))

    create_table_ddl = lambda table: (
    f"""
        create table {table} (
            token_uuid guid primary key,
            scryfall_id guid,
            name text
        )
    """)
    csr.execute(create_table_ddl('tokens_temp'))
    columns = csr.read_sql('select * from tokens_temp limit 1').columns
    csr.executemany(
    f"""
        insert into tokens_temp ({', '.join(columns)})
        values ({', '.join('? ' for _ in range(len(columns)))})
    """,
        df_import[columns].values
        )
    csr.executescript(
    f"""
        drop table if exists ad.tokens;
        {create_table_ddl('ad.tokens')};
        insert into ad.tokens ({', '.join(columns)})
        select {', '.join(columns)}
        from tokens_temp
    """)

def reset_table_foreign_data():
    #NOTE https://stackoverflow.com/questions/50376345/python-insert-uuid-value-in-sqlite3
    sqlite3.register_adapter(uuid.UUID, lambda u: u.bytes_le)
    sqlite3.register_converter('guid', lambda b: uuid.UUID(bytes_le=b))
    csr = Db(':memory:', detect_types=sqlite3.PARSE_DECLTYPES)
    csr.executescript(
    """
        attach database './import/AllPrintings.sqlite' as ap;
        attach database './data/app_data.db' as ad;
    """)
    df = csr.read_sql(
    """
        select
            uuid as card_uuid,
            name,
            case
                when language = 'Portuguese (Brazil)'
                    then 'Portuguese'
                else language
            end as language,
            type
        from ap.cardforeigndata
    """) \
        .assign(card_uuid=lambda df: df['card_uuid'].apply(lambda x:uuid.UUID(x)))

    create_table_ddl = lambda table: (
    f"""
        create table {table} (
            card_uuid guid,
            name text,
            language text,
            type text
        )
    """)
    csr.execute(create_table_ddl('foreign_data_temp'))
    columns = csr.read_sql('select * from foreign_data_temp limit 1').columns
    csr.executemany(
    f"""
        insert into foreign_data_temp ({', '.join(columns)})
        values ({', '.join('? ' for _ in range(len(columns)))})
    """,
        df[columns].values
    )
    csr.executescript(
    f"""
        drop table if exists ad.foreign_data;
        {create_table_ddl('ad.foreign_data')};
        insert into ad.foreign_data ({', '.join(columns)})
        select {', '.join(columns)}
        from foreign_data_temp
    """)