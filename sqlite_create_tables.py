import sqlite3

# name of db file
# assuming that db file is in the same catalogue as the main script
sqlite_file = 'sejm_gov_pl_db.db'


portraits_table = """
                CREATE TABLE portraits
                (
                term INTEGER,
                id_ TEXT PRIMARY KEY,
                full_name TEXT,
                elected TEXT,
                graduated_school TEXT,
                education_level TEXT,
                occupation TEXT,
                function TEXT,
                academic_title TEXT,
                date_and_place_of_birth TEXT,
                party_section TEXT,
                website TEXT,
				function_in_the_party TEXT,
				election_list TEXT,
				previous_cadency TEXT,
                constituency TEXT,
                email TEXT,
                number_of_votes TEXT,
                end_of_cadency TEXT,
                ethics_violation TEXT,
                married_status TEXT,
                languages TEXT,
                parliamentary_committees TEXT,
                parliamentary_undercommittees TEXT,
                get_term TEXT,
                last_party TEXT,
                db_date TEXT
                )
            """

speech_table = """
                CREATE TABLE speech_data
                (
                term INTERGER,
                id_ TEXT,
                session_number TEXT,
                day_ TEXT,
                date_ TEXT,
                number_ TEXT,
                speech_title TEXT,
                speech_number TEXT,
                speech_link TEXT,
                speech_raw TEXT,
                db_date TEXT
                )
            """


# Connecting to the database file
connection = sqlite3.connect(sqlite_file)
cursor = connection.cursor()

# Creating tables
cursor.execute(portraits_table)
cursor.execute(speech_table)

# commiting changes ans closing connection
connection.commit()
connection.close()
