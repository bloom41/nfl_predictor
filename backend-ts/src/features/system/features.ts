// Features router - minimal implementation to make tests pass

import { Router } from 'express';
import { featuresService } from './features-service';

export const featuresRouter = Router();

featuresRouter.get('/', async (_req, res, next) => {
  try {
    const features = await featuresService.getFeatures();
    return res.json(features);
  } catch (error) {
    return next(error);
  }
});