import csv
import os
from pathlib import Path
from statistics import median


def _norm(value: str | None) -> str:
    return (value or "").strip().lower()


class DatabricksNode:
    """Market data provider with local CSV default and Databricks-ready mode flag."""

    def __init__(self, csv_path: str | None = None):
        default_path = Path(__file__).resolve().parents[2] / "data" / "databast_test.csv"
        self.csv_path = Path(csv_path or os.getenv("MARKET_DATA_CSV_PATH", str(default_path)))
        self.source_mode = _norm(os.getenv("MARKET_DATA_SOURCE", "local")) or "local"

    def _load_rows(self) -> list[dict]:
        if not self.csv_path.exists():
            return []
        with self.csv_path.open("r", encoding="utf-8", newline="") as fh:
            return list(csv.DictReader(fh))

    def _filter_rows(self, rows: list[dict], state) -> list[dict]:
        industry = _norm(state.industry)
        title = _norm(state.job_title)
        remote = _norm(state.remote_status)

        strict = [
            r
            for r in rows
            if _norm(r.get("industry")) == industry
            and _norm(r.get("job_or_title")) == title
            and _norm(r.get("remote_onsite")) == remote
        ]
        if strict:
            return strict

        relaxed = [
            r
            for r in rows
            if _norm(r.get("industry")) == industry and _norm(r.get("job_or_title")) == title
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

    def _benchmark(self, rows: list[dict], state) -> dict:
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
            "provider": "local_csv" if self.source_mode != "databricks" else "databricks_fallback_local_csv",
            "csv_path": str(self.csv_path),
            "sample_size": len(rows),
            "market_base_median": round(market_base_median, 2),
            "market_bonus_avg": round(market_bonus_avg, 2),
            "market_signing_avg": round(market_signing_avg, 2),
            "market_total_est": round(market_total_est, 2),
            "offer_total_est": round(offer_total, 2),
            "offer_vs_market_ratio": round(ratio, 4),
        }

    async def __call__(self, state):
        rows = self._load_rows()
        matched = self._filter_rows(rows, state) if rows else []
        state.market_data = self._benchmark(matched, state)
        return state