# Twitter Analysis Platform Architecture

## Goals
- Keep the existing Python analysis engine intact.
- Replace the Streamlit UI with a modern React frontend.
- Introduce a small FastAPI layer for orchestration and future expansion.
- Avoid breaking the current scraper and model code.

## Current Direction
- `backend/` remains the source of truth for scraping and analysis logic.
- `backend/api/` becomes the HTTP boundary.
- `frontend/` becomes the new frontend application.
- The Streamlit app is treated as legacy and not used for the new UI.

## Proposed Flow
1. React UI collects channels and runtime settings.
2. React sends one request to FastAPI.
3. FastAPI calls existing scraping and analysis modules.
4. FastAPI returns a structured response for rendering.

## Working Rules
- Do not move business logic into React.
- Do not duplicate scraping code in the frontend.
- Keep the API contract stable and typed.
- Keep UI components presentational where possible.

## Initial API Surface
- `GET /health`
- `POST /api/analysis`

## Next Steps
- Add stricter schemas and validation.
- Split the React app into reusable components.
- Introduce background jobs only if runtime becomes too slow for a single request.
