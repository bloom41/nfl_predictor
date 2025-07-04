// Player router - minimal implementation to make tests pass

import { Router } from 'express';
import { validatePlayerId } from '../../shared/middleware/validation';
import { playerService } from './player-service';
import { Week } from '../../shared/schemas/player';

export const playerRouter = Router();

playerRouter.get('/:playerId/analysis', 
  validatePlayerId,
  async (req, res, next) => {
    try {
      const { playerId } = req.params;
      const week = req.query.week ? parseInt(req.query.week as string) : 1;

      if (!playerId) {
        return res.status(400).json({
          error: 'Player ID required',
          message: 'Player ID parameter is required',
        });
      }

      const analysis = await playerService.getPlayerAnalysis(playerId, week as Week);
      
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