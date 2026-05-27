# Trivz Backend

A multiplayer trivia game backend built with FastAPI and SQLAlchemy.

## Features

- User authentication with JWT tokens and refresh tokens
- Room-based multiplayer sessions
- Real-time communication via WebSockets
- Integration with Open Trivia Database API
- Invite/request system for room participation

## Prerequisites

- Python 3.13+
- `uv` package manager (recommended) or pip

## Setup

1. Clone the repository:
```bash
git clone <repo-url>
cd trivz_backend
```

2. Create a `.env` file in the root directory:
```env
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
TTL=30
DATABASE_URL=sqlite:///./trivz.db
```

3. Install dependencies:
```bash
uv sync
```
Or with pip:
```bash
pip install -e .
```

4. Run the application:
```bash
uv run python src/main.py
```
Or:
```bash
cd src && uvicorn main:app --reload
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
src/
├── main.py              # FastAPI application entry point
├── config.py            # Environment configuration
├── database.py          # SQLAlchemy setup
├── models.py            # Database models
├── routers/             # API route handlers
│   ├── auth.py         # Authentication endpoints
│   ├── room.py         # Room management
│   ├── session.py      # Game sessions
│   └── ws.py           # WebSocket endpoint
├── services/            # Business logic
│   ├── auth.py         # JWT & password handling
│   ├── db.py           # Database dependencies
│   ├── room.py         # Room code generation
│   ├── trivia.py       # Open Trivia DB client
│   └── ws.py           # WebSocket auth
├── schemas/             # Pydantic models
│   ├── user.py
│   ├── room.py
│   └── session.py
└── ws/
    └── manager.py       # WebSocket connection manager
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | JWT secret key (required) | - |
| `ALGORITHM` | JWT algorithm | HS256 |
| `TTL` | Access token expiry (minutes) | 30 |
| `DATABASE_URL` | Database connection string | sqlite:///./trivz.db |

## WebSocket Authentication

Pass the access token as a query parameter when connecting:
```
ws://localhost:8000/ws/{room_code}?token={access_token}
```
