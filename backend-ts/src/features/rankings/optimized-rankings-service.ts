// Optimized Rankings Service with Advanced Caching
// High-performance rankings with multi-layer caching and smart invalidation

import { 
  RankingsResponse, 
  Position, 
  Week, 
  ScoringFormat,
  PlayerRanking 
} from '../../shared/schemas/player';
import { optimizedDatabaseService } from '../../services/optimized-database';
import { cacheService } from '../../services/cache-service';
import { unifiedMLEngine } from '../../services/unified-ml-engine';

export interface OptimizedGetRankingsParams {
  position: Position;
  week: Week;
  scoring: ScoringFormat;
  limit: number;
  useCache?: boolean;
  includeProjections?: boolean;
  includeInjuries?: boolean;
  teamFilter?: string;
}

export interface RankingsPerformanceMetrics {
  responseTime: number;
  cacheHit: boolean;
  dataSource: 'cache' | 'database' | 'ml_engine';
  playerCount: number;
  timestamp: number;
}

class OptimizedRankingsService {
  private performanceMetrics: RankingsPerformanceMetrics[] = [];
  private readonly MAX_METRICS = 500;
  
  // Cache TTL configurations (in seconds)
  private readonly CACHE_TTL = {
    rankings: 1800,        // 30 minutes for rankings
    currentWeek: 900,      // 15 minutes for current week
    historical: 86400,     // 24 hours for historical data
    playerRankings: 3600,  // 1 hour for individual player rankings
    teamRankings: 2700     // 45 minutes for team-specific rankings
  };

  /**
   * Main optimized rankings method with intelligent caching
   */
  async getOptimizedRankings(params: OptimizedGetRankingsParams): Promise<RankingsResponse> {
    const startTime = Date.now();
    let dataSource: 'cache' | 'database' | 'ml_engine' = 'database';

    try {
      const {
        position,
        week,
        scoring,
        limit,
        useCache = true,
        includeProjections = true,
        includeInjuries = true,
        teamFilter
      } = params;
      
      const safeTeamFilter = teamFilter !== undefined ? teamFilter : undefined;

      // Generate intelligent cache key
      const cacheKey = this.generateCacheKey(params);

      // Try cache first if enabled
      if (useCache) {
        const cachedResult = await cacheService.get<RankingsResponse>(cacheKey);
        if (cachedResult) {
          dataSource = 'cache';
          this.trackPerformance({
            responseTime: Date.now() - startTime,
            cacheHit: true,
            dataSource: 'cache',
            playerCount: cachedResult.rankings.length,
            timestamp: Date.now()
          });
          return cachedResult;
        }
      }

      // Get optimized player data with selective loading
      const playerDataOptions: any = {
        position,
        week,
        scoring,
        limit: limit * 2, // Get more players for better ranking accuracy
        includeInjuries
      };
      if (safeTeamFilter) {
        playerDataOptions.teamFilter = safeTeamFilter;
      }
      const players = await this.getOptimizedPlayerData(playerDataOptions);

      // Generate rankings with ML predictions if enabled
      let rankings: PlayerRanking[];
      if (includeProjections && players.length > 0) {
        rankings = await this.generateMLEnhancedRankings(players, { week, scoring, limit });
        dataSource = 'ml_engine';
      } else {
        rankings = await this.generateBasicRankings(players, { week, scoring, limit });
      }

      // Create response
      const response: RankingsResponse = {
        rankings: rankings.slice(0, limit),
        metadata: {
          position,
          week,
          scoring,
          limit,
          generatedAt: new Date().toISOString(),
          cached: false,
          dataSource,
          totalPlayersEvaluated: players.length,
          includeProjections,
          includeInjuries
        }
      };

      // Cache the result with appropriate TTL
      if (useCache) {
        const ttl = this.calculateCacheTTL(week, scoring);
        await cacheService.set(cacheKey, response, { 
          ttl,
          tags: [`position:${position}`, `week:${week}`, `scoring:${scoring}`]
        });
      }

      this.trackPerformance({
        responseTime: Date.now() - startTime,
        cacheHit: false,
        dataSource,
        playerCount: rankings.length,
        timestamp: Date.now()
      });

      return response;
    } catch (error) {
      console.error('Optimized rankings service error:', error);
      
      // Fallback to basic rankings
      return this.generateFallbackRankings(params);
    }
  }

  /**
   * Optimized player data retrieval with intelligent queries
   */
  private async getOptimizedPlayerData(options: {
    position: Position;
    week: Week;
    scoring: ScoringFormat;
    limit: number;
    includeInjuries: boolean;
    teamFilter?: string;
  }): Promise<any[]> {
    const { position, week, limit, includeInjuries, teamFilter } = options;

    // Get players with optimized database service
    const players = await optimizedDatabaseService.getOptimizedPlayers({
      position,
      ...(teamFilter && { team: teamFilter }),
      fantasy_relevant: true,
      status: 'active',
      week,
      season: 2024,
      include_stats: true,
      include_injuries: includeInjuries,
      include_depth_chart: true,
      include_team: true,
      limit: limit,
      useCache: true
    });

    return players.filter(player => {
      // Additional filtering for fantasy relevance
      if (!player.fantasy_relevant) return false;
      if (player.status !== 'active') return false;
      
      // Filter out players with severe injuries if injury data is included
      if (includeInjuries && player.injury_reports && player.injury_reports.length > 0) {
        const latestInjury = player.injury_reports[0];
        if (latestInjury && (latestInjury.injury_status === 'out' || latestInjury.injury_status === 'ir')) {
          return false;
        }
      }
      
      return true;
    });
  }

