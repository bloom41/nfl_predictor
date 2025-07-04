# ⚙️ DevOps & CI/CD Guidelines

Deployment and environment standards.

---

## 🐳 Docker

- One `Dockerfile` per service.
- Use multi-stage builds: install, build, and runtime stages.
- Expose ports 3000, 3001, 5000.

---

## 🔧 docker-compose.yml

Services:
- `frontend` → React build served by Nginx.
- `backend` → Node.js API.
- `ml` → Python Flask.
- `db` → Postgres.
- `redis` → Caching.

---

## 🌐 Environment Files

- `.env.development`, `.env.test`, `.env.production`
- Do not commit `.env*` to repo.

---

## 🚀 CI/CD

- GitHub Actions workflows:
  - `ci.yml`: lint, test, build Docker images.
  - `deploy.yml`: push to registry, deploy to Kubernetes or cloud.

---

## 🔄 Rollbacks

- Use image tags tied to Git SHAs.
- Keep last 3 releases for quick rollback.

_Last updated: July 2025 • Author: Hogan_