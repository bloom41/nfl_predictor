# NFL Predictor Backend

TypeScript backend for NFL fantasy football predictions built with Test-Driven Development (TDD) principles.

## 🚀 Quick Start

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Run tests
npm test

# Build for production
npm run build
```

## 📊 API Endpoints

The server runs on `http://localhost:3002/api` with the following endpoints:

### Core Features
- `GET /api/status` - System health check
- `GET /api/features` - Available API capabilities
- `GET /api/rankings/:position` - Player rankings (QB, RB, WR, TE)
- `GET /api/player/:id/analysis` - Detailed player analysis

### Analysis Features
- `GET /api/injury` - Injury analysis and monitoring
- `GET /api/boom-bust` - Volatility and risk analysis
- `GET /api/matchup-analysis` - Game-specific insights
- `GET /api/projections` - ML-powered predictions

### Batch Processing
- `POST /api/batch-rankings` - Multi-position rankings
- `POST /api/boom-bust/batch` - Multi-player volatility
- `POST /api/projections/batch` - Multi-player predictions

## 🏗️ Architecture

This backend follows a domain-driven architecture with features organized by business capability:

```
src/
├── features/           # Domain-organized features
│   ├── analysis/      # ML analysis (boom-bust, injury, matchup, projections)
│   ├── players/       # Player analysis and lookup
│   ├── rankings/      # Player rankings and batch processing
│   └── system/        # Status and API discovery
└── shared/            # Shared utilities and types
    ├── middleware/    # Validation and error handling
    ├── schemas/       # Zod schemas and TypeScript types
    ├── test-utils/    # Testing utilities
    └── types/         # React-friendly type exports
```

## 📚 Documentation

Detailed documentation is available in the [`docs/`](./docs/) folder:

- **[Architecture Guide](./docs/ARCHITECTURE.md)** - Detailed system architecture and organization
- **[Improvements Summary](./docs/IMPROVEMENTS.md)** - Recent improvements and integration status

## 🧪 Testing

Built with TDD principles following CLAUDE.md guidelines:

- **88 tests** covering all endpoints and business logic
- **Behavior-driven testing** focusing on user-visible functionality
- **100% test coverage** through business behavior validation
- **Schema-first development** with Zod validation

```bash
npm test              # Run all tests
npm run test:watch    # Watch mode for development
npm run test:coverage # Generate coverage report
```

## 🔧 Development

### Environment Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Key settings:
- `PORT=3002` - Server port
- `NODE_ENV=development` - Environment mode
- Feature flags for ML components

### Code Standards

- **TypeScript strict mode** enforced
- **Schema-first development** with Zod
- **Functional programming** patterns
- **Test-driven development** (TDD) required

## 🌟 Features

### ML-Powered Analysis
- **Player Rankings** with confidence intervals
- **Injury Impact** assessment and monitoring
- **Boom/Bust Analysis** with position-specific volatility
- **Matchup Analysis** including weather and pace factors
- **Batch Processing** for efficient multi-query operations

### Production Ready
- Graceful shutdown handling
- Comprehensive error handling
- Environment-based configuration
- Rate limiting and security middleware
- React integration via shared types

## 📦 Integration

### React Frontend Integration

```typescript
// Clean type imports for frontend
import { 
  PlayerProjection, 
  ApiResponse, 
  AsyncState 
} from '@nfl-predictor/types';
```

### API Integration Examples

```bash
# Get QB rankings for week 1
curl "http://localhost:3002/api/rankings/QB?week=1&limit=10"

# Get ML projections with features
curl "http://localhost:3002/api/projections?position=RB"

# Batch query multiple positions
curl -X POST "http://localhost:3002/api/batch-rankings" \
  -H "Content-Type: application/json" \
  -d '{"positions": ["QB", "RB"], "week": 1}'
```

## 🤝 Contributing

1. Follow TDD principles - write tests first
2. Use schema-first development with Zod
3. Maintain TypeScript strict mode compliance
4. Follow the established architecture patterns

See [CLAUDE.md](./CLAUDE.md) for detailed development guidelines.

---

Built with ❤️ using TypeScript, Express, and TDD principles.