# Backend (FastAPI)

Configuration and project structure only — business logic not implemented yet.

## Structure

```
backend/
├── requirements.txt
└── app/
    ├── main.py          # FastAPI app, CORS, router registration
    ├── config.py        # Environment settings (Pydantic)
    ├── database.py      # SQLAlchemy engine, session, Base
    ├── routers/         # API route modules (empty routers)
    ├── models/          # SQLAlchemy ORM models (to be added)
    ├── schemas/         # Pydantic request/response schemas (to be added)
    └── services/        # Business logic (to be added)
```

## Run (after installing dependencies)

From the `backend/` directory:

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Health check: `GET http://127.0.0.1:8000/health`

Copy `.env.example` from the project root to `.env` and adjust values as needed.
