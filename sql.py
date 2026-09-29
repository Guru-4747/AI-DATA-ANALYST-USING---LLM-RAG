"""SQLite executes generated SQL with a deny-by-default authorizer."""
import json
import sqlite3
import time

import pandas as pd

FUNCTIONS = set('abs avg count max min sum total round coalesce ifnull nullif lower upper length trim ltrim rtrim substr substring replace instr like glob date time datetime julianday strftime unixepoch typeof cast group_concat row_number rank dense_rank lag lead first_value last_value ntile percent_rank cume_dist'.split())


def quote(name):
    return '"' + name.replace('"', '""') + '"'


def authorizer(allowed_tables):
    def check(action, arg1, arg2, database, trigger):
        if action in (sqlite3.SQLITE_SELECT, sqlite3.SQLITE_RECURSIVE):
            return sqlite3.SQLITE_OK
        if action == sqlite3.SQLITE_READ and arg1 in allowed_tables:
            return sqlite3.SQLITE_OK
        if action == sqlite3.SQLITE_FUNCTION and (arg2 or '').lower() in FUNCTIONS:
            return sqlite3.SQLITE_OK
        return sqlite3.SQLITE_DENY
    return check


def execute(tables, sql, limit=2000, timeout=4):
    if not sql.strip():
        raise ValueError('No SQL was generated.')
    conn = sqlite3.connect(':memory:')
    try:
        for name, frame in tables.items():
            frame.to_sql(name, conn, index=False, if_exists='replace')
        conn.execute('PRAGMA query_only=ON')
        conn.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 2_000_000)
        conn.setlimit(sqlite3.SQLITE_LIMIT_SQL_LENGTH, 30_000)
        conn.set_authorizer(authorizer(set(tables)))
        deadline = time.monotonic() + timeout
        conn.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
        cursor = conn.execute(sql)
        if cursor.description is None:
            raise ValueError('Only result-producing SELECT queries are permitted.')
        rows = cursor.fetchmany(limit + 1)
        frame = pd.DataFrame(rows[:limit], columns=[c[0] for c in cursor.description])
        if frame.columns.duplicated().any():
            raise ValueError('Duplicate output columns. Give each selected column a unique SQL alias.')
        return frame, len(rows) > limit
    finally:
        conn.close()


def schema(tables, include_samples=False):
    items = []
    for name, frame in tables.items():
        item = {'table': name, 'rows': len(frame), 'columns': [
            {'name': c, 'type': str(frame[c].dtype), 'nulls': int(frame[c].isna().sum())} for c in frame
        ]}
        if include_samples:
            item['examples'] = json.loads(frame.head(2).to_json(orient='records', date_format='iso'))
        items.append(item)
    return json.dumps(items, ensure_ascii=False, default=str)


def quality(frame):
    return pd.DataFrame([{'column': c, 'type': str(frame[c].dtype),
        'missing': int(frame[c].isna().sum()), 'unique': int(frame[c].nunique())} for c in frame])
