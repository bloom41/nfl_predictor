// Enhanced Batch Rankings Service with Async Queue Processing
// Provides high-performance batch predictions using Python ML bridge with queue management

import { 
  BatchRankingsResponse,
  Position,
  Week,
  ScoringFormat,
  PlayerRanking
} from '../../shared/schemas/player';
import { pythonMLDataSource } from '../../services/python-ml-bridge';
import { unifiedMLEngine } from '../../services/unified-ml-engine';

// Queue management types
type QueuedRequest = {
  id: string;
  positions: Position[];
  week: Week;
  scoringFormat: ScoringFormat;
  limit: number;
  timestamp: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  result?: BatchRankingsResponse;
  error?: string;
};

type QueueProcessingOptions = {
  useCache?: boolean;
  priorityLevel?: 'low' | 'normal' | 'high';
  maxRetries?: number;
};

class BatchRankingsService {
  private requestQueue: Map<string, QueuedRequest> = new Map();
  private processing: boolean = false;
  private readonly MAX_CONCURRENT_REQUESTS = 3;
  private readonly QUEUE_TIMEOUT_MS = 30000; // 30 seconds
  private readonly CACHE_TTL_MS = 600000; // 10 minutes
  private resultCache: Map<string, { data: BatchRankingsResponse; expiry: number }> = new Map();

