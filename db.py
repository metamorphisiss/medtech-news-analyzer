# db.py
# Supabase / Postgres persistence layer.
#
# VERIFIED AT BUILD TIME:
#   - Using psycopg2 with direct Postgres connection string (port 5432) for a backend
#     server-side script. This is cleaner than supabase-py for this use case because:
#       (a) No RLS required — single-user app
#       (b) Full SQL control needed for date-range queries
#       (c) Avoids the supabase-py REST overhead for a backend pipeline
#   - Connection string format: postgresql://postgres:[password]@[host]:5432/postgres
#     (Supabase provides this under Project Settings > Database > Connection String)
#
# Table schema (run once in Supabase SQL editor — see Section 7 of build spec):
# Note: Schema updated for v2 thorough build to store coach_json as JSONB
#
#   CREATE TABLE briefings (
#       id               SERIAL PRIMARY KEY,
#       date             DATE NOT NULL,
#       title            TEXT NOT NULL,
#       source           TEXT,
#       link             TEXT,
#       analyst_json     JSONB,
#       coach_json       JSONB,
#       created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#   );

import json
import psycopg2
import psycopg2.extras
from datetime import date


def _get_connection(connection_string: str):
    """Open a new psycopg2 connection. Caller is responsible for closing."""
    conn = psycopg2.connect(connection_string, sslmode="require")
    return conn


def save_briefing_row(
    connection_string: str,
    run_date: date,
    story: dict,
    analyst_json: dict,
    coach_json: dict,
    **kwargs
) -> int:
    """
    Insert one briefing row (one story) into the briefings table.
    Returns the new row's id.

    Arguments:
        connection_string : Supabase Postgres connection string from secrets
        run_date          : The date this pipeline run covers (usually today)
        story             : Scout output dict with keys: title, link, source, published_date
        analyst_json      : Analyst output dict (MBA-lens fields)
        coach_json        : Coach output dict (GDPI prep + dashboard components)
    """
    sql = """
        INSERT INTO briefings
            (date, title, source, link, analyst_json, coach_json, run_id)
        VALUES
            (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id;
    """
    with _get_connection(connection_string) as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql,
                (
                    run_date,
                    story.get("title", ""),
                    story.get("source", ""),
                    story.get("link", ""),
                    json.dumps(analyst_json),
                    json.dumps(coach_json),
                    kwargs.get("run_id") or run_date.isoformat(),
                ),
            )
            new_id = cur.fetchone()[0]
        conn.commit()
    return new_id


def fetch_briefing_dates(connection_string: str) -> list[str]:
    """
    Return a sorted (descending) list of distinct run_ids that have briefings stored.
    Used to populate the Past Briefings selector in the UI.
    Fallback to date if run_id is NULL for older entries.
    """
    sql = "SELECT DISTINCT COALESCE(run_id, date::text) as run_label FROM briefings ORDER BY run_label DESC;"
    with _get_connection(connection_string) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
    return [row[0] for row in rows]


def fetch_briefings_for_date(connection_string: str, target_run_id: str) -> list[dict]:
    """
    Return all briefing rows for a given run_id (or date string as fallback), ordered by id (insertion order).
    Each row is returned as a dict matching the table columns.
    """
    sql = """
        SELECT id, date, title, source, link, analyst_json, coach_json, created_at, run_id
        FROM briefings
        WHERE COALESCE(run_id, date::text) = %s
        ORDER BY id ASC;
    """
    with _get_connection(connection_string) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (target_run_id,))
            rows = cur.fetchall()
    return [dict(row) for row in rows]
