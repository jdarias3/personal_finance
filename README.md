# Clarity - Personal Finance Operating System

An AI-powered personal finance web application designed as a calm, trustworthy financial operating system. Built with a focus on financial clarity, emotional safety, deterministic financial correctness, and explainable AI insights.

## Features

- **Financial Ledger** - Track accounts, transactions, and categories with immutable records
- **Debt Engine** - Snowball and avalanche debt payoff simulations with projections
- **Forecasting** - Cash flow prediction, safe-to-spend calculations, upcoming bill detection
- **Insights** - AI-powered spending analysis and anomaly detection
- **Onboarding** - Profile modes for different financial goals

## Tech Stack

- **Backend**: Python 3.12, FastAPI, async SQLAlchemy 2.0, Pydantic v2
- **Frontend**: Server-rendered HTML with HTMX and Alpine.js
- **Database**: PostgreSQL 15
- **Architecture**: Modular monolith with domain-driven boundaries

## Prerequisites

- Python 3.12+ (for local development)
- Docker & Docker Compose (for containerized development)
- PostgreSQL 15+ (for local development without Docker)

---

## Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone <your-repo-url>
cd personal_finance

# Start the application
docker-compose -f docker/docker-compose.yml up
```

The app will be available at `http://localhost:8000`

### Option 2: Local Development

#### 1. Install Dependencies

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with pip
pip install uv

# Install project dependencies
uv sync
```

#### 2. Set Up Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your database connection
# DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/personal_finance
```

#### 3. Set Up Database

```bash
# Run migrations
uv run alembic upgrade head
```

#### 4. Run the Application

```bash
# Start the development server
uv run uvicorn src.api.main:app --reload
```

Open `http://localhost:8000` in your browser.

### Option 3: Frontend Only (No Backend)

This serves static HTML files without the Python backend. Forms and dynamic features won't work.

```bash
cd src/frontend
python3 -m http.server 8080
```

Open `http://localhost:8080` to view the static templates.

---

## Development

### Installing Additional Dependencies

```bash
# Add a new dependency
uv add <package-name>

# Add a dev dependency
uv add --dev <package-name>
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=html

# Run specific test file
uv run pytest tests/test_services.py
```

### Code Quality

```bash
# Lint code
uv run ruff check .

# Fix auto-fixable issues
uv run ruff check --fix .

# Type check
uv run mypy src

# Run all checks
uv run ruff check . && uv run mypy src
```

### Database Migrations

```bash
# Create a new migration
uv run alembic revision --autogenerate -m "description"

# Apply migrations
uv run alembic upgrade head

# Rollback one migration
uv run alembic downgrade -1

# Show current migration
uv run alembic current
```

---

## Project Structure

```
personal_finance/
├── src/
│   ├── api/               # FastAPI routes and endpoints
│   │   ├── main.py       # Application entry point
│   │   ├── auth.py       # Authentication routes
│   │   ├── pages.py      # Page routes (dashboard, accounts, transactions)
│   │   ├── pages_debts.py # Debt and forecasting routes
│   │   └── templates.py  # Jinja2 template helpers
│   ├── domain/
│   │   └── models.py     # SQLAlchemy models
│   ├── services/         # Business logic layer
│   │   ├── financial_ledger.py  # Account and transaction services
│   │   ├── debt_engine.py        # Debt calculations and projections
│   │   ├── forecasting.py        # Cash flow projections
│   │   └── insights.py          # AI insights and analysis
│   ├── infrastructure/
│   │   └── database.py  # Database configuration
│   └── frontend/
│       ├── templates/   # Jinja2 HTML templates
│       │   ├── accounts/
│       │   ├── debts/
│       │   ├── forecasting/
│       │   ├── transactions/
│       │   ├── onboarding/
│       │   ├── partials/
│       │   ├── base.html
│       │   ├── dashboard.html
│       │   └── index.html
│       └── static/
│           ├── css/styles.css
│           └── js/
├── alembic/
│   ├── versions/         # Database migrations
│   ├── env.py
│   └── script.py.mako
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── tests/
│   ├── test_api.py
│   └── test_services.py
├── .env.example
├── .gitignore
├── pyproject.toml
├── alembic.ini
└── README.md
```

---

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Landing page |
| POST | `/auth/register` | Create account |
| POST | `/auth/login` | Sign in |
| POST | `/auth/logout` | Sign out |

### Dashboard & Pages
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/dashboard` | Main dashboard |
| GET | `/accounts` | List accounts |
| GET | `/accounts/new` | Add account form |
| GET | `/transactions` | List transactions |
| GET | `/transactions/new` | Add transaction form |
| GET | `/debts` | Debt overview |
| GET | `/forecast` | Cash flow forecast |
| GET | `/onboarding` | Setup wizard |

### API Features
- Full CRUD for accounts, transactions, categories
- Debt payoff simulations (snowball/avalanche)
- Cash flow projections
- CSV import for transactions
- Transaction reversal via compensating entries

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/personal_finance` | PostgreSQL connection string |
| `SECRET_KEY` | `dev-secret-change-in-production` | JWT signing key |
| `ENVIRONMENT` | `development` | Runtime environment |

---

## Architecture Principles

1. **Deterministic Financial Core** - All money calculations use integer cents, never floats
2. **Immutable Ledger** - Transactions are never deleted, only reversed with compensating entries
3. **AI as Interpretation** - AI explains data but never mutates financial records
4. **Modular Monolith** - Domain-driven modules with explicit service boundaries
5. **Async-First** - Full async/await for I/O operations

---

## Design Philosophy

The UI is designed to feel:
- **Calm** - No aggressive gamification or stressful alerts
- **Trustworthy** - Transparent about how calculations work
- **Clear** - Simple language over accounting jargon
- **Actionable** - Focus on next steps, not overwhelming data

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

MIT License - See LICENSE file for details

---

## Support

For issues and feature requests, please open a GitHub issue.