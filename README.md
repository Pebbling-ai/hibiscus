# Hibiscus Agent Registry

Hibiscus is a federated agent registry platform with two main components:

1. **Frontend**: A Next.js application with Clerk authentication for user management
2. **Backend**: A FastAPI application that communicates with Supabase for data storage

This platform enables:
- Registration and discovery of AI agents
- User authentication via Clerk
- Personal access token generation for API access
- Federation with other agent registries

## Project Structure

```
hibiscus/
├── frontend/         # Next.js application
├── backend/          # FastAPI application
└── docker-compose.yml
```

## Features

- **Agent Registration**: Submit new agents to the registry
- **Agent Discovery**: Search and browse available agents
- **Agent Details**: View comprehensive information about each agent
- **Authentication**: User login and signup via Clerk
- **API Access**: Generate and manage Personal Access Tokens
- **Federation**: Connect with other agent registries to discover their agents

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Node.js 16+ (for local frontend development)
- Python 3.9+ (for local backend development)
- uv (for Python package management)

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/hibiscus.git
   cd hibiscus
   ```

2. Create environment files:
   ```bash
   # Backend
   cp backend/.env.example backend/.env
   # Frontend
   cp frontend/.env.example frontend/.env
   ```

3. Configure environment variables:
   - Set up Supabase credentials in `backend/.env`
   - Add Clerk authentication keys in `frontend/.env`

4. Start the application with Docker:
   ```bash
   docker-compose up
   ```

5. The application will be available at:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

## Development

### Frontend (Next.js)

To run the frontend locally:

```bash
cd frontend
npm install
npm run dev
```

### Backend (FastAPI)

To run the backend locally:

```bash
cd backend
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .
uvicorn main:app --reload
```

## API Documentation

When the backend is running, API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Federation

Hibiscus supports federation with other agent registries:

1. Add a new federated registry through the admin interface
2. Agents from the federated registry will appear in your search results
3. The registry will maintain reference to the original source

## Docker Compose

The included Docker Compose configuration sets up:
- Frontend container
- Backend container
- No database (uses remote Supabase)

## License

[MIT License](LICENSE)
