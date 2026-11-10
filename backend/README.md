# SEAS Backend

## Run
1. `cd backend`
2. `python -m venv venv`
3. Windows: `venv\Scripts\activate`
4. Linux/macOS: `source venv/bin/activate`
5. `pip install -r requirements.txt`
6. Copy `.env.example` to `.env` and change `JWT_SECRET_KEY` for non-demo use.
7. `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`

API docs: `http://127.0.0.1:8000/docs`

Default development administrator:
- username: `admin`
- password: `admin123`

For another machine on the same network, set the frontend `window.SEAS_API_BASE_URL` to `http://SERVER_IP:8000/api` and set `CORS_ORIGINS` to the frontend origin.

The SQLite database is `seas.db` in the backend working directory. Do not expose or commit `.env` or `seas.db`.
