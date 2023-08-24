import sqlite3
import uuid
import streamlit as st
from utils import Db

def check_table(
    table_name, db_file, reset_table_func
):
    tbl_names_col, rows_cnt_col, btn_col, _, = st.columns((0.2, 0.1, 0.1, 0.6))
    tbl_names_col.text(db_file[:-2] + table_name)
    rows_cnt_col.text(f"rows: {get_rows_count(db_file, table_name)}")
    reset_table_btn = btn_col.button('Reset table', key=f'reset_{table_name}_btn')
    if reset_table_btn:
        reset_table_func()
        st.experimental_rerun()

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
    csr = Db('user_data.db')
    csr.executescript(
    """
        drop table if exists card_condition;
        create table card_condition (
            condition_id integer primary key,
            code text not null unique
        );
        insert into card_condition (condition_id, code)
        values (1, 'NM'), (2, 'SP'), (3, 'MP'), (4, 'HP'), (5, 'D');
    """)

def reset_table_deck_types():
    csr = Db('user_data.db')
    csr.executescript(
    """
        drop table if exists deck_types;
        create table deck_types (
            deck_type_id integer primary key,
            name text not null unique
        );
        insert into deck_types (deck_type_id, name)
        values (1, 'main'), (2, 'sideboard'), (3, 'maybe');
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
            note text,
            is_default_list integer default 0,
            foreign key (player_id) references players(player_id) on delete set null on update cascade
        );
        insert into lists (name, creation_date, is_default_list)
        values ('Default list', strftime('%s','now'), 1)
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
            condition_id integer,
            qnty integer,
            foil integer,
            language text,
            foreign key (list_id) references lists(list_id) on delete cascade on update cascade--,
            --foreign key (card_uuid) references cards(card_uuid) on delete cascade on update cascade,
            --foreign key (condition_id) references cards(card_uuid) on delete set null on update cascade
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
            note text,
            foreign key (player_id) references players(player_id) on delete set null on update cascade
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
            condition_id integer,
            deck_type_id integer,
            qnty integer,
            foil integer,
            language text,
            foreign key (deck_id) references decks(deck_id) on delete cascade on update cascade--,
            --foreign key (card_uuid) references cards(card_uuid) on delete cascade on update cascade,
            --foreign key (condition_id) references cards(card_uuid) on delete set null on update cascade
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
        select distinct name, language
        from ap.cards
        union all
        select distinct name, language
        from ap.cardForeignData
    """)

def reset_table_sets():
    csr = Db('app_data.db')
    csr.execute("attach database './import/AllPrintings.sqlite' as ap")
    csr.executescript(
    """
        drop table if exists main.sets;
        create table sets (
            set_code text primary key,
            keyrune_code text,
            release_date integer
        );
        insert into sets (
            set_code, keyrune_code, release_date
        )
        select code, keyrunecode, strftime('%s', releasedate)
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
            ('Portuguese (Brazil)', 'pt'),
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

def reset_table_cards():
    #NOTE https://stackoverflow.com/questions/50376345/python-insert-uuid-value-in-sqlite3
    sqlite3.register_adapter(uuid.UUID, lambda u: u.bytes_le)
    sqlite3.register_converter('guid', lambda b: uuid.UUID(bytes_le=b))
    csr = Db(':memory:', detect_types=sqlite3.PARSE_DECLTYPES)
    csr.execute("attach database './import/AllPrintings.sqlite' as ap")
    rows = csr.execute(
    """
        select
            c.uuid,
            c.name,
            c.number,
            c.setcode,
            i.scryfallid,
            c.language,
            c.manacost,
            c.manavalue,
            c.colors,
            c.power,
            c.toughness
        from
            ap.cards as c
            join ap.cardidentifiers as i on c.uuid = i.uuid
    """).fetchall()

    csr.execute(
    """
        create table cards_temp (
            card_uuid guid,
            name text,
            number text,
            set_code text,
            scryfall_id guid,
            language text,
            mana_cost text,
            mana_value text,
            colors text,
            power text,
            toughness text
        )
    """)
    for r in rows:
        csr.execute(
        """
            insert into cards_temp (
                card_uuid,
                name,
                number,
                set_code,
                scryfall_id,
                language,
                mana_cost,
                mana_value,
                colors,
                power,
                toughness
            )
            values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (uuid.UUID(r[0]), r[1], r[2], r[3], uuid.UUID(r[4]), r[5], r[6], r[7], r[8], r[9], r[10])
        )
    csr.execute("attach database './data/app_data.db' as ad")
    csr.executescript(
    """
        drop table if exists ad.cards;
        create table ad.cards (
            card_uuid guid primary key,
            name text,
            number text,
            set_code text ,
            scryfall_id guid,
            language text,
            mana_cost text,
            mana_value text,
            colors text,
            power text,
            toughness text,
            foreign key (set_code) references sets(set_code) on delete set null on update cascade,
            foreign key (language) references languages(language) on delete set null on update cascade
        );
        insert into ad.cards (
            card_uuid,
            name,
            number,
            set_code,
            scryfall_id,
            language,
            mana_cost,
            mana_value,
            colors,
            power,
            toughness
        )
        select
            card_uuid,
            name,
            number,
            set_code,
            scryfall_id,
            language,
            mana_cost,
            mana_value,
            colors,
            power,
            toughness
        FROM
            cards_temp
    """)

def reset_table_foreign_data():
    #NOTE https://stackoverflow.com/questions/50376345/python-insert-uuid-value-in-sqlite3
    sqlite3.register_adapter(uuid.UUID, lambda u: u.bytes_le)
    sqlite3.register_converter('guid', lambda b: uuid.UUID(bytes_le=b))
    csr = Db(':memory:', detect_types=sqlite3.PARSE_DECLTYPES)
    csr.execute("attach database './import/AllPrintings.sqlite' as ap")
    rows = csr.execute(
    """
        select
            uuid,
            name,
            language
        from ap.cardforeigndata
    """).fetchall()

    csr.execute(
    """
        create table foreign_data_temp (
            card_uuid guid,
            foreign_name text,
            language text
        )
    """)
    for r in rows:
        csr.execute(
        """
            insert into foreign_data_temp (
                card_uuid,
                foreign_name,
                language
            )
            values (?, ?, ?)
        """, (uuid.UUID(r[0]), r[1], r[2])
        )
    csr.execute("attach database './data/app_data.db' as ad")
    csr.executescript(
    """
        drop table if exists ad.foreign_data;
        create table ad.foreign_data (
            card_uuid guid,
            foreign_name text,
            language text,
            foreign key (card_uuid) references cards (card_uuid) on delete set null on update cascade
        );
        insert into ad.foreign_data (
                card_uuid,
                foreign_name,
                language
        )
        select
                card_uuid,
                foreign_name,
                language
        FROM
            foreign_data_temp
    """)