# Supplytics — Supply Chain Resilience Agent

> **Runs 100% locally** — no Google Cloud SDK, no GCP credentials required for local development.

---

## ⚡ Quick Start (Local — No Cloud Needed)

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
python app.py
```

The server starts at **http://127.0.0.1:5000**.  
Health check: `GET http://localhost:5000/api/health`

By default the backend uses **in-memory simulators** for both the database (Firestore) and the AI (Vertex AI/Gemini).  
No authentication or GCP account is needed.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** in your browser.

---

## 🔑 Optional: Live Gemini AI Responses

For real Gemini AI responses (instead of deterministic simulator templates):

1. Get a free API key at https://aistudio.google.com/app/apikey
2. Copy `.env.example` to `.env` inside the `backend/` folder:
   ```bash
   cp backend/.env.example backend/.env
   ```
3. Set your key:
   ```env
   GEMINI_API_KEY=your_actual_key_here
   ```
4. Restart `python app.py`

The `/api/health` endpoint reports `"gemini_live": true` when the key is active.

---

## ⚙️ Environment Variables (`backend/.env`)

| Variable | Default | Description |
|---|---|---|
| `GEMINI_API_KEY` | *(empty)* | Optional Gemini REST API key for live responses |
| `USE_LOCAL_STORAGE` | `true` | Use in-memory store instead of Firestore |
| `PORT` | `5000` | Flask server port |
| `USE_REAL_FIRESTORE` | `false` | Set `true` only with active GCP credentials |
| `USE_REAL_VERTEX` | `false` | Set `true` only with active GCP credentials |

See [`backend/.env.example`](backend/.env.example) for the full reference.

---

## ☁️ Advanced: Full GCP Deployment (Optional)

Only needed for production / cloud deployment with real Firestore and Vertex AI.

### Prerequisites
1. Install the [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
2. Authenticate:
   ```bash
   gcloud auth application-default login
   gcloud config set project YOUR_PROJECT_ID
   ```
3. In `backend/.env`, set:
   ```env
   USE_REAL_VERTEX=true
   USE_REAL_FIRESTORE=true
   GCP_PROJECT_ID=your-project-id
   FIRESTORE_DATABASE=your-db-name
   ```

---

## 🗂️ Project Structure

```
Supplytics/
├── backend/
│   ├── app.py              # Flask entry point
│   ├── config.py           # All config / env vars
│   ├── .env                # Local secrets (git-ignored)
│   ├── .env.example        # Template — copy to .env
│   ├── modules/            # Core AI pipeline (orchestrator, memory, agents…)
│   ├── routes/             # Flask API blueprints
│   ├── services/           # Firestore / Vertex / Gemini adapters + simulators
│   └── data/               # Seed data
└── frontend/               # React/Vite UI
```
