# 🔍 Testing Standards

Unified testing practices across all layers.

---

## 🧪 Frameworks

- **Frontend**: Jest + React Testing Library + MSW
- **Backend**: Jest/Vitest + Supertest for API
- **ML**: Pytest + pytest-mocker for Flask endpoints

---

## 📁 Folder Structure

- `/tests/unit/` → pure function tests.
- `/tests/integration/` → DB and service integration.
- `/tests/ml/` → prediction pipeline tests.

---

## ✅ Coverage Targets

- 100% behavior coverage for critical paths.
- Report uncovered lines in CI; fail build if < 95%.

---

## 🔄 CI Integration

- Run tests in parallel where possible.
- Seed test DBs before integration tests.
- Clean up test artifacts after each run.

_Last updated: July 2025 • Author: Hogan_