  /**
   * Main batch rankings method - enhanced with Python ML integration
   */
  async getBatchRankings(
    positions: Position[],
    week: Week = 1,
    scoringFormat: ScoringFormat = 'half_ppr',
    limit: number = 10,
    options: QueueProcessingOptions = {}
  ): Promise<BatchRankingsResponse> {
    // Track performance for monitoring
    
    try {
      // Check cache first if enabled
      if (options.useCache !== false) {
        const cached = this.getCachedResult(positions, week, scoringFormat, limit);
        if (cached) {
          return cached;
        }
      }

      // Try Python ML bridge first for best performance
      const pythonResult = await this.getBatchFromPythonML(positions, week, scoringFormat, limit);
      if (pythonResult) {
        this.cacheResult(positions, week, scoringFormat, limit, pythonResult);
        return pythonResult;
      }

      // Fallback to unified ML engine
      console.warn('Python ML service unavailable, using unified ML engine fallback');
      const unifiedResult = await this.getBatchFromUnifiedML(positions, week, scoringFormat, limit);
      this.cacheResult(positions, week, scoringFormat, limit, unifiedResult);
      return unifiedResult;

    } catch (error) {
      console.error('Batch rankings failed:', error);
      throw new Error(`Failed to get batch rankings: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Queue a batch request for async processing
   */
  async queueBatchRequest(
    positions: Position[],
    week: Week = 1,
    scoringFormat: ScoringFormat = 'half_ppr',
    limit: number = 10,
    _options: QueueProcessingOptions = {}
  ): Promise<string> {
    const requestId = this.generateRequestId();
    const queuedRequest: QueuedRequest = {
      id: requestId,
      positions,
      week,
      scoringFormat,
      limit,
      timestamp: Date.now(),
      status: 'pending'
    };

    this.requestQueue.set(requestId, queuedRequest);
    
    // Start processing if not already running
    if (!this.processing) {
      this.processQueue();
    }

    return requestId;
  }

  /**
   * Get status of queued request
   */
  getQueuedRequestStatus(requestId: string): QueuedRequest | null {
    return this.requestQueue.get(requestId) || null;
  }

  /**
   * Get result of completed queued request
   */
  getQueuedRequestResult(requestId: string): BatchRankingsResponse | null {
    const request = this.requestQueue.get(requestId);
    if (request?.status === 'completed' && request.result) {
      return request.result;
    }
    return null;
  }

  /**
   * Process queue asynchronously
   */
  private async processQueue(): Promise<void> {
    if (this.processing) return;
    this.processing = true;

    try {
      while (this.requestQueue.size > 0) {
        const pendingRequests = Array.from(this.requestQueue.values())
          .filter(req => req.status === 'pending')
          .sort((a, b) => a.timestamp - b.timestamp) // FIFO
          .slice(0, this.MAX_CONCURRENT_REQUESTS);

        if (pendingRequests.length === 0) break;

        // Process requests concurrently
        const processingPromises = pendingRequests.map(req => this.processQueuedRequest(req));
        await Promise.allSettled(processingPromises);

        // Clean up old completed requests
        this.cleanupCompletedRequests();
      }
    } finally {
      this.processing = false;
    }
  }

  /**
   * Process individual queued request
   */
  private async processQueuedRequest(request: QueuedRequest): Promise<void> {
    try {
      // Update status to processing
      request.status = 'processing';
      this.requestQueue.set(request.id, request);

      // Execute the batch request
      const result = await this.getBatchRankings(
        request.positions,
        request.week,
        request.scoringFormat,
        request.limit,
        { useCache: true }
      );

      // Store result
      request.result = result;
      request.status = 'completed';
      this.requestQueue.set(request.id, request);

    } catch (error) {
      request.error = error instanceof Error ? error.message : 'Unknown error';
      request.status = 'failed';
      this.requestQueue.set(request.id, request);
    }
  }

  /**
   * Get batch rankings from Python ML service
   */
  private async getBatchFromPythonML(
    positions: Position[],
    week: Week,
    scoringFormat: ScoringFormat,
    limit: number
  ): Promise<BatchRankingsResponse | null> {
    try {
      const isAvailable = await pythonMLDataSource.isAvailable();
      if (!isAvailable) return null;

      const batchResults = await pythonMLDataSource.getBatchRankingsData(positions, {
        week,
        season: 2024,
        scoring: scoringFormat,
        limit
      });

      if (!batchResults) return null;

      // Convert Python ML results to our format
      const rankings: Record<Position, PlayerRanking[]> = {} as Record<Position, PlayerRanking[]>;
      
      for (const position of positions) {
        const flaskResponse = batchResults[position];
        if (flaskResponse?.rankings) {
          rankings[position] = flaskResponse.rankings.map((ranking, index) => ({
            rank: index + 1,
            player: {
              id: `player_${ranking.player_name.replace(/\s+/g, '_')}`,
              name: ranking.player_name,
              position: ranking.position as Position,
              team: ranking.team,
              isActive: true,
              createdAt: new Date(),
              updatedAt: new Date()
            },
            predictedPoints: ranking.predicted_points,
            confidence: ranking.confidence,
            week,
            scoringFormat
          }));
        }
      }

      return {
        rankings,
        metadata: {
          positions,
          week,
          scoring: scoringFormat,
          limit,
          generatedAt: new Date().toISOString(),
          cached: false
        }
      };

    } catch (error) {
      console.error('Python ML batch request failed:', error);
      return null;
    }
  }

  /**
   * Get batch rankings from unified ML engine (fallback)
   */
  private async getBatchFromUnifiedML(
    positions: Position[],
    week: Week,
    scoringFormat: ScoringFormat,
    limit: number
  ): Promise<BatchRankingsResponse> {
    const rankings: Record<Position, PlayerRanking[]> = {} as Record<Position, PlayerRanking[]>;
    
    // Process each position using unified ML engine
    for (const position of positions) {
      try {
        const projections = await unifiedMLEngine.getFastPredictions({
          position,
          week,
          scoring_format: scoringFormat,
          limit
        });

        rankings[position] = projections.projections.map((proj, index) => ({
          rank: index + 1,
          player: {
            id: proj.player_info.id,
            name: proj.player_info.name,
            position: proj.player_info.position,
            team: proj.player_info.team,
            isActive: true,
            createdAt: new Date(),
            updatedAt: new Date()
          },
          predictedPoints: proj.ml_prediction.predicted_points,
          confidence: proj.ml_prediction.confidence,
          week,
          scoringFormat
        }));
      } catch (error) {
        console.error(`Failed to get ${position} rankings:`, error);
        rankings[position] = [];
      }
    }

    return {
      rankings,
      metadata: {
        positions,
        week,
        scoring: scoringFormat,
        limit,
        generatedAt: new Date().toISOString(),
        cached: false
      }
    };
  }

  /**
   * Cache management methods
   */
  private getCacheKey(positions: Position[], week: Week, scoringFormat: ScoringFormat, limit: number): string {
    return `${positions.sort().join(',')}_${week}_${scoringFormat}_${limit}`;
  }

  private getCachedResult(positions: Position[], week: Week, scoringFormat: ScoringFormat, limit: number): BatchRankingsResponse | null {
    const key = this.getCacheKey(positions, week, scoringFormat, limit);
    const cached = this.resultCache.get(key);
    
    if (cached && cached.expiry > Date.now()) {
      return {
        ...cached.data,
        metadata: {
          ...cached.data.metadata,
          cached: true
        }
      };
    }
    
    this.resultCache.delete(key);
    return null;
  }

  private cacheResult(positions: Position[], week: Week, scoringFormat: ScoringFormat, limit: number, result: BatchRankingsResponse): void {
    const key = this.getCacheKey(positions, week, scoringFormat, limit);
    this.resultCache.set(key, {
      data: result,
      expiry: Date.now() + this.CACHE_TTL_MS
    });
  }

  /**
   * Utility methods
   */
  private generateRequestId(): string {
    return `batch_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }


  private cleanupCompletedRequests(): void {
    const cutoffTime = Date.now() - this.QUEUE_TIMEOUT_MS;
    for (const [id, request] of this.requestQueue.entries()) {
      if (request.timestamp < cutoffTime && request.status !== 'processing') {
        this.requestQueue.delete(id);
      }
    }
  }

  /**
   * Queue status and management
   */
  getQueueStatus(): {
    totalRequests: number;
    pending: number;
    processing: number;
    completed: number;
    failed: number;
    cacheSize: number;
  } {
    const requests = Array.from(this.requestQueue.values());
    return {
      totalRequests: requests.length,
      pending: requests.filter(r => r.status === 'pending').length,
      processing: requests.filter(r => r.status === 'processing').length,
      completed: requests.filter(r => r.status === 'completed').length,
      failed: requests.filter(r => r.status === 'failed').length,
      cacheSize: this.resultCache.size
    };
  }

  clearCache(): void {
    this.resultCache.clear();
  }

  clearQueue(): void {
    this.requestQueue.clear();
  }
}

export const batchRankingsService = new BatchRankingsService();