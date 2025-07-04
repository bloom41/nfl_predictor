// Enhanced Batch Rankings Router with Queue Support

import { Router } from 'express';
import { BatchRankingsRequestSchema } from '../../shared/schemas/player';
import { batchRankingsService } from './batch-rankings-service';

export const batchRankingsRouter = Router();

// ==============================================================================
// SYNCHRONOUS BATCH RANKINGS
// ==============================================================================

// Standard batch rankings endpoint (immediate processing)
batchRankingsRouter.post('/', async (req, res, next) => {
  try {
    const batchRequest = BatchRankingsRequestSchema.parse(req.body);
    
    const rankings = await batchRankingsService.getBatchRankings(
      batchRequest.positions,
      batchRequest.week,
      batchRequest.scoring_format,
      batchRequest.limit,
      { useCache: true }
    );

    return res.json({
      success: true,
      data: rankings,
      processing: {
        method: 'synchronous',
        cached: rankings.metadata.cached || false,
source: 'enhanced_batch_service'
      }
    });
  } catch (error) {
    if (error instanceof Error && error.name === 'ZodError') {
      return res.status(400).json({
        success: false,
        error: 'Invalid request format',
        message: 'Request must include positions array with valid positions',
      });
    }
    return next(error);
  }
});

// ==============================================================================
// ASYNCHRONOUS QUEUE ENDPOINTS
// ==============================================================================

// Queue a batch request for async processing
batchRankingsRouter.post('/queue', async (req, res, next) => {
  try {
    const batchRequest = BatchRankingsRequestSchema.parse(req.body);
    
    const requestId = await batchRankingsService.queueBatchRequest(
      batchRequest.positions,
      batchRequest.week,
      batchRequest.scoring_format,
      batchRequest.limit,
      { useCache: true }
    );

    return res.status(202).json({
      success: true,
      requestId,
      message: 'Batch request queued for processing',
      status: 'queued',
      checkStatusUrl: `/api/batch-rankings/queue/${requestId}`,
      estimatedCompletionTime: '5-15 seconds'
    });
  } catch (error) {
    if (error instanceof Error && error.name === 'ZodError') {
      return res.status(400).json({
        success: false,
        error: 'Invalid request format',
        message: 'Request must include positions array with valid positions',
      });
    }
    return next(error);
  }
});

// Get status of queued request
batchRankingsRouter.get('/queue/:requestId', async (req, res) => {
  try {
    const { requestId } = req.params;
    const request = batchRankingsService.getQueuedRequestStatus(requestId);
    
    if (!request) {
      return res.status(404).json({
        success: false,
        error: 'Request not found',
        message: 'The requested batch job was not found or has expired'
      });
    }

    const response: any = {
      success: true,
      requestId: request.id,
      status: request.status,
      timestamp: request.timestamp,
      queuedAt: new Date(request.timestamp).toISOString()
    };

    // Add additional info based on status
    switch (request.status) {
      case 'pending':
        response.message = 'Request is waiting in queue';
        response.estimatedWaitTime = '2-10 seconds';
        break;
      case 'processing':
        response.message = 'Request is currently being processed';
        response.estimatedCompletionTime = '1-5 seconds';
        break;
      case 'completed':
        response.message = 'Request completed successfully';
        response.resultUrl = `/api/batch-rankings/queue/${requestId}/result`;
        response.completedAt = new Date().toISOString();
        break;
      case 'failed':
        response.message = 'Request failed to process';
        response.error = request.error;
        break;
    }

    return res.json(response);
  } catch (error) {
    return res.status(500).json({
      success: false,
      error: 'Failed to get request status',
      message: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

// Get result of completed queued request
batchRankingsRouter.get('/queue/:requestId/result', async (req, res) => {
  try {
    const { requestId } = req.params;
    const result = batchRankingsService.getQueuedRequestResult(requestId);
    
    if (!result) {
      const request = batchRankingsService.getQueuedRequestStatus(requestId);
      
      if (!request) {
        return res.status(404).json({
          success: false,
          error: 'Request not found',
          message: 'The requested batch job was not found or has expired'
        });
      }
      
      if (request.status === 'failed') {
        return res.status(500).json({
          success: false,
          error: 'Request failed',
          message: request.error || 'Unknown processing error'
        });
      }
      
      return res.status(202).json({
        success: false,
        error: 'Result not ready',
        message: `Request is ${request.status}. Please try again in a few seconds.`,
        status: request.status,
        checkStatusUrl: `/api/batch-rankings/queue/${requestId}`
      });
    }

    return res.json({
      success: true,
      data: result,
      processing: {
        method: 'asynchronous',
        requestId,
        cached: result.metadata.cached || false,
source: 'enhanced_batch_service'
      }
    });
  } catch (error) {
    return res.status(500).json({
      success: false,
      error: 'Failed to get request result',
      message: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

// ==============================================================================
// QUEUE MANAGEMENT ENDPOINTS
// ==============================================================================

// Get queue status and statistics
batchRankingsRouter.get('/queue-status', async (_req, res) => {
  try {
    const queueStatus = batchRankingsService.getQueueStatus();
    
    return res.json({
      success: true,
      queue: queueStatus,
      performance: {
        cacheEnabled: true,
        cacheTtlMinutes: 10,
        maxConcurrentRequests: 3,
        queueTimeoutSeconds: 30
      },
      health: {
        status: queueStatus.processing === 0 && queueStatus.pending === 0 ? 'idle' : 'active',
        totalActiveRequests: queueStatus.pending + queueStatus.processing
      }
    });
  } catch (error) {
    return res.status(500).json({
      success: false,
      error: 'Failed to get queue status',
      message: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

// Clear cache (admin endpoint)
batchRankingsRouter.delete('/cache', async (_req, res) => {
  try {
    batchRankingsService.clearCache();
    
    return res.json({
      success: true,
      message: 'Cache cleared successfully'
    });
  } catch (error) {
    return res.status(500).json({
      success: false,
      error: 'Failed to clear cache',
      message: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});