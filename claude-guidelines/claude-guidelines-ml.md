# 🤖 ML Service (Flask Python) Guidelines

Standards for the prediction engine in `/app.py` and `/src/`.

---

## 🔬 Endpoint Contract

- Single POST endpoint: `/predict`
- Request body validated by Pydantic schema.
- Response:
  ```json
  {
    "predictions": [...],
    "confidence": number,
    "timestamp": "ISO8601"
  }
  ```

---

## 🧩 Pipeline Steps

- **Input Validation**: Pydantic models.
- **Feature Engineering**: Pure functions → DataFrame.
- **Model Ensemble**: Load pickled models, aggregate.
- **Scoring**: Compute confidence intervals.
- **Fallback**: Catch DB or model load errors → return default predictions.

---

## 📦 Folder Layout

- `/src/schemas/` → Pydantic models.
- `/src/features/` → data processing functions.
- `/src/models/` → serialized model loaders.
- `/tests/ml/` → prediction unit tests.

---

## 🚀 Performance

- Cache heavy computations in Redis.
- Batch requests when possible.
- Serve with Gunicorn and Uvicorn workers.

_Last updated: July 2025 • Author: Hogan_