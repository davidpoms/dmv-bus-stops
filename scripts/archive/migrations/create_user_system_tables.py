from pathlib import Path
import sqlite3


DB = Path("src/database/dmv_bus_stops.db")


conn = sqlite3.connect(DB)

cur = conn.cursor()


cur.executescript("""

CREATE TABLE IF NOT EXISTS users (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    email TEXT UNIQUE,

    name TEXT,

    password_hash TEXT,

    role TEXT DEFAULT 'volunteer',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

);



CREATE TABLE IF NOT EXISTS stop_reviews (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    stop_id INTEGER NOT NULL,

    user_id INTEGER,

    anonymous_email TEXT,

    has_bench TEXT,

    has_space_for_bench TEXT,

    notes TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY(user_id)
        REFERENCES users(id)

);



CREATE TABLE IF NOT EXISTS stop_stewardships (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    stop_id INTEGER NOT NULL,

    user_id INTEGER NOT NULL,

    status TEXT DEFAULT 'pending',

    approved_by INTEGER,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY(user_id)
        REFERENCES users(id)

);



CREATE TABLE IF NOT EXISTS route_stewardships (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    route_id TEXT NOT NULL,

    user_id INTEGER NOT NULL,

    status TEXT DEFAULT 'pending',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY(user_id)
        REFERENCES users(id)

);


""")

conn.commit()

conn.close()

print("Created user and stewardship tables")
