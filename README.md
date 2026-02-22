# OfferGo
Built by Blake Chang, Danny Hua, Frankie Wu, Sean Xia

OfferGo is a full-stack app that:
- ingests offer letters (PDF),
- benchmarks compensation using Databricks market data,
- runs a Nemotron-based evaluation workflow,
- shows recommendations + charts,
- supports follow-up chat on the analyzed offer.

This guide is written for someone cloning the repo on a new machine.

## 1) Prerequisites

- Git
- Python 3.10+
- Node.js 18+ and npm
- Databricks SQL warehouse credentials
- NVIDIA NIM API key

## 2) Clone the repo

```bash
git clone <YOUR_REPO_URL>
cd hofbuildathon2026
```

## 3) Backend setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 4) Frontend setup

```bash
cd frontend
npm install
cd ..
npm run dev
```

## 5) Configure environment variables

Create `.env` in the project root:

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

# Legacy flag (optional)
USE_COMP_STUB=true
```

Optional frontend env file (`frontend/.env`):

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## 6) Run the app

Start backend (terminal 1):

```bash
source .venv/bin/activate
python -m uvicorn app.main:app --reload --env-file .env --log-level debug
```

Start frontend (terminal 2):

```bash
cd frontend
npm run dev
```

URLs:
- Frontend: `http://127.0.0.1:8080` (or Vite-provided port)
- Backend: `http://127.0.0.1:8000`
- Backend docs: `http://127.0.0.1:8000/docs`

## 7) Quick manual test

1. Open frontend at `/submit`
2. Upload a PDF
3. Set priorities
4. Click **Analyze Offer**
5. Confirm results page shows:
   - recommendation,
   - score bars,
   - market snapshot chart,
   - Nemotron chat responses

## 8) API test (curl)

Upload + create records:

```bash
curl -X POST "http://127.0.0.1:8000/offers/ingest-pdf?create_records=true" \
  -H "X-User-Id: 42" \
  -F "file=@/absolute/path/to/offer.pdf" \
  -F "priority_financial=4" \
  -F "priority_career=3" \
  -F "priority_lifestyle=3" \
  -F "priority_alignment=3"
```

Evaluate:

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

## 9) Troubleshooting

- `Offer not found`
  - Re-run upload/analyze to generate a fresh `offer_id`.
- `LLM_AUTH_FAILED`
  - Check `NIM_API_KEY`, restart backend.
- Databricks connected but bad/empty market values
  - Verify `MARKET_DATA_TABLE` and column data.
- UI not updating
  - Hard refresh browser (`Cmd+Shift+R`).
