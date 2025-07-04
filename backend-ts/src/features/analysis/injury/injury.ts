// Injury analysis router - minimal implementation to make tests pass

import { Router } from 'express';
import { validateWeekQuery, validatePlayerId } from '../../../shared/middleware/validation';
import { injuryService } from './injury-service';
import { Week } from '../../../shared/schemas/player';

export const injuryRouter = Router();

// Basic injury analysis endpoint
injuryRouter.get('/', 
  validateWeekQuery,
  async (req, res, next) => {
    try {
      const week = parseInt(req.query.week as string) as Week;
      const analysis = await injuryService.getBasicInjuryAnalysis(week);
      return res.json(analysis);
    } catch (error) {
      return next(error);
    }
  }
);

// Player-specific injury analysis endpoint
injuryRouter.get('/player/:playerId',
  validatePlayerId,
  validateWeekQuery,
  async (req, res, next) => {
    try {
      const { playerId } = req.params;
      const week = parseInt(req.query.week as string) as Week;
      
      if (!playerId) {
        return res.status(400).json({
          error: 'Player ID required',
          message: 'Player ID parameter is required',
        });
      }
      
      const analysis = await injuryService.getPlayerInjuryAnalysis(playerId, week);
      
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