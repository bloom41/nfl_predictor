// Boom-bust analysis router - minimal implementation to make tests pass

import { Router } from 'express';
import { 
  validateBoomBustQuery, 
  validatePlayerId, 
  validateBaseProjection,
  validateWeekQuery 
} from '../../../shared/middleware/validation';
import { boomBustService } from './boom-bust-service';
import { Position, Week, ScoringFormat, BatchBoomBustRequestSchema } from '../../../shared/schemas/player';

export const boomBustRouter = Router();

// Basic boom-bust analysis endpoint
boomBustRouter.get('/', 
  validateBoomBustQuery,
  async (req, res, next) => {
    try {
      const position = req.query.position as Position;
      const week = parseInt(req.query.week as string) as Week;
      
      const analysis = await boomBustService.getBasicBoomBustAnalysis(position, week);
      return res.json(analysis);
    } catch (error) {
      return next(error);
    }
  }
);

// Player-specific boom-bust analysis endpoint
boomBustRouter.get('/player/:playerId',
  validatePlayerId,
  validateBaseProjection,
  validateWeekQuery,
  async (req, res, next) => {
    try {
      const { playerId } = req.params;
      const baseProjection = parseFloat(req.query.base_projection as string);
      const week = parseInt(req.query.week as string) as Week;
      const scoringFormat = req.query.scoring_format as ScoringFormat || 'half_ppr';
      
      if (!playerId) {
        return res.status(400).json({
          error: 'Player ID required',
          message: 'Player ID parameter is required',
        });
      }
      
      const analysis = await boomBustService.getPlayerBoomBustAnalysis(
        playerId, 
        baseProjection, 
        week, 
        scoringFormat
      );
      
      if (!analysis) {
        return res.status(404).json({
          error: 'Player not found',
          message: `No player found with ID: ${playerId}`,
        });
      }

      return res.json(analysis);
    } catch (error) {
      return next(error);
    }
  }
);

// Batch boom-bust analysis endpoint
boomBustRouter.post('/batch',
  async (req, res, next) => {
    try {
      // Validate request body
      const batchRequest = BatchBoomBustRequestSchema.parse(req.body);
      
      const analysis = await boomBustService.getBatchBoomBustAnalysis(
        batchRequest.players,
        batchRequest.week,
        batchRequest.scoring_format
      );

      return res.json(analysis);
    } catch (error) {
      if (error instanceof Error && error.name === 'ZodError') {
        return res.status(400).json({
          error: 'Invalid request format',
          message: 'Request must include players array and week parameter',
        });
      }
      return next(error);
    }
  }
);