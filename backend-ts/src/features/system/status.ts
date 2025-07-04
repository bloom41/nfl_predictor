// Status router - minimal implementation to make tests pass

import { Router } from 'express';
import { statusService } from './status-service';

export const statusRouter = Router();

statusRouter.get('/', async (_req, res, next) => {
  try {
    const status = await statusService.getSystemStatus();
    res.json(status);
  } catch (error) {
    next(error);
  }
});