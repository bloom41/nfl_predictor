// NFL Predictor Express Application
// Secure configuration with environment validation and secrets management

import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import rateLimit from 'express-rate-limit';
import { configService } from './services/config-init';
import { rankingsRouter } from './features/rankings';
import { playerRouter } from './features/players';
import { statusRouter, featuresRouter } from './features/system';
import { injuryRouter, boomBustRouter, matchupAnalysisRouter, projectionsRouter } from './features/analysis';
import { batchRankingsRouter } from './features/rankings/batch-rankings';
import { eliteRouter } from './features/elite';
import { errorHandler } from './shared/middleware/error-handler';

export const createApp = async () => {
  // Initialize secure configuration
  await configService.initialize();
  const config = configService.getConfig();

  const app = express();

  // Security middleware with configuration
  app.use(helmet({
    hsts: {
      maxAge: 31536000,
      includeSubDomains: true,
      preload: true
    },
    contentSecurityPolicy: config.server.environment === 'production' ? {
      directives: {
        defaultSrc: ["'self'"],
        styleSrc: ["'self'", "'unsafe-inline'"],
        scriptSrc: ["'self'"],
        imgSrc: ["'self'", "data:", "https:"],
      }
    } : false
  }));

  // CORS with secure configuration
  app.use(cors({
    origin: config.security.corsOrigins,
    credentials: true,
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization']
  }));

  // Rate limiting
  app.use(rateLimit({
    windowMs: config.security.rateLimit.windowMs,
    max: config.security.rateLimit.max,
    message: 'Too many requests from this IP, please try again later.',
    standardHeaders: true,
    legacyHeaders: false,
    skip: (req) => {
      // Skip rate limiting for health checks
      return req.path === '/api/status' || req.path === '/api/health';
    }
  }));

  app.use(express.json({ limit: '10mb' }));
  app.use(express.urlencoded({ extended: true, limit: '10mb' }));

  // Routes
  app.use('/api/rankings', rankingsRouter);
  app.use('/api/player', playerRouter);
  app.use('/api/status', statusRouter);
  app.use('/api/features', featuresRouter);
  app.use('/api/injury', injuryRouter);
  app.use('/api/boom-bust', boomBustRouter);
  app.use('/api/batch-rankings', batchRankingsRouter);
  app.use('/api/matchup-analysis', matchupAnalysisRouter);
  app.use('/api/projections', projectionsRouter);
  
  // Elite API with Django Integration
  app.use('/api/elite', eliteRouter);

  // Error handling
  app.use(errorHandler);

  return app;
};

// Export app factory for secure initialization
// Note: Tests and server startup should await createApp()