import sqlite3
from pathlib import Path
from typing import Iterable, List, Tuple

DB_PATH = Path("private.db")


def init_db(path: Path = DB_PATH) -> None:
    """Create the private SQLite database with sample data if it does not exist."""
    if path.exists():
        return

    path.touch()
    conn = sqlite3.connect(path)
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            department TEXT NOT NULL,
            salary INTEGER NOT NULL
        );
        """
    )

    seed_rows: List[Tuple[str, str, str, int]] = [
        ("Alice Johnson", "alice.j@example.com", "Engineering", 145000),
        ("Bob Smith", "bob.s@example.com", "Security", 160000),
        ("Carla Gomez", "carla.g@example.com", "Finance", 152000),
        ("Dev Patel", "dev.p@example.com", "Data Science", 148000),
        ("Emily Chen", "emily.c@example.com", "Product", 141000),
    ]

    cur.executemany(
        "INSERT INTO employees (name, email, department, salary) VALUES (?, ?, ?, ?);",
        seed_rows,
    )

    conn.commit()
    conn.close()


def run_insecure_query(user_input: str, path: Path = DB_PATH) -> Iterable[Tuple]:
    """
    Deliberately insecure query that interpolates user input directly into SQL.

    This mirrors a vulnerable backend. Do not use this pattern in real systems.
    """
    conn = sqlite3.connect(path)
    cur = conn.cursor()

    sql = f"""
    SELECT id, name, email, department, salary
    FROM employees
    WHERE name LIKE '%{user_input}%'
        OR department LIKE '%{user_input}%';
    """

    cur.execute(sql)
    rows = cur.fetchall()
    conn.close()
    return rows
