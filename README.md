# 🏈 NFL Predictor

A comprehensive full-stack application for NFL player performance prediction and fantasy football analysis with enterprise-grade security and performance optimization.

## 🏗️ Architecture

### Full-Stack Components
- **Frontend**: React TypeScript (port 3000)
- **Backend API**: Express TypeScript (port 3001) 
- **ML Service**: Flask Python (port 5000)
- **Database**: PostgreSQL (primary) + SQLite (fallback)

### Data Flow
```
React Client → Express TS API → Python ML Service → PostgreSQL/SQLite
     ↓              ↓                    ↓              ↓
   Port 3000    Port 3001          Port 5000      Database
```

## 🚀 Quick Start

### Prerequisites
- Node.js 18+
- Python 3.8+
- PostgreSQL (or SQLite for development)

### 1. Backend Setup (Express TypeScript)
```bash
cd backend-ts
npm install
npm run build
npm start
```

### 2. Frontend Setup (React)
```bash
cd frontend/client
npm install
npm start
```

### 3. ML Service Setup (Flask Python)
```bash
pip install -r requirements.txt
python app.py
```

## 📊 Current Features

### ✅ Implemented
- **Player Rankings**: Multi-position rankings with scoring format support
- **ML Predictions**: Ensemble modeling with confidence intervals
- **Real-time Data**: Live injury, transaction, and depth chart monitoring
- **Batch Processing**: Async queue system for large requests
- **Advanced Analytics**: Boom/bust analysis, matchup insights
- **Elite Integration**: Django-powered enhanced predictions

### 🎯 API Endpoints
- `GET /api/status` - System health
- `GET /api/rankings/:position` - Position rankings
- `GET /api/projections` - ML predictions
- `POST /api/batch-rankings` - Batch processing
- `GET /api/injury` - Injury analysis
- `GET /api/boom-bust` - Volatility analysis

## 🔧 Development

### Backend (TypeScript)
- **Framework**: Express with TypeScript strict mode
- **Database**: Prisma ORM with PostgreSQL
- **Architecture**: Feature-based modular structure
- **Testing**: Jest with comprehensive coverage

### Frontend (React)
- **Framework**: React 19 with TypeScript
- **State**: TanStack Query for server state
- **UI**: Material-UI components
- **Routing**: React Router

### ML Service (Python)
- **Framework**: Flask with Django ORM integration
- **Models**: Position-optimized ensemble predictions
- **Data**: Real-time NFL data collection
- **Caching**: Intelligent caching with TTL

## 📈 Performance

### Current Metrics
- **API Response**: 24ms (elite projections)
- **Batch Rankings**: 408ms (multi-position)
- **ML Predictions**: 130-150ms (cached)
- **Database Queries**: 5ms average

### Optimization Features
- Async queue processing
- Multi-level caching
- Concurrent request handling
- Smart fallback strategies

## 🗂️ Project Structure

```
nfl_predictor/
├── README.md                    # This file
├── backend-ts/                  # Express TypeScript API
│   ├── src/
│   │   ├── features/           # Feature modules
│   │   ├── services/           # Core services
│   │   └── shared/            # Shared utilities
│   └── package.json
├── frontend/client/             # React application
│   ├── src/
│   │   ├── pages/             # Page components
│   │   ├── components/        # Reusable components
│   │   └── services/          # API services
│   └── package.json
├── app.py                      # Flask ML service
├── nfl_api/                    # Django models
├── src/                        # Python ML components
├── docs/                       # Documentation
└── reports/                    # Analysis reports
```

## 📋 System Status

### Recent Optimizations
- **Phase 1**: Python ML Bridge refactored (80 lines eliminated)
- **Phase 2**: ML service consolidation (350 lines eliminated)
- **Total**: 430+ lines of duplicate code removed
- **Architecture**: 3 → 1 unified ML prediction engine

### System Efficiency: 8.5/10
- ✅ Code consolidation complete
- ✅ Real data fallbacks implemented  
- ✅ Zero downtime during optimization
- ✅ All functionality preserved

## 📚 Documentation

- **[System Analysis](./reports/SYSTEM_ANALYSIS_REPORT.md)** - Comprehensive system overview
- **[Consolidation Plan](./reports/CONSOLIDATION_PLAN.md)** - Optimization strategy
- **[Architecture Guide](./backend-ts/docs/ARCHITECTURE.md)** - Technical architecture
- **[API Reference](./backend-ts/docs/README.md)** - Backend documentation

## 🛠️ Maintenance

### Key Commands
```bash
# Build all services
npm run build           # Backend TypeScript
cd frontend/client && npm run build  # React frontend

# Testing
npm test               # Backend tests
npm run test:coverage  # Coverage report

# Database
npm run db:migrate     # Run Prisma migrations
python manage.py migrate  # Django migrations
```

### Health Monitoring
- System status: `GET /api/status`
- Performance metrics: Built-in monitoring
- Error tracking: Comprehensive logging

## 🚀 Production Ready

This system is optimized for production with:
- TypeScript strict mode
- Comprehensive error handling
- Performance monitoring
- Security best practices
- Scalable architecture

---

**Current Version**: 2.1.3 (Unified ML Engine)  
**Last Updated**: July 2025  
**Status**: Production Ready ✅