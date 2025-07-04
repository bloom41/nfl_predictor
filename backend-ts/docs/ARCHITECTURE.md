# Backend TypeScript Architecture

## Overview

The NFL Predictor backend has been reorganized into a domain-driven architecture that supports both Node.js backend operations and React frontend consumption. The structure separates concerns into feature-based modules while providing shared utilities and types.

## Directory Structure

```
src/
├── app.ts                      # Main Express application
├── api/                        # Integration tests
│   └── rankings.test.ts
├── features/                   # Domain-organized features
│   ├── analysis/              # Analysis features
│   │   ├── index.ts
│   │   ├── boom-bust/
│   │   │   ├── boom-bust.ts            # Router
│   │   │   └── boom-bust-service.ts    # Business logic
│   │   ├── injury/
│   │   │   ├── injury.ts               # Router
│   │   │   └── injury-service.ts       # Business logic
│   │   ├── matchup/
│   │   │   ├── matchup-analysis.ts     # Router
│   │   │   └── matchup-analysis-service.ts # Business logic
│   │   └── projections/
│   │       ├── projections.ts          # Router
│   │       └── ml-projections-service.ts # ML business logic
│   ├── players/               # Player features
│   │   ├── index.ts
│   │   ├── player.ts                   # Router
│   │   └── player-service.ts           # Business logic
│   ├── rankings/              # Rankings features
│   │   ├── index.ts
│   │   ├── rankings.ts                 # Router
│   │   ├── rankings-service.ts         # Business logic
│   │   ├── batch-rankings.ts           # Batch router
│   │   └── batch-rankings-service.ts   # Batch business logic
│   └── system/                # System features
│       ├── index.ts
│       ├── status.ts                   # Health check router
│       ├── status-service.ts           # Health check logic
│       ├── features.ts                 # API discovery router
│       └── features-service.ts         # API discovery logic
└── shared/                    # Shared utilities and types
    ├── middleware/            # Express middleware
    │   ├── error-handler.ts
    │   └── validation.ts
    ├── schemas/               # Zod schemas and TypeScript types
    │   └── player.ts
    ├── test-utils/            # Testing utilities
    │   ├── factories.ts
    │   └── setup.ts
    ├── types/                 # React-friendly type exports
    │   ├── index.ts
    │   └── package.json       # Types package for frontend
    └── utils/                 # Shared utility functions
```

## Feature Organization

### Analysis Features (`/features/analysis/`)
- **Boom-Bust Analysis**: Volatility modeling and risk assessment
- **Injury Analysis**: Player health impact and risk factors
- **Matchup Analysis**: Game-specific insights and weather impact
- **ML Projections**: Machine learning-powered predictions

### Core Features (`/features/rankings/`, `/features/players/`)
- **Rankings**: Player ranking algorithms and batch processing
- **Players**: Individual player analysis and lookup

### System Features (`/features/system/`)
- **Status**: Health checks and system monitoring
- **Features**: API discovery and capability reporting

## Shared Components (`/shared/`)

### Schemas (`/shared/schemas/`)
Schema-first development using Zod for runtime validation and TypeScript type generation.

### Types (`/shared/types/`)
React-friendly type exports with a dedicated package.json for frontend consumption. Includes:
- API response interfaces
- Paginated response types  
- Error response types
- Async state utilities
- API endpoint configuration types

### Middleware (`/shared/middleware/`)
- Request validation using Zod schemas
- Error handling with structured responses
- Common middleware patterns

### Test Utils (`/shared/test-utils/`)
- Mock data factories with partial override support
- Jest setup and configuration
- Testing utilities following TDD patterns

## Import Patterns

### Within Features
```typescript
// Same directory imports use relative paths
import { rankingsService } from './rankings-service';
```

### Shared Resources
```typescript
// Schemas from shared location
import { Position, Week } from '../../shared/schemas/player';

// Middleware from shared location  
import { validatePosition } from '../../shared/middleware/validation';

// Test utilities from shared location
import { getMockQB } from '../../shared/test-utils/factories';
```

### React Frontend Integration
```typescript
// Frontend can import types cleanly
import { 
  PlayerProjection, 
  ApiResponse, 
  AsyncState 
} from '@nfl-predictor/types';
```

## Benefits

1. **Domain Organization**: Related functionality is grouped together
2. **Clean Imports**: Feature index files provide clean import paths
3. **React Integration**: Shared types package supports frontend development
4. **Maintainability**: Clear separation of concerns and responsibilities
5. **Testability**: Shared test utilities and consistent patterns
6. **Type Safety**: Schema-first development with runtime validation

## Development Guidelines

- Each feature maintains its own router and service files
- Shared utilities are accessed via `../../shared/` paths
- Test files follow the same organizational structure
- All new features should follow the established pattern
- Type definitions are derived from Zod schemas in `/shared/schemas/`