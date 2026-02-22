from app.schemas import RecommendationEnum


class NemotronNode:
    """Deterministic local reasoner for workflow testing."""

    async def __call__(self, state):
        state.tryout += 1
        market = state.market_data or {}
        ratio = float(market.get("offer_vs_market_ratio", 1.0))
        sample = int(market.get("sample_size", 0))

        if sample < 3:
            recommendation = RecommendationEnum.needs_more_info.value
            confidence = 0.35
            risks = ["Insufficient comparable market data for this role and profile."]
        elif ratio >= 1.1:
            recommendation = RecommendationEnum.accept.value
            confidence = 0.82
            risks = ["Equity terms and vesting still require review before signing."]
        elif ratio >= 0.95:
            recommendation = RecommendationEnum.renegotiate.value
            confidence = 0.7
            risks = ["Compensation is near market; upside likely depends on negotiation leverage."]
        else:
            recommendation = RecommendationEnum.renegotiate.value
            confidence = 0.76
            risks = ["Offer appears below market benchmarks based on available comparables."]

        score = max(0.0, min(10.0, 6.0 + (ratio - 1.0) * 6.0))
        offer_total = float(market.get("offer_total_est", 0.0))
        market_total = float(market.get("market_total_est", 0.0))
        delta = round(offer_total - market_total, 2)

        state.llm_response = {
            "score": round(score, 1),
            "recommendation": recommendation,
            "confidence": max(0.0, min(1.0, confidence)),
            "key_drivers": [
                {
                    "label": f"Total compensation delta vs market estimate: {delta}",
                    "impact": "positive" if delta >= 0 else "negative",
                },
                {
                    "label": f"Matched market sample size: {sample}",
                    "impact": "neutral" if sample >= 3 else "negative",
                },
                {
                    "label": f"Data source: {market.get('provider', 'unknown')}",
                    "impact": "neutral",
                },
            ],
            "negotiation_targets": [
                {
                    "item": "Base salary",
                    "ask": "Increase base salary toward market median or above.",
                    "reason": "Base cash has strongest predictable impact and benchmark support.",
                },
                {
                    "item": "Signing bonus",
                    "ask": "Request additional signing bonus to close near-term gap.",
                    "reason": "One-time compensation can bridge immediate market shortfall.",
                },
            ],
            "risks": risks[:6],
            "followup_questions": [
                "Can you share the exact equity vesting schedule and any acceleration terms?",
                "How is bonus eligibility measured and paid for the first performance cycle?",
            ][:3],
            "one_paragraph_summary": (
                f"This workflow run compares your estimated total compensation ({offer_total:,.0f}) "
                f"against matched market data ({market_total:,.0f}) using local CSV benchmarks. "
                f"The offer-to-market ratio is {ratio:.2f}, producing a {recommendation} recommendation "
                "with confidence adjusted by sample coverage."
            )[:600],
        }
        return state
