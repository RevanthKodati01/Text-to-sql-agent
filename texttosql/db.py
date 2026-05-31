from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS customers (
    id      INTEGER PRIMARY KEY,
    name    TEXT NOT NULL,
    city    TEXT NOT NULL,
    joined  DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
    id       INTEGER PRIMARY KEY,
    name     TEXT NOT NULL,
    category TEXT NOT NULL,
    price    REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    id          INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    product_id  INTEGER NOT NULL REFERENCES products(id),
    quantity    INTEGER NOT NULL,
    ordered_at  DATE NOT NULL
);
"""

_CUSTOMERS = [
    (1, "Alice",   "Austin",      "2022-03-15"),
    (2, "Bob",     "Boston",      "2022-07-01"),
    (3, "Carol",   "Austin",      "2023-01-20"),
    (4, "David",   "Chicago",     "2023-06-10"),
    (5, "Eve",     "Boston",      "2024-02-28"),
]

_PRODUCTS = [
    (1, "Laptop",      "electronics", 999.99),
    (2, "Headphones",  "electronics", 149.99),
    (3, "Keyboard",    "electronics",  79.99),
    (4, "Python Book", "books",        39.99),
    (5, "SQL Guide",   "books",        29.99),
    (6, "Sci-Fi Novel","books",        14.99),
    (7, "T-Shirt",     "clothing",     19.99),
    (8, "Jacket",      "clothing",     89.99),
]

_ORDERS = [
    (1,  1, 1, 1, "2023-01-10"),
    (2,  1, 4, 2, "2023-03-22"),
    (3,  2, 2, 1, "2023-04-05"),
    (4,  2, 7, 3, "2023-05-18"),
    (5,  3, 3, 1, "2023-07-30"),
    (6,  3, 5, 1, "2023-08-14"),
    (7,  4, 1, 1, "2023-11-01"),
    (8,  4, 8, 2, "2023-12-20"),
    (9,  1, 2, 1, "2024-01-09"),
    (10, 5, 6, 1, "2024-02-14"),
    (11, 2, 4, 1, "2024-03-03"),
    (12, 3, 1, 1, "2024-04-17"),
    (13, 4, 3, 2, "2024-06-25"),
    (14, 1, 8, 1, "2024-08-08"),
    (15, 5, 7, 2, "2024-09-30"),
]


def seed(db_path: Path | str) -> None:
    con = sqlite3.connect(str(db_path))
    con.executescript(SCHEMA_SQL)
    con.executemany("INSERT OR IGNORE INTO customers VALUES (?,?,?,?)", _CUSTOMERS)
    con.executemany("INSERT OR IGNORE INTO products  VALUES (?,?,?,?)", _PRODUCTS)
    con.executemany("INSERT OR IGNORE INTO orders    VALUES (?,?,?,?,?)", _ORDERS)
    con.commit()
    con.close()


def read_only(db_path: Path | str) -> sqlite3.Connection:
    uri = f"file:{db_path}?mode=ro"
    return sqlite3.connect(uri, uri=True)


def get_schema() -> str:
    """Return the DDL string for the built-in demo database."""
    return SCHEMA_SQL.strip()


def get_schema_from_db(db_path: Path | str) -> str:
    """Read CREATE TABLE statements directly from any SQLite file."""
    con = read_only(db_path)
    rows = con.execute(
        "SELECT sql FROM sqlite_master"
        " WHERE type='table' AND sql IS NOT NULL"
        " ORDER BY name"
    ).fetchall()
    con.close()
    return "\n\n".join(row[0] for row in rows)