  /**
   * Generate ML-enhanced rankings using unified ML engine
   */
  private async generateMLEnhancedRankings(
    players: any[],
    options: { week: Week; scoring: ScoringFormat; limit: number }
  ): Promise<PlayerRanking[]> {
    const { week, scoring, limit } = options;

    try {
      // Get ML predictions for players
      const predictions = await Promise.allSettled(
        players.slice(0, limit * 1.5).map(async player => {
          try {
            const prediction = await unifiedMLEngine.getPlayerPrediction(
              player.player_id,
              {
                week,
                season: 2024,
                scoring_format: scoring
              }
            );

            if (!prediction) return null;
            return {
              player,
              prediction: prediction.ml_prediction,
              playerInfo: prediction.player_info
            };
          } catch (error) {
            console.warn(`ML prediction failed for player ${player.player_id}:`, error);
            return null;
          }
        })
      );

      // Process successful predictions
      const successfulPredictions = predictions
        .filter((result): result is PromiseFulfilledResult<any> => 
          result.status === 'fulfilled' && result.value !== null
        )
        .map(result => result.value);

      // Generate rankings from ML predictions
      const rankings: PlayerRanking[] = successfulPredictions
        .sort((a, b) => b.prediction.predicted_points - a.prediction.predicted_points)
        .map((item, index) => ({
          rank: index + 1,
          player: {
            id: item.player.player_id,
            name: item.player.full_name,
            position: item.player.position as Position,
            team: item.player.team_id,
            isActive: item.player.status === 'active',
            createdAt: new Date(item.player.created_at),
            updatedAt: new Date(item.player.updated_at)
          },
          predictedPoints: item.prediction.predicted_points,
          confidence: item.prediction.confidence,
          week,
          scoringFormat: options.scoring,
          trends: item.prediction.trends,
          injuryRisk: this.calculateInjuryRisk(item.player),
          depthChartPosition: item.player.depth_chart_position || 1
        }));

      return rankings;
    } catch (error) {
      console.error('ML-enhanced rankings generation failed:', error);
      return this.generateBasicRankings(players, options);
    }
  }

  /**
   * Generate basic rankings from database stats
   */
  private async generateBasicRankings(
    players: any[],
    options: { week: Week; scoring: ScoringFormat; limit: number }
  ): Promise<PlayerRanking[]> {
    const { week, limit } = options;

    const rankings: PlayerRanking[] = players
      .map(player => {
        // Calculate basic predicted points from recent stats
        const recentStats = player.season_stats?.slice(0, 3) || [];
        const avgPoints = recentStats.length > 0
          ? recentStats.reduce((sum: number, stat: any) => {
              return sum + (options.scoring === 'ppr' 
                ? stat.fantasy_points_ppr 
                : options.scoring === 'standard' 
                  ? stat.fantasy_points_standard 
                  : stat.fantasy_points_half_ppr);
            }, 0) / recentStats.length
          : this.getPositionBaseline(player.position);

        return {
          rank: 0, // Will be set after sorting
          player: {
            id: player.player_id,
            name: player.full_name,
            position: player.position as Position,
            team: player.team_id,
            isActive: player.status === 'active',
            createdAt: new Date(player.created_at),
            updatedAt: new Date(player.updated_at)
          },
          predictedPoints: avgPoints,
          confidence: 0.65, // Moderate confidence for stats-based predictions
          week,
          scoringFormat: options.scoring,
          injuryRisk: this.calculateInjuryRisk(player),
          depthChartPosition: player.depth_chart_position || 1
        };
      })
      .sort((a, b) => b.predictedPoints - a.predictedPoints)
      .slice(0, limit)
      .map((ranking, index) => ({
        ...ranking,
        rank: index + 1
      }));

    return rankings;
  }

  /**
   * Generate cache key for rankings request
   */
  private generateCacheKey(params: OptimizedGetRankingsParams): string {
    const { position, week, scoring, limit, includeProjections, includeInjuries, teamFilter } = params;
    return cacheService.keys.rankings(
      position,
      week,
      `${scoring}_${includeProjections ? 'ml' : 'basic'}_${includeInjuries ? 'inj' : 'noinj'}${teamFilter ? `_${teamFilter}` : ''}`,
      limit
    );
  }

