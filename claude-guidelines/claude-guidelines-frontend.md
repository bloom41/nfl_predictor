# 🖥️ Frontend (React TypeScript) Guidelines

Guidance for building UI components, pages, and services in `/frontend/client/`.

---

## 🏗️ Project Structure

- `/frontend/client/src/pages/` → top-level routes and page components.
- `/components/` → reusable UI pieces.
- `/services/` → API hooks and utilities.

---

## 💡 Component Patterns

- Use functional components with hooks.
- Keep components small: max 2 levels of nesting.
- Use TanStack Query (`useQuery`, `useMutation`) for data fetching.
- Provide loading/error states with Suspense and error boundaries.

---

## 🎨 Styling & Theming

- Use Material-UI v6 theming system.
- Define color and typography tokens in a central theme file.
- Avoid inline styles; prefer `sx` prop or `styled()`.

---

## 🔄 State & Effects

- Favor local state where possible; global state only for cross-component needs.
- Use `useEffect` cleanups to avoid memory leaks.
- Debounce input where network calls are frequent.

---

## 🔬 Testing Components

- Use React Testing Library.
- Test user interactions and visible outcomes.
- Mock API with MSW for isolation.
- Aim for behavior-driven tests, not implementation details.

_Last updated: July 2025 • Author: Hogan_