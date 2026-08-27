# Frontend (React + Vite + Tailwind)

Doctor-facing web UI for the medical record system.

## Layout

| Path | Purpose |
|------|---------|
| `src/pages/` | Route-level views (Login, Dashboard, Patients, Upload, Search) |
| `src/components/` | Reusable UI (Navbar, RecordCard, SearchBar, etc.) |
| `src/services/` | API client wrappers for backend endpoints |
| `src/hooks/` | Custom React hooks (auth, fetch) |

## Setup (when implementing)

Initialize with Vite + React in this folder, then add Tailwind CSS. Point API calls to the FastAPI backend (default `http://127.0.0.1:8000`).

## Planned pages

- Login
- Dashboard
- Patient list / detail
- Upload medical record
- Semantic search + AI summary
- Record verification status
