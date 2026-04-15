"""Database — PostgreSQL / Redis / DuckDB integrations."""
from __future__ import annotations


class DatabaseTopic:
    name = "database"
    tools = ["postgresql", "sqlite", "redis", "clickhouse", "duckdb", "mongodb", "timescaledb"]

    def duckdb_query(self, sql: str, db_path: str = ":memory:") -> list:
        try:
            import duckdb
            conn = duckdb.connect(db_path)
            return conn.execute(sql).fetchall()
        except ImportError:
            return [{"error": "duckdb not installed"}]
