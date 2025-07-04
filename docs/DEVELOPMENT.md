# Development Guide

## Development Environment Setup

### Prerequisites
- **Node.js**: 18+ (LTS recommended)
- **Python**: 3.8+ 
- **PostgreSQL**: 13+ (optional, SQLite fallback available)
- **Git**: Latest version
- **VS Code**: Recommended IDE

### IDE Setup (VS Code)

#### Required Extensions
```json
{
  "recommendations": [
    "ms-vscode.vscode-typescript-next",
    "bradlc.vscode-tailwindcss", 
    "ms-python.python",
    "ms-python.pylint",
    "esbenp.prettier-vscode",
    "ms-vscode.vscode-json"
  ]
}
```

#### VS Code Settings
```json
{
  "typescript.preferences.strict": true,
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": true
  },
  "python.defaultInterpreterPath": "./venv/bin/python"
}
```

## Project Structure

```
nfl_predictor/
├── backend-ts/                 # Express TypeScript API
│   ├── src/
│   │   ├── features/          # Feature modules (analysis, rankings, etc.)
│   │   ├── services/          # Core services (database, ML engine)
│   │   ├── shared/            # Shared utilities and types
│   │   └── index.ts           # Server entry point
│   ├── tests/                 # Test files
│   ├── package.json
│   └── tsconfig.json
├── frontend/client/            # React TypeScript application
│   ├── src/
│   │   ├── pages/             # Page components
│   │   ├── components/        # Reusable UI components
│   │   ├── services/          # API service layer
│   │   └── types/             # TypeScript type definitions
│   ├── public/
│   └── package.json
├── app.py                     # Flask ML service entry point
├── nfl_api/                   # Django models and admin
├── src/                       # Python ML components
│   ├── models/                # ML model implementations
│   ├── analysis/              # Analytics modules
│   ├── scrapers/              # Data collection
│   └── utils/                 # Utility functions
├── docs/                      # Documentation
├── reports/                   # Analysis reports
└── README.md
```

## Development Workflow

### 1. Initial Setup
```bash
# Clone repository
git clone <repository-url>
cd nfl_predictor

# Backend setup
cd backend-ts
npm install
npm run build

# Frontend setup
cd ../frontend/client
npm install

# Python environment setup
cd ../..
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Development Servers

#### Start All Services
```bash
# Terminal 1: Backend TypeScript
cd backend-ts
npm run dev

# Terminal 2: Frontend React
cd frontend/client
npm start

# Terminal 3: ML Service Python
python app.py
```

#### Individual Services
```bash
# Backend only (port 3001)
cd backend-ts && npm run dev

# Frontend only (port 3000)
cd frontend/client && npm start

# ML service only (port 5000)
python app.py
```

## Development Guidelines

### Code Style Standards

#### TypeScript/JavaScript
- **ESLint**: Airbnb configuration with TypeScript
- **Prettier**: Code formatting
- **Strict Mode**: TypeScript strict mode enabled
- **Naming**: camelCase for variables, PascalCase for types

#### Python
- **PEP 8**: Standard Python style guide
- **Black**: Code formatting
- **Pylint**: Code analysis
- **Type Hints**: Required for all functions

### Testing Strategy

#### Backend Testing
```bash
# Run all tests
npm test

# Run specific test file
npm test -- rankings.test.ts

# Coverage report
npm run test:coverage

# Watch mode for development
npm run test:watch
```

#### Frontend Testing
```bash
cd frontend/client

# Run React tests
npm test

# Coverage report
npm run test:coverage

# Visual regression tests
npm run test:visual
```

#### Python Testing
```bash
# Run Python tests
python -m pytest

# Specific test file
python -m pytest tests/test_predictions.py

# Coverage report
python -m pytest --cov=src
```

### Git Workflow

#### Branch Strategy
```bash
# Feature development
git checkout -b feature/player-rankings
git commit -m "feat: add player rankings endpoint"
git push origin feature/player-rankings

# Bug fixes
git checkout -b fix/prediction-accuracy
git commit -m "fix: correct prediction calculation logic"

# Release preparation
git checkout -b release/v2.1.4
```

#### Commit Message Format
```
type(scope): description

feat(rankings): add multi-position ranking support
fix(ml): correct ensemble model weights
docs(api): update endpoint documentation
test(frontend): add component integration tests
```

## Debugging

### Backend Debugging (Node.js)

#### VS Code Debug Configuration
```json
{
  "name": "Debug Backend",
  "type": "node",
  "request": "launch",
  "program": "${workspaceFolder}/backend-ts/src/index.ts",
  "preLaunchTask": "tsc: build",
  "outFiles": ["${workspaceFolder}/backend-ts/dist/**/*.js"],
  "env": {
    "NODE_ENV": "development"
  }
}
```

#### Debug Commands
```bash
# Debug with VS Code
F5 (with debug configuration)

