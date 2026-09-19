# Hateco Chatbot Console

A multi-page Facebook Messenger chatbot with a web console for managing pages,
per-page knowledge and instructions, conversation history, and a human-reviewed
learning loop.

## Layout

- `backend/` — FastAPI app, SQLite database, FAISS indexes, pytest suite
- `frontend/` — React + Vite admin console
- `data/` — legacy knowledge text files, used once by the seed script

## Setup

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # .venv/bin/python on macOS/Linux
cp .env.example .env
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# paste that value into TOKEN_ENCRYPTION_KEY in .env, then set SECRET_KEY and OPENROUTER_API_KEY
```

## Run the backend

```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

## Run the frontend

```bash
cd frontend
npm install
npm run dev
```

Console: http://localhost:5173

## First run

Open the console and create the first admin account — the login screen offers it
while no user exists. Then add a page with its Facebook Page ID and Page Access
Token.

To import the legacy `data/*.txt` knowledge into a page:

```bash
cd backend
python -m scripts.seed_from_legacy --fb-page-id 1234567890 --name "Hateco Tuyen Sinh" \
  --access-token EAAG... --admin-email you@hateco.vn --admin-password your-password
```

## Facebook webhook

Point the Facebook App webhook at `https://<your-host>/webhook` and use the
`VERIFY_TOKEN` from `.env`. One webhook serves every page: events are routed by the
Facebook Page ID in the payload.

## Tests

```bash
cd backend && python -m pytest       # backend
cd frontend && npm test -- --run     # frontend
```