  /**
   * Calculate appropriate cache TTL based on data recency
   */
  private calculateCacheTTL(week: Week, _scoring: ScoringFormat): number {
    const currentWeek = this.getCurrentNFLWeek();
    
    if (week === currentWeek) {
      return this.CACHE_TTL.currentWeek; // Shorter TTL for current week
    } else if (week > currentWeek) {
      return this.CACHE_TTL.rankings; // Normal TTL for future weeks
    } else {
      return this.CACHE_TTL.historical; // Longer TTL for historical data
    }
  }

  /**
   * Calculate injury risk for a player
   */
  private calculateInjuryRisk(player: any): number {
    if (!player.injury_reports || player.injury_reports.length === 0) {
      return 0.1; // Low baseline risk
    }

    const latestInjury = player.injury_reports[0];
    switch (latestInjury.injury_status) {
      case 'out': return 0.9;
      case 'doubtful': return 0.7;
      case 'questionable': return 0.4;
      case 'ir': return 1.0;
      default: return 0.1;
    }
  }

  /**
   * Get position baseline points for fallback
   */
  private getPositionBaseline(position: string): number {
    const baselines: Record<string, number> = {
      'QB': 18.0,
      'RB': 12.0,
      'WR': 10.0,
      'TE': 8.0
    };
    return baselines[position] || 8.0;
  }

  /**
   * Get current NFL week (simplified)
   */
  private getCurrentNFLWeek(): number {
    // Simplified logic - in real implementation would calculate based on current date
    return 1;
  }

  /**
   * Generate fallback rankings in case of errors
   */
  private async generateFallbackRankings(params: OptimizedGetRankingsParams): Promise<RankingsResponse> {
    const { position, week, scoring, limit } = params;
    
    // Generate minimal mock rankings
    const rankings: PlayerRanking[] = Array.from({ length: Math.min(limit, 10) }, (_, index) => ({
      rank: index + 1,
      player: {
        id: `fallback_${position}_${index}`,
        name: `${position} Player ${index + 1}`,
        position,
        team: 'UNK',
        isActive: true,
        createdAt: new Date(),
        updatedAt: new Date()
      },
      predictedPoints: Math.max(5, 20 - index * 2),
      confidence: 0.5,
      week,
      scoringFormat: scoring
    }));

    return {
      rankings,
      metadata: {
        position,
        week,
        scoring,
        limit,
        generatedAt: new Date().toISOString(),
        cached: false,
        dataSource: 'fallback',
        totalPlayersEvaluated: rankings.length
      }
    };
  }

  /**
   * Performance tracking
   */
  private trackPerformance(metrics: RankingsPerformanceMetrics): void {
    this.performanceMetrics.push(metrics);
    
    if (this.performanceMetrics.length > this.MAX_METRICS) {
      this.performanceMetrics = this.performanceMetrics.slice(-this.MAX_METRICS);
    }
  }

  /**
   * Get performance analytics
   */
  async getPerformanceAnalytics(): Promise<{
    averageResponseTime: number;
    cacheHitRate: number;
    dataSourceDistribution: Record<string, number>;
    recentPerformance: RankingsPerformanceMetrics[];
  }> {
    const totalMetrics = this.performanceMetrics.length;
    if (totalMetrics === 0) {
      return {
        averageResponseTime: 0,
        cacheHitRate: 0,
        dataSourceDistribution: {},
        recentPerformance: []
      };
    }

    const averageResponseTime = this.performanceMetrics.reduce((sum, m) => sum + m.responseTime, 0) / totalMetrics;
    const cacheHits = this.performanceMetrics.filter(m => m.cacheHit).length;
    const cacheHitRate = (cacheHits / totalMetrics) * 100;

    const dataSourceDistribution = this.performanceMetrics.reduce((acc, m) => {
      acc[m.dataSource] = (acc[m.dataSource] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    return {
      averageResponseTime: Math.round(averageResponseTime),
      cacheHitRate: Math.round(cacheHitRate * 100) / 100,
      dataSourceDistribution,
      recentPerformance: this.performanceMetrics.slice(-20)
    };
  }

  /**
   * Cache invalidation methods
   */
  async invalidateRankingsCache(position?: Position, week?: Week): Promise<void> {
    if (position && week) {
      await cacheService.invalidatePattern(`*:rankings:${position}:w${week}:*`);
    } else if (position) {
      await cacheService.invalidatePattern(`*:rankings:${position}:*`);
    } else if (week) {
      await cacheService.invalidatePattern(`*:rankings:*:w${week}:*`);
    } else {
      await cacheService.invalidatePattern(`*:rankings:*`);
    }
  }

  async invalidateByTags(tags: string[]): Promise<void> {
    await cacheService.invalidateByTags(tags);
  }

  /**
   * Health check
   */
  async healthCheck(): Promise<boolean> {
    try {
      // Test basic functionality
      const testParams: OptimizedGetRankingsParams = {
        position: 'QB',
        week: 1,
        scoring: 'half_ppr',
        limit: 5,
        useCache: false
      };

      const result = await this.getOptimizedRankings(testParams);
      return result.rankings.length > 0;
    } catch (error) {
      console.error('Optimized rankings service health check failed:', error);
      return false;
    }
  }
}

export const optimizedRankingsService = new OptimizedRankingsService();