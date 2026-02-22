# OfferGo Buildathon (2026)

This repo contains:
- A FastAPI backend for PDF offer ingestion, evaluation workflow, Databricks market comps, and Nemotron chat.
- A React/Vite frontend for upload, analysis, and results UI.

## 1) Prerequisites

- Python 3.10+ (3.13 also works in this repo)
- Node.js 18+ and npm
- Databricks SQL warehouse access
- NVIDIA NIM API key (for Nemotron)

## 2) Clone and install

From repo root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Frontend:

```bash
cd frontend
npm install
cd ..
```

## 3) Environment file (`.env`)

Create/update `.env` in repo root:

```env
# Databricks
DATABRICKS_SERVER_HOSTNAME=dbc-xxxx.cloud.databricks.com
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/xxxxxxxx
DATABRICKS_TOKEN=dapi...
MARKET_DATA_SOURCE=databricks
MARKET_DATA_TABLE=workspace.buildathon.market_data_intelligent
MARKET_DATA_LIMIT=5000

# Nemotron
USE_LLM_STUB=false
WORKFLOW_USE_NEMOTRON=true
NIM_API_KEY=nvapi-...
NIM_BASE_URL=https://integrate.api.nvidia.com/v1
NIM_MODEL=nvidia/nvidia-nemotron-nano-9b-v2
NIM_JSON_MODE=true

# Optional legacy flag (safe to keep)
USE_COMP_STUB=true
```

## 4) Run backend

```bash
source .venv/bin/activate
python -m uvicorn app.main:app --reload --env-file .env --log-level debug
```

Backend base URL:
- `http://127.0.0.1:8000`

API docs:
- `http://127.0.0.1:8000/docs`

## 5) Run frontend

In a new terminal:

```bash
cd frontend
npm run dev
```

Frontend URL (default Vite):
- `http://127.0.0.1:8080` (or shown terminal port)

If needed, set `frontend/.env`:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## 6) End-to-end flow

1. Open frontend `/submit`
2. Upload a PDF offer
3. Set priorities and click **Analyze Offer**
4. App calls:
   - `POST /offers/ingest-pdf`
   - `POST /offers/{offer_id}/evaluate?mode=workflow`
   - `GET /offers/{offer_id}/market-snapshot`
5. Results page shows recommendation, score bars, market comparison, and Nemotron chat.

## 7) Quick API test with curl

Upload and create offer:

```bash
curl -X POST "http://127.0.0.1:8000/offers/ingest-pdf?create_records=true" \
  -H "X-User-Id: 42" \
  -F "file=@/absolute/path/to/offer.pdf" \
  -F "priority_financial=4" \
  -F "priority_career=3" \
  -F "priority_lifestyle=3" \
  -F "priority_alignment=3"
```

Evaluate (replace `<offer_id>`):

```bash
curl -X POST "http://127.0.0.1:8000/offers/<offer_id>/evaluate?mode=workflow" \
  -H "X-User-Id: 42"
```

Market snapshot:

```bash
curl "http://127.0.0.1:8000/offers/<offer_id>/market-snapshot" \
  -H "X-User-Id: 42"
```

Chat:

```bash
curl -X POST "http://127.0.0.1:8000/offers/<offer_id>/chat" \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 42" \
  -d '{"message":"Should I renegotiate base and bonus?"}'
```

## 8) Troubleshooting

- `Offer not found` in chat:
  - Re-run upload/analyze to generate a fresh `offer_id`.
- `LLM_AUTH_FAILED`:
  - Verify `NIM_API_KEY` and restart backend.
- Databricks connection appears active but no useful market rows:
  - Confirm `MARKET_DATA_TABLE` exists and contains expected columns/data.
- If frontend looks stale:
  - Hard refresh browser (`Cmd+Shift+R`).
