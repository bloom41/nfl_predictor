# 🚀 Backend (Express TypeScript) Guidelines

Standards for building and maintaining the API in `/backend-ts/`.

---

## 📁 Folder Layout

- `/features/` → individual feature modules (controllers, services).
- `/services/` → core utilities (database, cache, ML bridge).
- `/shared/` → types, middleware, validation schemas.

---

## 🔄 Request Flow

1. **Route** → validate input with Zod schemas.
2. **Controller** → orchestrate business logic.
3. **Service** → handle data operations and external calls.
4. **Response** → return typed DTOs.

---

## 🛡️ Security & Validation

- Use Helmet.js for security headers.
- Validate all inputs with Zod before processing.
- Rate limit endpoints based on usage patterns.
- JWT authentication where required.

---

## 📊 Performance

- Cache frequently requested data in Redis.
- Use Prisma connection pooling.
- Implement request/response compression.
- Monitor response times with middleware.

---

## 🔬 Testing APIs

- Use Supertest for integration tests.
- Mock external services (ML, external APIs).
- Test error conditions and edge cases.
- Validate response schemas match TypeScript types.

_Last updated: July 2025 • Author: Hogan_