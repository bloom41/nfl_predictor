// Rankings router - minimal implementation to make tests pass
// Following CLAUDE.md: write minimum code to satisfy failing tests

import { Router } from 'express';
import { validatePosition, validateRankingsQuery } from '../../shared/middleware/validation';
import { rankingsService } from './rankings-service';
import { Position } from '../../shared/schemas/player';

export const rankingsRouter = Router();

rankingsRouter.get('/:position', 
  validatePosition,
  validateRankingsQuery,
  async (req, res, next) => {
    try {
      const { position } = req.params;
      const { week, scoring, limit } = req.query as any;

      const rankingsData = await rankingsService.getRankings({
        position: position as Position,
        week,
        scoring,
        limit,
      });

      res.json(rankingsData);
    } catch (error) {
      next(error);
    }
  }
);