# Debug with Node inspect
node --inspect dist/index.js

# Debug specific feature
npm run debug:rankings
```

### Frontend Debugging (React)

#### React Developer Tools
- Install React DevTools browser extension
- Use Component and Profiler tabs
- Monitor state changes and re-renders

#### Debug Commands
```bash
# Start with debugging enabled
REACT_APP_DEBUG=true npm start

# Debug bundle size
npm run analyze

# Debug performance
npm run test -- --testNamePattern="performance"
```

### Python Debugging

#### VS Code Python Debug
```json
{
  "name": "Debug Python ML",
  "type": "python",
  "request": "launch",
  "program": "${workspaceFolder}/app.py",
  "env": {
    "FLASK_ENV": "development",
    "FLASK_DEBUG": "1"
  }
}
```

#### Debug Commands
```bash
# Debug Flask application
python -m pdb app.py

# Debug specific model
python -m pdb src/models/prediction_model.py

# Profile performance
python -m cProfile app.py
```

## Database Development

### Database Setup
```bash
# PostgreSQL setup
createdb nfl_predictor
python manage.py migrate

# Prisma setup
cd backend-ts
npm run db:migrate
npm run db:seed
```

### Database Tools
```bash
# Django admin
python manage.py createsuperuser
python manage.py runserver 8000
# Access: http://localhost:8000/admin

# Prisma Studio
cd backend-ts
npx prisma studio
# Access: http://localhost:5555
```

### Migration Workflow
```bash
# Django migrations
python manage.py makemigrations
python manage.py migrate

# Prisma migrations
cd backend-ts
npx prisma migrate dev --name add-new-feature
npx prisma generate
```

## API Development

### API Testing
```bash
# Health check
curl http://localhost:3001/api/status

# Get rankings
curl http://localhost:3001/api/rankings/QB?limit=10

# Test ML predictions
curl http://localhost:5000/predict/QB/week/1
```

### API Documentation
```bash
# Generate OpenAPI docs
npm run docs:generate

# Serve documentation
npm run docs:serve
# Access: http://localhost:3002/docs
```

## Performance Monitoring

### Development Metrics
```bash
# Backend performance
npm run perf:backend

# Frontend bundle analysis
cd frontend/client && npm run analyze

# Python profiling
python -m cProfile -o profile.stats app.py
```

### Memory Monitoring
```bash
# Node.js memory usage
node --trace-gc dist/index.js

# Python memory profiling
python -m memory_profiler app.py
```

## Common Development Tasks

### Adding New Feature
```bash
# 1. Create feature branch
git checkout -b feature/new-feature

# 2. Add backend endpoint
# Edit: backend-ts/src/features/new-feature/

# 3. Add frontend component
# Edit: frontend/client/src/pages/

# 4. Add tests
# Edit: backend-ts/src/features/new-feature/*.test.ts

# 5. Update documentation
# Edit: docs/API.md
```

### Updating Dependencies
```bash
# Backend dependencies
cd backend-ts
npm audit
npm update
npm run test

# Frontend dependencies
cd frontend/client
npm audit
npm update
npm run test

# Python dependencies
pip list --outdated
pip install -r requirements.txt --upgrade
```

### Code Quality Checks
```bash
# TypeScript linting
npm run lint
npm run lint:fix

# Python linting
pylint src/
black src/
mypy src/

# Security checks
npm audit
pip check
```

## Troubleshooting

### Common Development Issues

#### Port Already in Use
```bash
# Find process using port
lsof -i :3001
kill -9 <PID>

# Or use different port
PORT=3002 npm start
```

#### TypeScript Build Errors
```bash
# Clear build cache
rm -rf dist/
npm run build

# Check TypeScript configuration
npx tsc --noEmit
```

#### Python Import Errors
```bash
# Check virtual environment
which python
pip list

# Reinstall dependencies
pip install -r requirements.txt
```

#### Database Connection Issues
```bash
# Check PostgreSQL status
pg_ctl status

# Test connection
psql -h localhost -p 5432 -U postgres -d nfl_predictor
```

### Development Tools

#### Useful Commands
```bash
# Project-wide search
grep -r "search-term" src/

# Find large files
find . -size +10M -type f

# Monitor file changes
watch -n 1 "ls -la dist/"

# Check service health
curl -s http://localhost:3001/api/status | jq
```

#### Performance Tools
```bash
# Lighthouse CI
npm install -g @lhci/cli
lhci autorun

# Bundle analyzer
cd frontend/client
npm run build
npx webpack-bundle-analyzer build/static/js/*.js
```

---

*Last Updated: July 2025*  
*Version: 2.1.3 (Unified ML Engine)*