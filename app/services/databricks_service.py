import os

from app.schemas import MarketComps


def get_market_comps(role_title: str | None, level: str | None, location: str | None) -> dict:
    use_stub = os.getenv("USE_COMP_STUB", "true").lower() == "true"
    if use_stub:
        if not role_title or not level or not location:
            return MarketComps(sample_size=0).model_dump()
        # Lightweight deterministic comp stub for MVP.
        level_boost = {"junior": 0.9, "mid": 1.0, "senior": 1.25, "staff": 1.45}.get(level.lower(), 1.0)
        baseline = 160_000 * level_boost
        return MarketComps(
            p25=round(baseline * 0.85, 2),
            median=round(baseline, 2),
            p75=round(baseline * 1.2, 2),
            sample_size=60,
        ).model_dump()

    # Placeholder for real Databricks wrapper integration.
    # If unavailable, we still proceed with sample_size=0 and reduced confidence.
    return MarketComps(sample_size=0).model_dump()
