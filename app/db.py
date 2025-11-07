import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta


def ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(os.path.abspath(path))
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)


@contextmanager
def get_conn(db_path: str):
    ensure_parent_dir(db_path)
    conn = sqlite3.connect(db_path)
    try:
        conn.row_factory = sqlite3.Row
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: str) -> None:
    with get_conn(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_name TEXT NOT NULL,
                server_name TEXT NOT NULL,
                owner_name TEXT NOT NULL,
                owner_phone TEXT NOT NULL,
                server_login_username TEXT,
                server_login_password TEXT,
                server_ip TEXT,
                root_password TEXT,
                start_date TEXT NOT NULL,
                next_due_date TEXT NOT NULL
            );
            """
        )
        # Migrate existing database - add new columns if they don't exist
        try:
            conn.execute("ALTER TABLE projects ADD COLUMN server_login_username TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists
        try:
            conn.execute("ALTER TABLE projects ADD COLUMN server_login_password TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE projects ADD COLUMN server_ip TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE projects ADD COLUMN root_password TEXT")
        except sqlite3.OperationalError:
            pass


def add_project(db_path: str, project_name: str, server_name: str, owner_name: str, owner_phone: str, 
                server_login_username: str, server_login_password: str, server_ip: str, root_password: str,
                start_date: datetime, next_due_date: datetime) -> int:
    with get_conn(db_path) as conn:
        cur = conn.execute(
            """
            INSERT INTO projects (project_name, server_name, owner_name, owner_phone, 
                                 server_login_username, server_login_password, server_ip, root_password,
                                 start_date, next_due_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project_name,
                server_name,
                owner_name,
                owner_phone,
                server_login_username,
                server_login_password,
                server_ip,
                root_password,
                start_date.isoformat(),
                next_due_date.isoformat(),
            ),
        )
        return int(cur.lastrowid)


def list_projects(db_path: str):
    with get_conn(db_path) as conn:
        rows = conn.execute(
            """SELECT id, project_name, server_name, owner_name, owner_phone, 
                      server_login_username, server_login_password, server_ip, root_password,
                      start_date, next_due_date 
               FROM projects ORDER BY id DESC"""
        ).fetchall()
        return [dict(r) for r in rows]


def delete_project(db_path: str, project_id: int) -> bool:
    with get_conn(db_path) as conn:
        cur = conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        return cur.rowcount > 0


def get_due_projects(db_path: str, now: datetime):
    """Get projects that are due today or earlier"""
    with get_conn(db_path) as conn:
        # Compare dates only (ignore time part)
        now_date = now.date().isoformat()
        rows = conn.execute(
            "SELECT * FROM projects WHERE date(next_due_date) <= date(?)",
            (now_date,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_projects_due_in_days(db_path: str, now: datetime, days: int):
    """Get projects that are due in exactly N days (for reminder notifications)"""
    with get_conn(db_path) as conn:
        target_date = (now.date() + timedelta(days=days)).isoformat()
        rows = conn.execute(
            "SELECT * FROM projects WHERE date(next_due_date) = date(?)",
            (target_date,),
        ).fetchall()
        return [dict(r) for r in rows]


def bump_next_due_date(db_path: str, project_id: int):
    with get_conn(db_path) as conn:
        row = conn.execute("SELECT next_due_date FROM projects WHERE id = ?", (project_id,)).fetchone()
        if not row:
            return False
        current_due = datetime.fromisoformat(row["next_due_date"]) if row["next_due_date"] else datetime.now()
        # Add 30 days to the date part only, keeping time at midnight
        new_due_date = current_due.date() + timedelta(days=30)
        new_due = datetime.combine(new_due_date, datetime.min.time())
        conn.execute("UPDATE projects SET next_due_date = ? WHERE id = ?", (new_due.isoformat(), project_id))
        return True


def set_next_due_date(db_path: str, project_id: int, new_due: datetime) -> bool:
    with get_conn(db_path) as conn:
        cur = conn.execute("UPDATE projects SET next_due_date = ? WHERE id = ?", (new_due.isoformat(), project_id))
        return cur.rowcount > 0

