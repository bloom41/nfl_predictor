// Validation middleware using Zod schemas
// Following CLAUDE.md: schema-first development

import { Request, Response, NextFunction } from 'express';
import { z } from 'zod';
import { PositionSchema, WeekSchema, ScoringFormatSchema } from '../schemas/player';

export const validatePosition = (req: Request, res: Response, next: NextFunction) => {
  try {
    const position = PositionSchema.parse(req.params.position);
    req.params.position = position;
    next();
  } catch (error) {
    res.status(400).json({
      error: 'Invalid position',
      message: 'Position must be one of: QB, RB, WR, TE',
    });
  }
};

export const validateRankingsQuery = (req: Request, res: Response, next: NextFunction) => {
  try {
    const querySchema = z.object({
      week: z.string().optional().transform(val => val ? parseInt(val) : 1).pipe(WeekSchema),
      scoring: z.string().optional().transform(val => val || 'half_ppr').pipe(ScoringFormatSchema),
      limit: z.string().optional().transform(val => val ? parseInt(val) : 10).pipe(z.number().int().min(1).max(50)),
    });

    const validatedQuery = querySchema.parse(req.query);
    req.query = validatedQuery as any;
    next();
  } catch (error) {
    res.status(400).json({
      error: 'Invalid query parameters',
      message: 'Week must be 1-18, scoring must be standard/half_ppr/ppr, limit must be 1-50',
    });
  }
};

export const validatePlayerId = (req: Request, res: Response, next: NextFunction) => {
  try {
    const playerIdSchema = z.string().min(1);
    const playerId = playerIdSchema.parse(req.params.playerId);
    req.params.playerId = playerId;
    next();
  } catch (error) {
    res.status(400).json({
      error: 'Invalid player ID',
      message: 'Player ID is required',
    });
  }
};

export const validateWeekQuery = (req: Request, res: Response, next: NextFunction) => {
  try {
    const weekParam = req.query.week;
    
    if (weekParam === undefined) {
      // Default to week 1 if not provided
      req.query.week = '1';
      return next();
    }

    // Validate week parameter
    if (typeof weekParam !== 'string') {
      return res.status(400).json({
        error: 'Invalid week parameter',
        message: 'Week must be a number between 1 and 18',
      });
    }

    const weekValue = parseInt(weekParam);
    
    if (isNaN(weekValue)) {
      return res.status(400).json({
        error: 'Invalid week parameter',
        message: 'Week must be a number between 1 and 18',
      });
    }

    const week = WeekSchema.parse(weekValue);
    req.query.week = week.toString();
    next();
  } catch (error) {
    res.status(400).json({
      error: 'Invalid week parameter', 
      message: 'Week must be a number between 1 and 18',
    });
  }
};

export const validateBoomBustQuery = (req: Request, res: Response, next: NextFunction) => {
  try {
    // Validate position (defaults to WR if not provided)
    const position = req.query.position || 'WR';
    const validatedPosition = PositionSchema.parse(position);
    req.query.position = validatedPosition;
    
    // Validate week (defaults to 1 if not provided)
    const week = req.query.week || '1';
    const weekValue = parseInt(week as string);
    if (isNaN(weekValue)) {
      return res.status(400).json({
        error: 'Invalid week parameter',
        message: 'Week must be a number between 1 and 18',
      });
    }
    const validatedWeek = WeekSchema.parse(weekValue);
    req.query.week = validatedWeek.toString();
    
    return next();
  } catch (error) {
    return res.status(400).json({
      error: 'Invalid parameters',
      message: 'Position must be QB, RB, WR, or TE. Week must be between 1 and 18.',
    });
  }
};

export const validateBaseProjection = (req: Request, res: Response, next: NextFunction) => {
  try {
    const baseProjection = req.query.base_projection;
    
    if (!baseProjection) {
      return res.status(400).json({
        error: 'Missing base_projection parameter',
        message: 'base_projection is required and must be a positive number',
      });
    }

    const projectionValue = parseFloat(baseProjection as string);
    
    if (isNaN(projectionValue) || projectionValue <= 0) {
      return res.status(400).json({
        error: 'Invalid base_projection parameter',
        message: 'base_projection must be a positive number',
      });
    }

    req.query.base_projection = projectionValue.toString();
    return next();
  } catch (error) {
    return res.status(400).json({
      error: 'Invalid base_projection parameter',
      message: 'base_projection must be a positive number',
    });
  }
};

export const validateTeamCode = (req: Request, res: Response, next: NextFunction): void => {
  const { teamCode } = req.params;
  
  if (!teamCode) {
    res.status(400).json({
      error: 'Team code required',
      message: 'Team code parameter is required',
    });
    return;
  }
  
  if (teamCode.length !== 3) {
    res.status(400).json({
      error: 'Invalid team code format',
      message: 'Team code must be exactly 3 characters',
    });
    return;
  }
  
  next();
};