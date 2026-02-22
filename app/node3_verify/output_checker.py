class OutputChecker:
    """Validates workflow output shape before ending the graph."""

    REQUIRED_KEYS = {
        "score",
        "recommendation",
        "confidence",
        "key_drivers",
        "negotiation_targets",
        "risks",
        "followup_questions",
        "one_paragraph_summary",
    }

    async def __call__(self, state):
        payload = state.llm_response if isinstance(state.llm_response, dict) else {}
        keys_ok = self.REQUIRED_KEYS.issubset(payload.keys())

        score = payload.get("score")
        confidence = payload.get("confidence")
        lists_ok = isinstance(payload.get("key_drivers"), list) and isinstance(
            payload.get("negotiation_targets"), list
        )
        scalars_ok = (
            isinstance(payload.get("recommendation"), str)
            and isinstance(payload.get("one_paragraph_summary"), str)
            and isinstance(payload.get("risks"), list)
            and isinstance(payload.get("followup_questions"), list)
        )
        range_ok = isinstance(score, (int, float)) and 0 <= float(score) <= 10 and isinstance(
            confidence, (int, float)
        ) and 0 <= float(confidence) <= 1

        if keys_ok and lists_ok and scalars_ok and range_ok:
            state.output_checker = "yes"
            state.result = payload
        else:
            state.output_checker = "no"
            state.result = {
                "error": "Workflow output validation failed",
                "tryout": state.tryout,
            }
        return state
