# Sub-Zero

Subscription management and optimization platform. Connect your Gmail to automatically find subscriptions and get smart recommendations to save money.

## Features

- **Auto-Discovery**: Scans Gmail for receipts and invoices to find subscriptions
- **Smart Recommendations**: Rule-based engine suggests which subscriptions to cancel or review
- **Action Feed**: Easy-to-use dashboard for acting on recommendations
- **Privacy First**: Read-only Gmail access, encrypted tokens, no data sharing

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI + Python 3.11 |
| Database | PostgreSQL (Supabase) |
| Frontend | Next.js 14 + Tailwind CSS |
| Auth | Google OAuth 2.0 |

## Project Structure

```
sub-zero/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI entry point
│   │   ├── config.py         # Environment configuration
│   │   ├── database.py       # Database connection
│   │   ├── models/           # Pydantic schemas
│   │   ├── routers/          # API endpoints
│   │   ├── services/         # Business logic
│   │   └── utils/            # Utilities
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/              # Next.js pages
│   │   ├── components/       # React components
│   │   └── lib/              # API client
│   └── package.json
└── database/
    └── schema.sql            # PostgreSQL schema
```

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- Supabase account
- Google Cloud Console project

### 1. Supabase Setup

1. Go to [supabase.com](https://supabase.com) and create a new project
2. Run the SQL in `database/schema.sql` in the SQL Editor
3. Copy your project URL and API keys from Settings → API

### 2. Google Cloud Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project
3. Enable Gmail API (APIs & Services → Library → Gmail API)
4. Configure OAuth consent screen:
   - User Type: External
   - Add scopes: `gmail.readonly`, `userinfo.email`, `userinfo.profile`
5. Create OAuth credentials:
   - Application type: Web application
   - Redirect URI: `http://localhost:8000/auth/google/callback`
6. Copy Client ID and Client Secret

### 3. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your credentials

# Generate encryption key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Add this to ENCRYPTION_KEY in .env

# Run the server
uvicorn app.main:app --reload
```

### 4. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Create .env.local file
cp .env.local.example .env.local
# Edit with your API URL

# Run development server
npm run dev
```

### 5. Access the Application

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Environment Variables

### Backend (.env)

```env
DATABASE_URL=postgresql://postgres:password@db.xxx.supabase.co:5432/postgres
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=your_anon_key
SUPABASE_SERVICE_KEY=your_service_key
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
ENCRYPTION_KEY=your_fernet_key
JWT_SECRET=your_jwt_secret
FRONTEND_URL=http://localhost:3000
BACKEND_URL=http://localhost:8000
```

### Frontend (.env.local)

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## API Endpoints

### Authentication
- `GET /auth/google/login` - Redirect to Google OAuth
- `GET /auth/google/callback` - Handle OAuth callback
- `POST /auth/logout` - Clear session
- `GET /auth/me` - Get current user

### Subscriptions
- `GET /subscriptions` - List subscriptions
- `POST /subscriptions/sync` - Sync from Gmail
- `POST /subscriptions` - Add manual subscription
- `PATCH /subscriptions/{id}` - Update subscription
- `DELETE /subscriptions/{id}` - Delete subscription

### Decisions
- `GET /decisions` - List pending decisions
- `POST /decisions/generate` - Generate recommendations
- `POST /decisions/{id}/act` - Act on decision
- `GET /decisions/summary/stats` - Get statistics

## Decision Engine Rules

1. **CANCEL**: No emails from vendor in 90+ days
2. **REVIEW**: Cost >$20/month with low activity
3. **REMIND**: Renewal within 7 days
4. **KEEP**: Active usage detected

## Deployment

### Backend (Railway)

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway init
railway up
```

### Frontend (Vercel)

```bash
# Install Vercel CLI
npm install -g vercel

# Deploy
cd frontend
vercel
```

Remember to update:
- `FRONTEND_URL` in backend to production URL
- `NEXT_PUBLIC_API_URL` in frontend to production API URL
- Google OAuth redirect URI to production callback URL

## License

MIT
