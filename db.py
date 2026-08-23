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
import requests
import streamlit as st
from datetime import date

def _get_headers():
    # Read directly from secrets, ignoring whatever app.py passes
    url = st.secrets.get("SUPABASE_URL", "").strip("/")
    key = st.secrets.get("SUPABASE_SECRET_KEY", st.secrets.get("SUPABASE_KEY", ""))
    
    if not url or not key:
        raise ValueError("Missing SUPABASE_URL or SUPABASE_SECRET_KEY in secrets.")
        
    return url, {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }


def save_briefing_row(
    connection_string: str,
    run_date: date,
    story: dict,
    analyst_json: dict,
    coach_json: dict,
    **kwargs
) -> int:
    """Insert one briefing row into the briefings table using REST API."""
    url, headers = _get_headers()
    endpoint = f"{url}/rest/v1/briefings"
    
    payload = {
        "date": run_date.isoformat(),
        "title": story.get("title", ""),
        "source": story.get("source", ""),
        "link": story.get("link", ""),
        "analyst_json": analyst_json,
        "coach_json": coach_json,
        "run_id": kwargs.get("run_id") or run_date.isoformat()
    }
    
    resp = requests.post(endpoint, headers=headers, json=payload)
    resp.raise_for_status()
    data = resp.json()
    return data[0]["id"] if data else 0


def fetch_briefing_dates(connection_string: str) -> list[str]:
    """Return a sorted (descending) list of distinct run_ids using REST API."""
    url, headers = _get_headers()
    endpoint = f"{url}/rest/v1/briefings"
    params = {"select": "run_id,date"}
    
    resp = requests.get(endpoint, headers=headers, params=params)
    resp.raise_for_status()
    rows = resp.json()
    
    labels = set()
    for r in rows:
        label = r.get("run_id") or r.get("date")
        if label:
            labels.add(str(label))
            
    return sorted(list(labels), reverse=True)


def fetch_briefings_for_date(connection_string: str, target_run_id: str) -> list[dict]:
    """Return all briefing rows for a given run_id using REST API."""
    url, headers = _get_headers()
    endpoint = f"{url}/rest/v1/briefings"
    
    # If the target contains a space (e.g. "2026-08-23 10:30 PM"), it's a run_id.
    # If it doesn't (e.g. "2026-08-23"), it's a legacy date fallback.
    if " " in target_run_id:
        # Match only exact run_id
        # We need to surround the string in double quotes for PostgREST if it has spaces
        # actually requests handles URL encoding, but PostgREST exact match on strings with spaces requires quotes inside the eq.
        params = {
            "run_id": f"eq.{target_run_id}",
            "order": "id.asc"
        }
    else:
        # Match legacy rows that have this date AND no run_id
        params = {
            "date": f"eq.{target_run_id}",
            "run_id": "is.null",
            "order": "id.asc"
        }
    
    resp = requests.get(endpoint, headers=headers, params=params)
    resp.raise_for_status()
    return resp.json()
