// Matchup analysis router - minimal implementation to make tests pass

import { Router } from 'express';
import { 
  validateWeekQuery,
  validateTeamCode,
  validatePlayerId
} from '../../../shared/middleware/validation';
import { matchupAnalysisService } from './matchup-analysis-service';
import { Week } from '../../../shared/schemas/player';

export const matchupAnalysisRouter = Router();

// Basic matchup analysis for a week
matchupAnalysisRouter.get('/', 
  validateWeekQuery,
  async (req, res, next) => {
    try {
      const week = parseInt(req.query.week as string) as Week;
      
      const analysis = await matchupAnalysisService.getWeekMatchups(week);
      return res.json(analysis);
    } catch (error) {
      return next(error);
    }
  }
);

// Team-specific matchup analysis
matchupAnalysisRouter.get('/team/:teamCode',
  validateTeamCode,
  validateWeekQuery,
  async (req, res, next) => {
    try {
      const { teamCode } = req.params;
      const week = parseInt(req.query.week as string) as Week;
      
      const analysis = await matchupAnalysisService.getTeamMatchupAnalysis(teamCode!.toUpperCase(), week);
      
      if (!analysis) {
        return res.status(404).json({
          error: 'Team not found',
          message: `No team found with code: ${teamCode}`,
        });
      }

      return res.json(analysis);
    } catch (error) {
      return next(error);
    }
  }
);

// Player-specific matchup analysis
matchupAnalysisRouter.get('/player/:playerId',
  validatePlayerId,
  validateWeekQuery,
  async (req, res, next) => {
    try {
      const { playerId } = req.params;
      const week = parseInt(req.query.week as string) as Week;
      
      const analysis = await matchupAnalysisService.getPlayerMatchupAnalysis(playerId!, week);
      
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