# BillChill — Next.js + Flask

This repo contains:
- A Next.js 16 frontend (React 19) under `app/`
- A unified Flask backend under `app/backend/server.py` for both hospitals search and dispute analysis

Key backend entrypoints:
- Hospitals API: [`hospitals_bp` → `hospitals`](app/backend/server.py)
- Dispute API: [`dispute_bp` → `analyze`](app/backend/server.py) and [`dispute_home`](app/backend/server.py)

## Environment Variables

Frontend (`.env.local`):
```ini
NEXT_PUBLIC_BACKEND_URL=http://127.0.0.1:5000
```

Backend (shell env or `.env` at repo root, auto-loaded):
```bash
# Required for hospitals search (OpenRouter Sonar)
export OPENROUTER_API_KEY=sk-...

# Required for AI analysis and letter drafting (OpenAI)
export OPENAI_API_KEY=sk-...

# Recommended for Nominatim (reverse/forward geocoding)
export NOMINATIM_EMAIL=you@example.com

# Frontend origin allowed by CORS
export CORS_ALLOW_ORIGIN=http://localhost:3000
```

Windows PowerShell:
```powershell
$env:OPENROUTER_API_KEY="sk-..."; `
$env:OPENAI_API_KEY="sk-..."; `
$env:NOMINATIM_EMAIL="you@example.com"; `
$env:CORS_ALLOW_ORIGIN="http://localhost:3000"
```

## Install

Frontend:
```bash
npm install
```

Backend (use a venv if desired):
```bash
python -m venv .venv
# PowerShell: .venv\Scripts\Activate.ps1
source .venv/bin/activate
pip install -r app/backend/requirements.txt
```

## Run

Frontend (VS Code terminal 1):
```bash
npm run dev
```

Backend (VS Code terminal 2):
```bash
python app/backend/server.py
```

Visit:
- Hospitals finder: http://localhost:3000/hospital
- Dispute flow: http://localhost:3000/dispute

## Flow Overview

1. User interacts with the frontend.
2. Frontend calls the Flask backend at `NEXT_PUBLIC_BACKEND_URL`.
3. Hospitals search posts to `/api/hospitals`.
4. Dispute analysis uploads PDFs to `/api/dispute/analyze`.
5. Backend returns structured JSON used by the UI in [app/hospital/page.tsx](app/hospital/page.tsx) and [app/dispute/page.tsx](app/dispute/page.tsx).

## API Reference

Health
- GET `/health` → `{ ok: true }`

Hospitals (Nearby price estimates)
- POST `/api/hospitals`
  - Body (JSON): `{ lat: number, lon: number, condition: string }`
  - Response: `{ results: HospitalResult[] }`
  - Implementation: [`hospitals`](app/backend/server.py)
  - Notes:
    - Uses OpenRouter Perplexity Sonar for web search.
    - Reverse/forward geocoding via Nominatim.
    - Results filtered to ≈30–37 miles and sorted by price then distance.
  - Frontend consumer: [app/hospital/page.tsx](app/hospital/page.tsx)

Dispute (Analyze bill + draft letter)
- GET `/api/dispute` → `{ status: "ok", providers: string[] }`
  - Implementation: [`dispute_home`](app/backend/server.py)
- POST `/api/dispute/analyze` (multipart/form-data)
  - Fields:
    - bill_pdf: PDF (required)
    - rules_pdf: PDF (optional if provider chosen)
    - provider: one of `United | Providence | Molina | CMS` (optional)
    - patient_name: string (optional, default "John Doe")
    - household_size: number (optional, default 1)
    - annual_income: number (optional, default 0)
    - zip_code: string (optional)
  - Response:
    ```json
    {
      "providers": ["United","Providence","Molina","CMS"],
      "ai_result": "string (legacy combined text)",
      "ai_structured": {
        "state_abbr": "CA",
        "total_eligible_discount_percent": 45,
        "discount_explanation": "string",
        "overcharges": [
          { "line_number": "12", "service": "MRI", "amount": 1234.56, "reason": "string" }
        ]
      },
      "dispute_letter": "string (may be empty if no overcharges)"
    }
    ```
  - Implementation:
    - Structured analysis: [`ai_check_overcharges_and_discount`](app/backend/server.py)
    - Letter drafting: [`draft_dispute_letter`](app/backend/server.py)
    - Legacy text builder and safety checks handled in [`analyze`](app/backend/server.py)
  - Frontend consumer: [app/dispute/page.tsx](app/dispute/page.tsx)

## Files & Folders

- Backend service: [app/backend/server.py](app/backend/server.py)
- Backend deps: [app/backend/requirements.txt](app/backend/requirements.txt)
- Provider policy PDFs: `app/dispute/policy_docs/`
  - Mapped in [`PROVIDER_RULES`](app/backend/server.py)
- Uploads folder (auto-created): `app/dispute/uploads/`

## Notes

- PDF text extraction uses `pdfplumber` via [`extract_text_from_pdf`](app/backend/server.py).
- The dispute endpoint returns both a legacy summary (`ai_result`) and a structured payload (`ai_structured`) for robust UI parsing.
- The letter is only generated when overcharges are found, see [`overcharges_found`](app/backend/server.py).

## Troubleshooting

- CORS: ensure `CORS_ALLOW_ORIGIN` matches your frontend origin exactly.
- Keys:
  - Hospitals search requires `OPENROUTER_API_KEY`.
  - Dispute analysis requires `OPENAI_API_KEY`.
- Geolocation denied (hospitals page): browser will show an error; allow location and retry.
- Health check: `GET ${NEXT_PUBLIC_BACKEND_URL}/health`.

## Tech

- Next.js 16, React 19
- Flask 3, `flask-cors`
- OpenRouter (Perplexity Sonar) for hospital discovery
- OpenAI (`gpt-4.1-mini`) for dispute analysis and letters