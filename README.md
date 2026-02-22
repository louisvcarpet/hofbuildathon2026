# hofbuildathon2026

## Backend LLM Environment

Use these variables for the offer evaluation backend:

- `USE_LLM_STUB` - `true|false`, enables deterministic local stub when true.
- `NIM_BASE_URL` - NVIDIA/OpenAI-compatible base URL (example: `https://integrate.api.nvidia.com/v1`).
- `NIM_API_KEY` - API key for NIM access.
- `NIM_MODEL` - model id (example: `nvidia/nvidia-nemotron-nano-9b-v2`).
- `NIM_JSON_MODE` - `true|false`, requests JSON mode with `response_format` when supported.
- `USE_COMP_STUB` - `true|false`, controls Databricks comp stub fallback.
