# SaaS App Folder Structure

This repository uses a monorepo layout for a Flask API + React frontend + PostgreSQL stack.

```text
saas-app/
├─ apps/                                # Application code (backend + frontend)
│  ├─ api/                              # Flask backend service
│  │  ├─ app/                           # Flask application package
│  │  │  ├─ api/                        # HTTP/API layer
│  │  │  │  └─ v1/                      # Versioned API namespace (/api/v1)
│  │  │  │     ├─ auth/                 # Authentication routes and controllers
│  │  │  │     ├─ users/                # User profile/account endpoints
│  │  │  │     ├─ dashboard/            # Dashboard and analytics endpoints
│  │  │  │     ├─ billing/              # Subscription and payment endpoints
│  │  │  │     └─ admin/                # Admin-only routes
│  │  │  ├─ core/                       # App factory, config bootstrap, constants
│  │  │  ├─ extensions/                 # SQLAlchemy/JWT/Migrate/CORS/Limiter init
│  │  │  ├─ models/                     # SQLAlchemy ORM models
│  │  │  ├─ schemas/                    # Marshmallow/Pydantic validation schemas
│  │  │  ├─ services/                   # Business logic/services
│  │  │  ├─ repositories/               # Data-access/query abstraction layer
│  │  │  ├─ security/                   # Auth helpers, password hashing, RBAC guards
│  │  │  ├─ middleware/                 # Request middleware and audit hooks
│  │  │  ├─ tasks/                      # Async/background jobs
│  │  │  ├─ utils/                      # Shared backend helper utilities
│  │  │  └─ errors/                     # Global error handling + API error formats
│  │  ├─ migrations/                    # Alembic migration scripts
│  │  ├─ tests/                         # Backend tests (unit/integration/API)
│  │  ├─ scripts/                       # Seeders and admin/dev scripts
│  │  ├─ requirements/                  # Python dependency groups (base/dev/prod)
│  │  ├─ manage.py                      # Flask CLI/management entrypoint
│  │  └─ wsgi.py                        # Production WSGI entrypoint (Gunicorn)
│  │
│  └─ web/                              # React frontend service
│     ├─ public/                        # Static assets served directly
│     ├─ src/                           # Frontend source code
│     │  ├─ app/                        # App bootstrap/providers/root setup
│     │  ├─ routes/                     # React Router routes and route guards
│     │  ├─ api/                        # Axios client and API modules
│     │  ├─ features/                   # Feature-based modules (auth, billing, etc.)
│     │  ├─ components/                 # Reusable UI components
│     │  ├─ layouts/                    # Layout shells (sidebar/topbar/auth)
│     │  ├─ pages/                      # Route-level page components
│     │  ├─ hooks/                      # Custom React hooks
│     │  ├─ context/                    # Global state providers/contexts
│     │  ├─ utils/                      # Frontend helpers and formatters
│     │  ├─ styles/                     # Tailwind/global style definitions
│     │  └─ assets/                     # Images/icons/fonts
│     ├─ tests/                         # Frontend tests
│     └─ tailwind/                      # Tailwind configuration and theme tokens
│
├─ infra/                               # Deployment and infrastructure artifacts
│  ├─ docker/                           # Dockerfiles and container configs
│  ├─ nginx/                            # Nginx reverse-proxy/static configs
│  ├─ postgres/                         # DB init scripts and local bootstrap SQL
│  └─ terraform/                        # Infrastructure-as-code (optional)
│
├─ .github/                             # GitHub Actions pipelines
│  └─ workflows/                        # CI/CD workflow definitions
├─ docs/                                # Architecture docs and runbooks
├─ scripts/                             # Repo-level automation scripts
├─ .env.example                         # Environment variable template
├─ docker-compose.yml                   # Local stack orchestration
└─ README.md                            # Project overview and quick-start
```
