# 🗄️ Database Layer Guidelines

Rules for dual-ORM strategy with PostgreSQL (primary) and SQLite (fallback).

---

## 📦 ORM Usage

- **Prisma** for Node.js (Express).
- **Django ORM** for Python (ML service and admin).

---

## 🔄 Migrations

- Store Prisma migrations under `/backend-ts/prisma/migrations/`.
- Store Django migrations under `nfl_api/migrations/`.
- Run migrations in CI step before tests.

---

## 📐 Schema Design

- Define entities: Player, Team, Game, Stats, Injuries, Transactions.
- Use UUIDs as primary keys.
- Name tables in snake_case; columns in snake_case.

---

## ⚙️ Dual-Database Flow

1. ML service tries PostgreSQL first.
2. On connection error or missing record, fall back to SQLite.
3. Log fallback events for monitoring.

---

## 🔍 Query Performance

- Add indexes on foreign keys and timestamp fields.
- Use `select_related`/`prefetch_related` in Django.
- Use Prisma's `include` sparingly for nested relations.

_Last updated: July 2025 • Author: Hogan_