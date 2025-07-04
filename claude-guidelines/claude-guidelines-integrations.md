# 🔗 Service Integrations

Contracts and communication flow between services.

---

## 🗺️ API Flow

1. **React → Express**  
   - Use TanStack Query to call endpoints:
     - `GET /rankings/top`
     - `POST /predict`
2. **Express → Flask**  
   - Proxy `POST /predict` to ML service.
   - Include JWT token in `Authorization` header.
3. **Flask → DB**  
   - Query via Django ORM.
   - Return JSON response to Express.
4. **Express → React**  
   - Normalize payloads into DTOs.

---

## 📐 Payload Schemas

- **PredictRequest**:
  ```json
  {
    "playerId": "uuid",
    "week": number,
    "context": { "..." }
  }
  ```

- **PredictResponse**:
  ```json
  {
    "predictions": "number[]",
    "confidence": "number"
  }
  ```

---

## 🔄 Mocking & Testing

- Use MSW in frontend to mock Express and ML endpoints.
- Use pytest fixtures to mock DB queries in ML service.

_Last updated: July 2025 • Author: Hogan_