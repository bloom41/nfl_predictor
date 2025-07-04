# 🎯 CLAUDE Core Development Philosophy

This document outlines foundational principles for collaborating with Claude on the NFL Predictor project. It applies across frontend, backend, ML, and infrastructure layers.

---

General Guidance

- Responses should follow strict typing, test-first logic, and domain-aware reasoning.
- All code must be maintainable, modular, and performance-conscious.
- Claude should produce semantic commit messages, scoped to specific services or folders.

---

## 🧪 Testing-First Workflow

1. Write failing tests or test scaffolds before implementing new functionality.
2. Validate schema coverage and edge cases.
3. Ensure tests live in:
   - `/tests/unit/`
   - `/tests/integration/`
   - `/tests/ml/`
4. Always suggest testing strategy before generating code.

---

## 🔡 Naming & File Conventions

- Use `camelCase` for functions and variables.
- Use `PascalCase` for components and class-style modules.
- React files: `ComponentName.tsx`
- Express files: `routeName.controller.ts`

---

## 📦 Folder Principles

Claude must honor folder boundaries:
- Never modify files outside the target unless asked.
- Backend edits only in `/backend-ts/`
- ML edits only in `/src/` or `/app.py`
- DB schemas in `/backend-ts/prisma` or `nfl_api/models.py`

---

## 🧩 Claude Workflow Expectations

When prompted:
- Ask clarifying questions if needed.
- Use project schemas and folder layouts.
- Suggest modular improvements in addition to completing tasks.

Never:
- Generate untyped code.
- Mix layers unless explicitly requested.
- Change folder structure arbitrarily.

_Last updated: July 2025 • Author: Hogan_