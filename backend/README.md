# Hibiscus Backend

This is the backend component of the Hibiscus Agent Registry, a federated platform for registering and discovering AI agents.

## Features

- **Agent Management**: Register, update, and list AI agents
- **Authentication**: Secure API key authentication
- **Federation**: Connect with other agent registries
- **Supabase Integration**: Data storage with Supabase

## Project Structure

The backend follows a modular Python package structure:

```
backend/
├── app/                    # Main application package
│   ├── api/                # API layer
│   │   ├── routes/         # API route handlers
│   │   │   ├── agents.py   # Agent endpoints
│   │   │   ├── federated_registries.py  # Federation endpoints
│   │   │   └── tokens.py   # User token endpoints
│   ├── core/               # Core application components
│   │   └── auth.py         # Authentication functionality
│   ├── db/                 # Database access layer
│   │   ├── client.py       # Database client implementation
│   │   └── schema.py       # Database schema definitions
│   ├── models/             # Data models
│   │   └── schemas.py      # Pydantic schemas
│   ├── services/           # Business logic services
│   │   └── federation.py   # Federation client implementation
│   ├── utils/              # Utility functions
│   └── main.py             # FastAPI application entry point
├── scripts/                # Utility scripts
│   └── init_db.py          # Database initialization script
└── run.py                  # Server runner script
```

## Getting Started

### Prerequisites

- Python 3.9+
- uv (Python package manager)
- Supabase account (or use the included mock database for development)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/hibiscus.git
   cd hibiscus/backend
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   uv pip install -e .
   ```

3. Set up environment variables:
   ```bash
   cp .env.example .env
   # Then edit .env with your Supabase credentials
   ```

### Running the Server

```bash
python run.py
```

The API will be available at http://localhost:8000

## API Documentation

When the server is running, you can access the API documentation at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

### Agents

- `GET /agents` - List all agents
- `GET /agents/{agent_id}` - Get a specific agent
- `POST /agents` - Create a new agent (requires authentication)

### Federation

- `GET /federated-registries` - List all federated registries
- `POST /federated-registries` - Add a new federated registry

### Authentication

- `POST /user/tokens` - Create a new API token
- `GET /user/tokens` - List all API tokens
- `DELETE /user/tokens/{token_id}` - Delete an API token
- `GET /user/profile` - Get the profile of the authenticated user

## Database Schema

The application uses Supabase with the following tables:

- `users` - User information
- `agents` - Agent information
- `api_keys` - API keys for authentication
- `federated_registries` - Connected federated registries

## Development

For local development without Supabase, the application includes a mock database in `app/db/client.py`.

### Initializing the Supabase Database

To initialize the Supabase database with the required schema:

```bash
python scripts/init_db.py
```

### Adding New Routes

To add new functionality:

1. Create a new route module in `app/api/routes/`
2. Define your endpoints using FastAPI router
3. Include the router in `app/main.py`

## Federation Protocol

The federation protocol allows connecting multiple Hibiscus instances:

1. Register a remote registry via the `/federated-registries` endpoint
2. Federated agents appear in search results with proper attribution
3. When viewing a federated agent, the request is proxied to the source registry

## Testing with curl

Test the API with curl:

```bash
# List all agents
curl http://localhost:8000/agents

# Create an API token (requires authentication)
curl -X POST http://localhost:8000/user/tokens \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"name": "My API Token"}'

# Create a new agent
curl -X POST http://localhost:8000/agents \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"name": "My Agent", "description": "My AI assistant", "category": "assistant", "capabilities": ["text", "search"]}'
```
