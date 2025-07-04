# API Reference

## Overview

The NFL Predictor API provides comprehensive fantasy football data and predictions through RESTful endpoints. The API is built with Express TypeScript and integrates with Python ML services.

**Base URL**: `http://localhost:3001/api`  
**Content Type**: `application/json`  
**Authentication**: Currently open (add JWT when needed)

## System Endpoints

### Health Check
```http
GET /api/status
```

**Description**: System health and status information

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-07-04T12:00:00Z",
  "version": "2.1.3",
  "services": {
    "database": "connected",
    "ml_service": "available"
  },
  "uptime": 3600
}
```

### API Features
```http
GET /api/features
```

**Description**: Available API capabilities and endpoints

**Response**:
```json
{
  "endpoints": [
    "/rankings",
    "/projections", 
    "/injury",
    "/boom-bust",
    "/matchup-analysis"
  ],
  "features": [
    "real-time-data",
    "ml-predictions",
    "batch-processing"
  ]
}
```

## Player Rankings

### Get Position Rankings
```http
GET /api/rankings/:position
```

**Parameters**:
- `position` (path): Player position (`QB`, `RB`, `WR`, `TE`)
- `week` (query): NFL week number (1-18)
- `season` (query): NFL season year
- `scoring` (query): Scoring format (`standard`, `half_ppr`, `ppr`)
- `limit` (query): Number of results (default: 20)

**Example**:
```http
GET /api/rankings/QB?week=1&scoring=half_ppr&limit=10
```

**Response**:
```json
{
  "week": 1,
  "position": "QB",
  "scoring_format": "half_ppr",
  "rankings": [
    {
      "player_id": "josh_allen_qb",
      "player_name": "Josh Allen",
      "team": "BUF", 
      "position": "QB",
      "predicted_points": 24.8,
      "confidence": 0.89,
      "rank": 1,
      "tier": 1,
      "volatility": "low"
    }
  ],
  "metadata": {
    "total_players": 10,
    "last_updated": "2025-07-04T12:00:00Z",
    "data_sources": ["django", "python_ml"]
  }
}
```

### Batch Rankings
```http
POST /api/batch-rankings
```

**Description**: Get rankings for multiple positions

**Request Body**:
```json
{
  "positions": ["QB", "RB", "WR", "TE"],
  "week": 1,
  "scoring_format": "half_ppr",
  "limit_per_position": 10
}
```

**Response**:
```json
{
  "week": 1,
  "scoring_format": "half_ppr",
  "rankings": {
    "QB": [...],
    "RB": [...],
    "WR": [...],
    "TE": [...]
  },
  "metadata": {
    "total_players": 40,
    "processing_time_ms": 408,
    "queue_position": 1
  }
}
```

## ML Projections

### Get ML Predictions
```http
GET /api/projections
```

**Parameters**:
- `week` (query): NFL week number
- `position` (query): Filter by position (optional)
- `scoring_format` (query): Scoring format
- `limit` (query): Number of results

**Example**:
```http
GET /api/projections?week=1&position=RB&limit=15
```

**Response**:
```json
{
  "week": 1,
  "projections": [
    {
      "player_id": "christian_mccaffrey_rb",
      "player_name": "Christian McCaffrey",
      "position": "RB",
      "team": "SF",
      "predicted_points": 22.3,
      "confidence": 0.92,
      "features": {
        "recent_performance": 24.1,
        "trend_direction": 0.15,
        "matchup_difficulty": 0.3,
        "injury_status": "healthy"
      },
      "model_version": "v2.1.3-unified"
    }
  ],
  "metadata": {
    "total_players": 15,
    "model_updated_at": "2025-07-04T10:00:00Z",
    "feature_importance": {
      "recent_performance": 0.35,
      "matchup_difficulty": 0.25,
      "injury_status": 0.25,
      "weather_conditions": 0.15
    }
  }
}
```

### Individual Player Projection
```http
GET /api/projections/player/:playerId
```

**Parameters**:
- `playerId` (path): Unique player identifier
- `week` (query): NFL week number
- `scoring_format` (query): Scoring format

**Response**:
```json
{
  "player_info": {
    "player_id": "josh_allen_qb",
    "position": "QB",
    "team": "BUF"
  },
  "prediction": {
    "predicted_points": 24.8,
    "confidence": 0.89,
    "range": {
      "floor": 18.2,
      "ceiling": 31.4
    }
  },
  "model_details": {
    "model_version": "v2.1.3-unified",
    "training_date": "2025-07-04T12:00:00Z",
    "accuracy_metrics": {
      "rmse": 4.2,
      "mae": 3.1,
      "r2_score": 0.78
    }
  },
  "feature_breakdown": {
    "recent_games": [],
    "season_trends": {},
    "matchup_analysis": {
      "difficulty_score": 0.25,
      "key_factors": []
    }
  }
}
```

### Batch Player Projections
```http
POST /api/projections/batch
```

**Request Body**:
```json
{
  "player_ids": ["josh_allen_qb", "stefon_diggs_wr"],
  "week": 1,
  "scoring_format": "half_ppr"
}
```

**Response**:
```json
{
  "projections": [
    {
      "player_info": {...},
      "prediction": {...},
      "model_details": {...}
    }
  ]
}
```

## Analysis Endpoints

### Injury Analysis
```http
GET /api/injury
```

**Parameters**:
- `position` (query): Filter by position
- `severity` (query): Filter by injury severity
- `timeframe` (query): Days to look back

**Response**:
```json
{
  "injury_reports": [
    {
      "player_id": "saquon_barkley_rb",
      "player_name": "Saquon Barkley", 
      "team": "NYG",
      "injury_status": "questionable",
      "injury_type": "ankle",
      "impact_score": 0.3,
      "return_probability": 0.7,
      "last_updated": "2025-07-04T10:00:00Z"
    }
  ],
  "summary": {
    "total_injuries": 15,
    "by_severity": {
      "questionable": 8,
      "doubtful": 4,
      "out": 3
    }
  }
}
```

### Boom/Bust Analysis
```http
GET /api/boom-bust
```

**Parameters**:
- `position` (query): Player position
- `week` (query): NFL week
- `scoring_format` (query): Scoring format

**Response**:
```json
{
  "analysis": [
    {
      "player_id": "tyreek_hill_wr",
      "player_name": "Tyreek Hill",
      "position": "WR",
      "boom_probability": 0.35,
      "bust_probability": 0.15,
      "floor_projection": 8.2,
      "ceiling_projection": 28.6,
      "volatility_rating": "high",
      "reasons": [
        "High target share variance",
        "Weather-dependent performance",
        "Explosive play potential"
      ]
    }
  ]
}
```

### Matchup Analysis
```http
GET /api/matchup-analysis
```

**Parameters**:
- `week` (query): NFL week
- `team` (query): Team abbreviation (optional)

**Response**:
```json
{
  "matchups": [
    {
      "game_id": "buf_vs_mia_w1",
      "teams": {
        "home": "MIA",
        "away": "BUF"
      },
      "game_info": {
        "week": 1,
        "date": "2025-09-08",
        "time": "1:00 PM",
        "weather": "clear, 75°F"
      },
      "analysis": {
        "total_points": 47.5,
        "pace": "fast",
        "key_factors": [
          "High-scoring affair expected",
          "Neutral weather conditions",
          "Both teams pass-heavy"
        ]
      },
      "player_impacts": [
        {
          "player_id": "josh_allen_qb",
          "impact": "positive",
          "reason": "Weak pass defense matchup"
        }
      ]
    }
  ]
}
```

## Player Data

### Get Player Information
```http
GET /api/player/:playerId
```

**Response**:
```json
{
  "player_info": {
    "player_id": "josh_allen_qb",
    "full_name": "Josh Allen",
    "position": "QB",
    "team": "BUF",
    "jersey_number": 17,
    "status": "active",
    "depth_chart_position": 1
  },
  "season_stats": [...],
  "recent_games": [...],
  "injury_history": [...]
}
```

### Player Analysis
```http
GET /api/player/:playerId/analysis
```

**Parameters**:
- `playerId` (path): Player identifier
- `weeks` (query): Number of weeks to analyze

**Response**:
```json
{
  "player_analysis": {
    "consistency_score": 0.82,
    "trend_direction": "upward",
    "target_share": 0.28,
    "red_zone_usage": 0.15,
    "strength_of_schedule": 0.45
  },
  "recommendations": [
    "Start with confidence",
    "Strong floor projection",
    "Favorable upcoming schedule"
  ]
}
```

## Elite Features

### Enhanced Projections
```http
GET /api/elite/projections
```

**Description**: Django-enhanced projections with comprehensive data

**Response**:
```json
{
  "enhanced_projections": [
    {
      "player_info": {...},
      "ml_prediction": {
        "predicted_points": 24.8,
        "confidence": 0.89,
        "model_blend": {
          "django_weight": 0.65,
          "typescript_weight": 0.35,
          "ensemble_confidence": 0.87
        }
      },
      "enhanced_features": {
        "depth_chart_impact": 0.8,
        "injury_risk_assessment": {...},
        "transaction_risk": {...},
        "historical_performance": {...}
      },
      "volatility_metrics": {
        "boom_probability": 0.35,
        "bust_probability": 0.12,
        "floor_projection": 18.2,
        "ceiling_projection": 31.4
      }
    }
  ]
}
```

## Error Responses

### Standard Error Format
```json
{
  "error": "Invalid position",
  "message": "Position must be one of: QB, RB, WR, TE",
  "code": "INVALID_POSITION",
  "timestamp": "2025-07-04T12:00:00Z"
}
```

### Common HTTP Status Codes
- `200` - Success
- `400` - Bad Request (invalid parameters)
- `404` - Not Found (player/resource not found)
- `429` - Too Many Requests (rate limited)
- `500` - Internal Server Error
- `503` - Service Unavailable (ML service down)

## Rate Limiting

- **Standard endpoints**: 100 requests/minute
- **Batch endpoints**: 10 requests/minute
- **ML projections**: 50 requests/minute

## WebSocket Endpoints (Future)

### Real-time Updates
```javascript
// Future implementation
const ws = new WebSocket('ws://localhost:3001/ws/updates');
ws.onmessage = (event) => {
  const update = JSON.parse(event.data);
  // Handle real-time injury/transaction updates
};
```

## SDK Usage (Future)

### JavaScript/TypeScript
```typescript
import { NFLPredictorClient } from '@nfl-predictor/sdk';

const client = new NFLPredictorClient({
  baseURL: 'http://localhost:3001',
  apiKey: 'your-api-key'
});

const rankings = await client.rankings.getByPosition('QB', {
  week: 1,
  scoring: 'half_ppr',
  limit: 10
});
```

---

*Last Updated: July 2025*  
*Version: 2.1.3 (Unified ML Engine)*