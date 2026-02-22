import os
from statistics import median
from typing import Any

from databricks import sql

def _norm(value: str | None) -> str:
    return (value or "").strip().lower()


class DatabricksNode:
    """Market data provider backed by Databricks SQL."""

    def __init__(self):
        self.source_mode = _norm(os.getenv("MARKET_DATA_SOURCE", "local")) or "local"
        self.db_server_hostname = os.getenv("DATABRICKS_SERVER_HOSTNAME")
        self.db_http_path = os.getenv("DATABRICKS_HTTP_PATH")
        self.db_token = os.getenv("DATABRICKS_TOKEN")
        self.db_table = os.getenv("MARKET_DATA_TABLE", "workspace.buildathon.market_data_intelligent")
        self.db_limit = int(os.getenv("MARKET_DATA_LIMIT", "5000"))

    @staticmethod
    def _sql_quote(value: str) -> str:
        return "'" + value.replace("'", "''") + "'"

    @staticmethod
    def _as_dict_row(row: Any) -> dict:
        if hasattr(row, "asDict"):
            return row.asDict()
        if isinstance(row, dict):
            return row
        try:
            return dict(row)
        except Exception:
            return {}

    def _describe_columns(self, conn) -> list[str]:
        with conn.cursor() as cur:
            cur.execute(f"DESCRIBE TABLE {self.db_table}")
            rows = cur.fetchall()
        columns: list[str] = []
        for row in rows:
            data = self._as_dict_row(row)
            name = str(data.get("col_name", "")).strip()
            if not name or name.startswith("#"):
                continue
            columns.append(name.lower())
        return columns

    @staticmethod
    def _pick(columns: list[str], options: list[str]) -> str | None:
        for opt in options:
            if opt.lower() in columns:
                return opt.lower()
        return None

    def _select_expr(self, col: str | None, default_expr: str, alias: str, cast_numeric: bool = False) -> str:
        if not col:
            return f"{default_expr} AS {alias}"
        if cast_numeric:
            return f"CAST({col} AS DOUBLE) AS {alias}"
        return f"{col} AS {alias}"

    def _fetch_rows_from_databricks(self, state) -> list[dict]:
        if self.source_mode != "databricks":
            return []
        if not (self.db_server_hostname and self.db_http_path and self.db_token and self.db_table):
            return []

        with sql.connect(
            server_hostname=self.db_server_hostname,
            http_path=self.db_http_path,
            access_token=self.db_token,
        ) as conn:
            cols = self._describe_columns(conn)
            if not cols:
                return []

            industry_col = self._pick(cols, ["industry"])
            title_col = self._pick(cols, ["job_title", "job_or_title"])
            remote_col = self._pick(cols, ["remote_status", "remote_onsite"])
            base_col = self._pick(cols, ["base_salary"])
            bonus_col = self._pick(cols, ["bonus", "bonus_val", "bonus_amount", "bonus_pct"])
            signing_col = self._pick(cols, ["signing_bonus"])

            select_sql = ", ".join(
                [
                    self._select_expr(industry_col, "'Unknown'", "industry"),
                    self._select_expr(title_col, "'Unknown'", "job_title"),
                    self._select_expr(remote_col, "'Unknown'", "remote_status"),
                    self._select_expr(base_col, "CAST(0 AS DOUBLE)", "base_salary", cast_numeric=True),
                    self._select_expr(bonus_col, "CAST(0 AS DOUBLE)", "bonus", cast_numeric=True),
                    self._select_expr(signing_col, "CAST(0 AS DOUBLE)", "signing_bonus", cast_numeric=True),
                ]
            )

            possible_filters: list[list[str]] = []
            strict_filters: list[str] = []
            relaxed_filters: list[str] = []
            industry_only_filters: list[str] = []
            if industry_col and _norm(state.industry):
                industry_match = f"lower({industry_col}) = lower({self._sql_quote(str(state.industry))})"
                strict_filters.append(industry_match)
                relaxed_filters.append(industry_match)
                industry_only_filters.append(industry_match)
            if title_col and _norm(state.job_title):
                title_match = f"lower({title_col}) = lower({self._sql_quote(str(state.job_title))})"
                strict_filters.append(title_match)
                relaxed_filters.append(title_match)
            if remote_col and _norm(state.remote_status):
                strict_filters.append(f"lower({remote_col}) = lower({self._sql_quote(str(state.remote_status))})")

            if strict_filters:
                possible_filters.append(strict_filters)
            if relaxed_filters and relaxed_filters != strict_filters:
                possible_filters.append(relaxed_filters)
            if industry_only_filters and industry_only_filters != relaxed_filters:
                possible_filters.append(industry_only_filters)
            possible_filters.append([])

            rows: list[Any] = []
            for filters in possible_filters:
                where_clause = f" WHERE {' AND '.join(filters)}" if filters else ""
                query = f"SELECT {select_sql} FROM {self.db_table}{where_clause} LIMIT {max(1, self.db_limit)}"
                with conn.cursor() as cur:
                    cur.execute(query)
                    rows = cur.fetchall()
                if rows:
                    break

        normalized: list[dict] = []
        for row in rows:
            data = self._as_dict_row(row)
            normalized.append(
                {
                    "industry": data.get("industry"),
                    "job_title": data.get("job_title"),
                    "remote_status": data.get("remote_status"),
                    "base_salary": data.get("base_salary"),
                    "bonus": data.get("bonus"),
                    "signing_bonus": data.get("signing_bonus"),
                }
            )
        return normalized

    def _filter_rows(self, rows: list[dict], state) -> list[dict]:
        industry = _norm(state.industry)
        title = _norm(state.job_title)
        remote = _norm(state.remote_status)

        strict = [
            r
            for r in rows
            if _norm(r.get("industry")) == industry
            and _norm(r.get("job_title", r.get("job_or_title"))) == title
            and _norm(r.get("remote_status", r.get("remote_onsite"))) == remote
        ]
        if strict:
            return strict

        relaxed = [
            r
            for r in rows
            if _norm(r.get("industry")) == industry and _norm(r.get("job_title", r.get("job_or_title"))) == title
        ]
        if relaxed:
            return relaxed

        return [r for r in rows if _norm(r.get("industry")) == industry] or rows

    @staticmethod
    def _to_float(row: dict, key: str) -> float:
        raw = str(row.get(key, "")).strip()
        try:
            return float(raw) if raw else 0.0
        except ValueError:
            return 0.0

    def _benchmark(self, rows: list[dict], state, provider: str) -> dict:
        base_vals = [self._to_float(r, "base_salary") for r in rows]
        bonus_vals = [self._to_float(r, "bonus") for r in rows]
        signing_vals = [self._to_float(r, "signing_bonus") for r in rows]

        bonus_amount = float(state.base_salary or 0) * float(state.bonus_pct or 0) / 100.0
        offer_total = float(state.base_salary or 0) + bonus_amount + float(state.equity_val or 0) + float(
            state.signing_bonus or 0
        )

        market_base_median = float(median(base_vals)) if base_vals else 0.0
        market_bonus_avg = float(sum(bonus_vals) / len(bonus_vals)) if bonus_vals else 0.0
        market_signing_avg = float(sum(signing_vals) / len(signing_vals)) if signing_vals else 0.0
        market_total_est = market_base_median + market_bonus_avg + market_signing_avg

        ratio = offer_total / market_total_est if market_total_est > 0 else 1.0
        return {
            "provider": provider,
            "databricks_table": self.db_table,
            "sample_size": len(rows),
            "market_base_median": round(market_base_median, 2),
            "market_bonus_avg": round(market_bonus_avg, 2),
            "market_signing_avg": round(market_signing_avg, 2),
            "market_total_est": round(market_total_est, 2),
            "offer_total_est": round(offer_total, 2),
            "offer_vs_market_ratio": round(ratio, 4),
        }

    async def __call__(self, state):
        provider = "databricks_sql"
        rows: list[dict] = []

        if self.source_mode != "databricks":
            provider = "databricks_disabled"
        else:
            try:
                rows = self._fetch_rows_from_databricks(state)
            except Exception:
                provider = "databricks_error"
                rows = []

        matched = self._filter_rows(rows, state) if rows else []
        state.market_data = self._benchmark(matched, state, provider=provider)
        return state