import sqlite3
from typing import Any

TASK_COLUMNS = "id,title,description,status,owner,priority,created_at"


def find_tasks_by_owner(connection: sqlite3.Connection, owner: str) -> list[sqlite3.Row]:
    sql = f"SELECT {TASK_COLUMNS} FROM tasks WHERE owner = ? ORDER BY id"
    return connection.execute(sql, (owner,)).fetchall()


def find_task_by_id(connection: sqlite3.Connection, task_id: int) -> sqlite3.Row:
    sql = f"SELECT {TASK_COLUMNS} FROM tasks WHERE id = ?"
    return connection.execute(sql, (task_id,)).fetchone()


def insert_task(connection: sqlite3.Connection, fields: dict[str, Any]) -> int:
    sql = (
        "INSERT INTO tasks(title,description,status,owner,priority,created_at) "
        "VALUES (?,?,?,?,?,datetime('now'))"
    )
    cursor = connection.execute(
        sql,
        (fields["title"], fields["description"], fields["status"], fields["owner"], fields["priority"]),
    )
    connection.commit()
    return int(cursor.lastrowid or 0)


def find_status_and_priority_by_owner(connection: sqlite3.Connection, owner: str) -> list[sqlite3.Row]:
    sql = "SELECT status,priority FROM tasks WHERE owner = ?"
    return connection.execute(sql, (owner,)).fetchall()
