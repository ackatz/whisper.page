import sqlite3


def get_db_connection():
    conn = sqlite3.connect("/app/whisper_app.db")
    conn.execute("pragma journal_mode=wal")
    conn.row_factory = sqlite3.Row
    return conn
