"""Datenbank-Layer: Verbindung, Schema und alle Queries."""

import psycopg
from psycopg.rows import dict_row

SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (
    id          serial PRIMARY KEY,
    name        text NOT NULL UNIQUE,
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS projects (
    id          serial PRIMARY KEY,
    name        text NOT NULL UNIQUE,
    customer_id integer REFERENCES customers(id) ON DELETE SET NULL,
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS time_entries (
    id          serial PRIMARY KEY,
    project_id  integer NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    description text NOT NULL DEFAULT '',
    started_at  timestamptz NOT NULL DEFAULT now(),
    ended_at    timestamptz,
    CHECK (ended_at IS NULL OR ended_at >= started_at)
);

CREATE INDEX IF NOT EXISTS idx_time_entries_started ON time_entries (started_at);
CREATE INDEX IF NOT EXISTS idx_time_entries_project ON time_entries (project_id);

CREATE TABLE IF NOT EXISTS notes (
    id          serial PRIMARY KEY,
    project_id  integer REFERENCES projects(id) ON DELETE CASCADE,
    customer_id integer REFERENCES customers(id) ON DELETE CASCADE,
    title       text NOT NULL DEFAULT '',
    body        text NOT NULL DEFAULT '',
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now(),
    CHECK (project_id IS NOT NULL OR customer_id IS NOT NULL)
);

CREATE TABLE IF NOT EXISTS issues (
    id          serial PRIMARY KEY,
    project_id  integer NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    note_id     integer REFERENCES notes(id) ON DELETE SET NULL,
    repo        text NOT NULL,
    number      integer NOT NULL,
    title       text NOT NULL,
    url         text NOT NULL,
    state       text NOT NULL DEFAULT 'open',
    created_at  timestamptz NOT NULL DEFAULT now(),
    UNIQUE (repo, number)
);

ALTER TABLE projects     ADD COLUMN IF NOT EXISTS github_repo text;
ALTER TABLE time_entries ADD COLUMN IF NOT EXISTS issue_id integer
    REFERENCES issues(id) ON DELETE SET NULL;

CREATE OR REPLACE VIEW time_report AS
SELECT
    e.id,
    e.started_at,
    e.ended_at,
    COALESCE(e.ended_at, now()) - e.started_at AS duration,
    p.name  AS project,
    c.name  AS customer,
    e.description,
    i.repo   AS issue_repo,
    i.number AS issue_number,
    i.title  AS issue_title,
    i.url    AS issue_url
FROM time_entries e
JOIN projects p ON p.id = e.project_id
LEFT JOIN customers c ON c.id = p.customer_id
LEFT JOIN issues i ON i.id = e.issue_id;
"""


class Database:
    def __init__(self, dsn: str | None = None):
        if dsn is None:
            from .settings import resolve_dsn  # lazy: hält db.py für Tests Qt-frei
            dsn = resolve_dsn()
        self.dsn = dsn
        self._connect()
        with self.conn.cursor() as cur:
            cur.execute(SCHEMA)

    def _connect(self):
        self.conn = psycopg.connect(
            self.dsn, row_factory=dict_row, autocommit=True, connect_timeout=5)

    def reconnect(self, dsn: str):
        """Zur Laufzeit auf eine neue Verbindung wechseln.

        Schlägt der Aufbau fehl, bleibt die bisherige Verbindung unverändert aktiv.
        """
        new_conn = psycopg.connect(
            dsn, row_factory=dict_row, autocommit=True, connect_timeout=5)
        new_conn.execute(SCHEMA)
        old_conn, self.conn, self.dsn = self.conn, new_conn, dsn
        try:
            old_conn.close()
        except Exception:  # noqa: BLE001 - alte Verbindung ist ohnehin obsolet
            pass

    def _cursor(self):
        """Cursor mit einmaligem Reconnect, falls die Verbindung weg ist."""
        if self.conn.closed:
            self._connect()
        try:
            self.conn.execute("SELECT 1")
        except psycopg.OperationalError:
            self._connect()
        return self.conn.cursor()

    # ---- Projekte -------------------------------------------------------

    def ensure_project(self, name: str) -> int:
        with self._cursor() as cur:
            cur.execute(
                """INSERT INTO projects (name) VALUES (%s)
                   ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
                   RETURNING id""",
                (name.strip(),),
            )
            return cur.fetchone()["id"]

    def project_names(self) -> list[str]:
        """Projektnamen, zuletzt bebuchte zuerst."""
        with self._cursor() as cur:
            cur.execute(
                """SELECT p.name
                   FROM projects p
                   LEFT JOIN (
                       SELECT project_id, max(started_at) AS last_used
                       FROM time_entries GROUP BY project_id
                   ) t ON t.project_id = p.id
                   ORDER BY t.last_used DESC NULLS LAST, p.name"""
            )
            return [r["name"] for r in cur.fetchall()]

    def projects_with_customers(self) -> list[dict]:
        with self._cursor() as cur:
            cur.execute(
                """SELECT p.id, p.name, p.customer_id, c.name AS customer
                   FROM projects p
                   LEFT JOIN customers c ON c.id = p.customer_id
                   ORDER BY p.name"""
            )
            return cur.fetchall()

    def set_project_customer(self, project_id: int, customer_id: int | None):
        with self._cursor() as cur:
            cur.execute(
                "UPDATE projects SET customer_id = %s WHERE id = %s",
                (customer_id, project_id),
            )

    def project_by_id(self, project_id: int) -> dict | None:
        with self._cursor() as cur:
            cur.execute(
                "SELECT id, name, customer_id, github_repo FROM projects WHERE id = %s",
                (project_id,),
            )
            return cur.fetchone()

    def project_id_by_name(self, name: str) -> int | None:
        with self._cursor() as cur:
            cur.execute("SELECT id FROM projects WHERE name = %s", (name.strip(),))
            row = cur.fetchone()
            return row["id"] if row else None

    def set_project_repo(self, project_id: int, repo: str):
        with self._cursor() as cur:
            cur.execute(
                "UPDATE projects SET github_repo = %s WHERE id = %s",
                (repo.strip() or None, project_id),
            )

    # ---- Issues ---------------------------------------------------------

    def create_issue(self, *, project_id: int, note_id: int | None, repo: str,
                     number: int, title: str, url: str) -> int:
        with self._cursor() as cur:
            cur.execute(
                """INSERT INTO issues (project_id, note_id, repo, number, title, url)
                   VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""",
                (project_id, note_id, repo, number, title, url),
            )
            return cur.fetchone()["id"]

    def open_issues(self, project_id: int) -> list[dict]:
        with self._cursor() as cur:
            cur.execute(
                """SELECT id, repo, number, title, url FROM issues
                   WHERE project_id = %s AND state = 'open'
                   ORDER BY number DESC""",
                (project_id,),
            )
            return cur.fetchall()

    def set_issue_state(self, issue_id: int, state: str):
        with self._cursor() as cur:
            cur.execute("UPDATE issues SET state = %s WHERE id = %s", (state, issue_id))

    def issue_totals(self, since_sql: str | None) -> list[dict]:
        where = f"AND started_at >= {since_sql}" if since_sql else ""
        with self._cursor() as cur:
            cur.execute(
                f"""SELECT issue_repo, issue_number, issue_title, project,
                        EXTRACT(EPOCH FROM sum(COALESCE(ended_at, now()) - started_at)) AS secs
                    FROM time_report
                    WHERE issue_number IS NOT NULL {where}
                    GROUP BY issue_repo, issue_number, issue_title, project
                    ORDER BY secs DESC"""
            )
            return cur.fetchall()

    # ---- Kunden ---------------------------------------------------------

    def customers(self) -> list[dict]:
        with self._cursor() as cur:
            cur.execute("SELECT id, name FROM customers ORDER BY name")
            return cur.fetchall()

    def ensure_customer(self, name: str) -> int:
        with self._cursor() as cur:
            cur.execute(
                """INSERT INTO customers (name) VALUES (%s)
                   ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
                   RETURNING id""",
                (name.strip(),),
            )
            return cur.fetchone()["id"]

    # ---- Zeiteinträge ---------------------------------------------------

    def start_entry(self, project_id: int, description: str,
                    issue_id: int | None = None) -> int:
        with self._cursor() as cur:
            cur.execute(
                """INSERT INTO time_entries (project_id, description, issue_id)
                   VALUES (%s, %s, %s) RETURNING id""",
                (project_id, description, issue_id),
            )
            return cur.fetchone()["id"]

    def stop_entry(self, entry_id: int, description: str):
        with self._cursor() as cur:
            cur.execute(
                """UPDATE time_entries
                   SET ended_at = now(), description = %s
                   WHERE id = %s""",
                (description, entry_id),
            )

    def open_entry(self) -> dict | None:
        """Laufender (nicht gestoppter) Eintrag, falls vorhanden."""
        with self._cursor() as cur:
            cur.execute(
                """SELECT e.id, e.description, e.started_at, e.issue_id,
                          p.name AS project
                   FROM time_entries e JOIN projects p ON p.id = e.project_id
                   WHERE e.ended_at IS NULL
                   ORDER BY e.started_at DESC LIMIT 1"""
            )
            return cur.fetchone()

    def discard_entry(self, entry_id: int):
        with self._cursor() as cur:
            cur.execute("DELETE FROM time_entries WHERE id = %s", (entry_id,))

    def update_entry_description(self, entry_id: int, description: str):
        with self._cursor() as cur:
            cur.execute(
                "UPDATE time_entries SET description = %s WHERE id = %s",
                (description, entry_id),
            )

    def today_seconds(self) -> int:
        """Summe aller heutigen Einträge in Sekunden (laufende bis jetzt)."""
        with self._cursor() as cur:
            cur.execute(
                """SELECT COALESCE(EXTRACT(EPOCH FROM
                       sum(COALESCE(ended_at, now()) - started_at)), 0) AS secs
                   FROM time_entries
                   WHERE started_at >= date_trunc('day', now())"""
            )
            return int(cur.fetchone()["secs"])

    def entries_since(self, since_sql: str | None) -> list[dict]:
        """Einträge ab Zeitraum-Ausdruck (SQL-Fragment aus fester Liste) inkl. Summe."""
        where = f"WHERE started_at >= {since_sql}" if since_sql else ""
        with self._cursor() as cur:
            cur.execute(
                f"""SELECT id, started_at, ended_at,
                        EXTRACT(EPOCH FROM (COALESCE(ended_at, now()) - started_at)) AS secs,
                        project, customer, description,
                        issue_repo, issue_number, issue_title
                    FROM time_report {where}
                    ORDER BY started_at DESC"""
            )
            return cur.fetchall()

    def project_totals(self, since_sql: str | None) -> list[dict]:
        where = f"WHERE started_at >= {since_sql}" if since_sql else ""
        with self._cursor() as cur:
            cur.execute(
                f"""SELECT project,
                        EXTRACT(EPOCH FROM sum(COALESCE(ended_at, now()) - started_at)) AS secs
                    FROM time_report {where}
                    GROUP BY project ORDER BY secs DESC"""
            )
            return cur.fetchall()

    # ---- Notizen --------------------------------------------------------

    def notes_for(self, *, project_id: int | None = None, customer_id: int | None = None) -> list[dict]:
        col = "project_id" if project_id is not None else "customer_id"
        val = project_id if project_id is not None else customer_id
        with self._cursor() as cur:
            cur.execute(
                f"""SELECT id, title, body, updated_at FROM notes
                    WHERE {col} = %s ORDER BY updated_at DESC""",
                (val,),
            )
            return cur.fetchall()

    def create_note(self, *, project_id: int | None = None, customer_id: int | None = None,
                    title: str = "", body: str = "") -> int:
        with self._cursor() as cur:
            cur.execute(
                """INSERT INTO notes (project_id, customer_id, title, body)
                   VALUES (%s, %s, %s, %s) RETURNING id""",
                (project_id, customer_id, title, body),
            )
            return cur.fetchone()["id"]

    def update_note(self, note_id: int, title: str, body: str):
        with self._cursor() as cur:
            cur.execute(
                """UPDATE notes SET title = %s, body = %s, updated_at = now()
                   WHERE id = %s""",
                (title, body, note_id),
            )

    def delete_note(self, note_id: int):
        with self._cursor() as cur:
            cur.execute("DELETE FROM notes WHERE id = %s", (note_id,))
