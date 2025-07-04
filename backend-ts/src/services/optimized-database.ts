// Optimized Database Service with Multi-Layer Caching
// High-performance database layer with Redis caching and query optimization

import { PrismaClient } from '@prisma/client';
import { cacheService } from './cache-service';
import type {
  CompleteNFLPlayer,
  PlayerTransaction,
  InjuryReport,
  DepthChart,
  SeasonStats,
  NFLTeam
} from '@prisma/client';

// Enhanced types for optimized queries
export type Position = 'QB' | 'RB' | 'WR' | 'TE';
export type PlayerStatus = 'active' | 'injured' | 'suspended' | 'practice_squad' | 'ir' | 'retired' | 'free_agent';
export type InjuryStatus = 'healthy' | 'questionable' | 'doubtful' | 'out' | 'ir';

export type OptimizedPlayerWithRelations = CompleteNFLPlayer & {
  team_ref?: NFLTeam;
  transactions?: PlayerTransaction[];
  injury_reports?: InjuryReport[];
  season_stats?: SeasonStats[];
  depth_charts?: DepthChart[];
};

export type OptimizedPlayerQueryOptions = {
  position?: Position;
  team?: string;
  fantasy_relevant?: boolean;
  status?: PlayerStatus;
  week?: number;
  season?: number;
  include_transactions?: boolean;
  include_injuries?: boolean;
  include_stats?: boolean;
  include_depth_chart?: boolean;
  include_team?: boolean;
  limit?: number;
  useCache?: boolean;
  cacheKey?: string;
};

export type BatchPlayerOptions = {
  playerIds: string[];
  season?: number;
  week?: number;
  include_stats?: boolean;
  include_injuries?: boolean;
  include_transactions?: boolean;
  useCache?: boolean;
};

export type QueryPerformanceMetrics = {
  queryTime: number;
  cacheHit: boolean;
  resultCount: number;
  queryType: string;
};

class OptimizedDatabaseService {
  private prisma: PrismaClient;
  private queryMetrics: QueryPerformanceMetrics[] = [];
  private readonly MAX_METRICS = 1000;

  constructor() {
    try {
      this.prisma = new PrismaClient({
        log: ['warn', 'error'],
        datasources: {
          db: {
            url: process.env.DATABASE_URL || 'postgresql://localhost:5432/nfl_predictor'
          }
        }
      });

      // Optimize connection pool
      this.prisma.$connect();
    } catch (error) {
      console.warn('Prisma client initialization failed - using fallback mode:', error);
      this.prisma = null as any;
    }
  }

  /**
   * Enhanced wrapper for cached database operations
   */
  private async cachedQuery<T>(
    cacheKey: string,
    queryFn: () => Promise<T>,
    options: { ttl?: number; useCache?: boolean } = {}
  ): Promise<T> {
    const startTime = Date.now();
    let cacheHit = false;
    let result: T;

    try {
      // Check cache first if enabled
      if (options.useCache !== false) {
        const cached = await cacheService.get<T>(cacheKey);
        if (cached !== null) {
          cacheHit = true;
          result = cached;
        } else {
          // Execute query and cache result
          result = await queryFn();
          const cacheOptions: any = {};
          if (options.ttl !== undefined) {
            cacheOptions.ttl = options.ttl;
          }
          await cacheService.set(cacheKey, result, cacheOptions);
        }
      } else {
        result = await queryFn();
      }

      // Track performance metrics
      this.trackQueryMetrics({
        queryTime: Date.now() - startTime,
        cacheHit,
        resultCount: Array.isArray(result) ? result.length : 1,
        queryType: cacheKey.split(':')[1] || 'unknown'
      });

      return result;
    } catch (error) {
      console.error(`Database query failed for key ${cacheKey}:`, error);
      throw error;
    }
  }

  /**
   * Optimized player queries with intelligent caching
   */
  async getOptimizedPlayers(options: OptimizedPlayerQueryOptions = {}): Promise<OptimizedPlayerWithRelations[]> {
    const {
      position,
      team,
      fantasy_relevant,
      status,
      week,
      season = 2024,
      include_transactions = false,
      include_injuries = false,
      include_stats = false,
      include_depth_chart = false,
      include_team = true,
      limit = 100,
      useCache = true,
      cacheKey
    } = options;

    // Generate optimized cache key
    const key = cacheKey || cacheService.keys.player(
      `query:${position || 'all'}:${team || 'all'}:${fantasy_relevant}:${status || 'all'}:${season}:${week || 'all'}:${limit}`
    );

    return this.cachedQuery(
      key,
      async () => {
        // Build optimized where clause
        const where: any = {};
        
        // Only add conditions that will use indexes
        if (position) where.position = position;
        if (team) where.team_id = team;
        if (fantasy_relevant !== undefined) where.fantasy_relevant = fantasy_relevant;
        if (status) where.status = status;

        // Build optimized include clause - only include what's needed
        const include: any = {};
        if (include_team) include.team_ref = true;
        
        if (include_transactions) {
          include.transactions = {
            orderBy: { transaction_date: 'desc' },
            take: 5 // Limit to recent transactions
          };
        }

        if (include_injuries) {
          include.injury_reports = week ? 
            { 
              where: { week, season },
              orderBy: { date_reported: 'desc' },
              take: 3
            } :
            { 
              where: { season },
              orderBy: { date_reported: 'desc' },
              take: 3
            };
        }

        if (include_stats) {
          include.season_stats = week ?
            { where: { week, season } } :
            { 
              where: { season },
              orderBy: { week: 'desc' },
              take: 5 // Limit to recent weeks
            };
        }

        if (include_depth_chart) {
          include.depth_charts = week ?
            { where: { week, season } } :
            { 
              where: { season },
              orderBy: { week: 'desc' },
              take: 1 // Only latest depth chart
            };
        }

        // Execute optimized query
        return this.prisma.completeNFLPlayer.findMany({
          where,
          include,
          orderBy: [
            { fantasy_relevant: 'desc' },
            { depth_chart_position: 'asc' },
            { full_name: 'asc' }
          ],
          take: limit
        }) as Promise<OptimizedPlayerWithRelations[]>;
      },
      { useCache }
    );
  }

  /**
   * Optimized single player query with comprehensive caching
   */
  async getOptimizedPlayerById(
    playerId: string, 
    options: OptimizedPlayerQueryOptions = {}
  ): Promise<OptimizedPlayerWithRelations | null> {
    const {
      week,
      season = 2024,
      include_transactions = true,
      include_injuries = true,
      include_stats = true,
      include_depth_chart = true,
      useCache = true
    } = options;

    const cacheKey = cacheService.keys.player(playerId);

    return this.cachedQuery(
      cacheKey,
      async () => {
        // Optimized include strategy - selective loading
        const include: any = {
          team_ref: true
        };

        if (include_transactions) {
          include.transactions = {
            orderBy: { transaction_date: 'desc' },
            take: 10
          };
        }

        if (include_injuries) {
          include.injury_reports = {
            where: { season },
            orderBy: { date_reported: 'desc' },
            take: 5
          };
        }

        if (include_stats) {
          include.season_stats = week ?
            { where: { week, season } } :
            { 
              where: { season },
              orderBy: { week: 'desc' },
              take: 10
            };
        }

        if (include_depth_chart) {
          include.depth_charts = week ?
            { where: { week, season } } :
            { 
              where: { season },
              orderBy: { week: 'desc' },
              take: 3
            };
        }

        return this.prisma.completeNFLPlayer.findUnique({
          where: { player_id: playerId },
          include
        }) as Promise<OptimizedPlayerWithRelations | null>;
      },
      { useCache, ttl: 3600 } // 1 hour cache for individual players
    );
  }

  /**
   * Batch player queries with intelligent caching
   */
  async getBatchPlayersOptimized(options: BatchPlayerOptions): Promise<OptimizedPlayerWithRelations[]> {
    const {
      playerIds,
      season = 2024,
      week,
      include_stats = false,
      include_injuries = false,
      include_transactions = false,
      useCache = true
    } = options;

    // Cache individual players and batch together
    const cacheKey = cacheService.keys.batchRankings(
      playerIds.sort(),
      week || 0,
      `${season}`,
      playerIds.length
    );

    return this.cachedQuery(
      cacheKey,
      async () => {
        const include: any = {
          team_ref: true
        };

        if (include_stats) {
          include.season_stats = week ?
            { where: { week, season } } :
            { where: { season }, orderBy: { week: 'desc' }, take: 5 };
        }

        if (include_injuries) {
          include.injury_reports = {
            where: { season },
            orderBy: { date_reported: 'desc' },
            take: 3
          };
        }

        if (include_transactions) {
          include.transactions = {
            orderBy: { transaction_date: 'desc' },
            take: 5
          };
        }

        return this.prisma.completeNFLPlayer.findMany({
          where: {
            player_id: { in: playerIds }
          },
          include
        }) as Promise<OptimizedPlayerWithRelations[]>;
      },
      { useCache, ttl: 1800 } // 30 minutes for batch queries
    );
  }

  /**
   * Optimized season statistics with caching
   */
  async getOptimizedSeasonStats(
    playerId: string,
    season: number = 2024,
    week?: number,
    useCache: boolean = true
  ): Promise<SeasonStats[]> {
    const cacheKey = cacheService.keys.playerStats(playerId, season, week);

    return this.cachedQuery(
      cacheKey,
      async () => {
        const numericPlayerId = parseInt(playerId, 10);
        if (isNaN(numericPlayerId)) return [];

        const where: any = {
          player_id: numericPlayerId,
          season
        };

        if (week) where.week = week;

        return this.prisma.seasonStats.findMany({
          where,
          include: { player: true },
          orderBy: { week: 'asc' }
        });
      },
      { useCache, ttl: week ? 14400 : 43200 } // 4 hours for current week, 12 hours for season
    );
  }

  /**
   * Optimized injury reports with caching
   */
  async getOptimizedInjuryReports(
    week?: number,
    season: number = 2024,
    useCache: boolean = true
  ): Promise<InjuryReport[]> {
    const cacheKey = cacheService.keys.injuries(week || 0, season);

    return this.cachedQuery(
      cacheKey,
      async () => {
        const where: any = { season };
        if (week) where.week = week;

        return this.prisma.injuryReport.findMany({
          where,
          orderBy: { date_reported: 'desc' },
          take: week ? 100 : 50 // Limit results
        });
      },
      { useCache, ttl: 7200 } // 2 hours cache for injury reports
    );
  }

  /**
   * Optimized team roster with caching
   */
  async getOptimizedTeamRoster(
    team: string,
    position?: Position,
    useCache: boolean = true
  ): Promise<CompleteNFLPlayer[]> {
    const cacheKey = cacheService.keys.teamRoster(team, position);

    return this.cachedQuery(
      cacheKey,
      async () => {
        const where: any = { 
          team_id: team,
          status: 'active',
          fantasy_relevant: true
        };
        if (position) where.position = position;

        return this.prisma.completeNFLPlayer.findMany({
          where,
          include: { team_ref: true },
          orderBy: [
            { position: 'asc' },
            { depth_chart_position: 'asc' },
            { full_name: 'asc' }
          ],
          take: 100
        });
      },
      { useCache, ttl: 21600 } // 6 hours cache for team rosters
    );
  }

  /**
   * Cache invalidation methods
   */
  async invalidatePlayerCache(playerId: string): Promise<void> {
    await cacheService.invalidatePattern(`*:player:${playerId}*`);
  }

  async invalidateTeamCache(teamId: string): Promise<void> {
    await cacheService.invalidatePattern(`*:team:${teamId}*`);
  }

  async invalidateWeekCache(week: number, season: number): Promise<void> {
    await cacheService.invalidatePattern(`*:w${week}*`);
    await cacheService.invalidatePattern(`*:${season}:w${week}*`);
  }

  async invalidatePositionCache(position: Position): Promise<void> {
    await cacheService.invalidatePattern(`*:${position}:*`);
  }

  /**
   * Performance monitoring
   */
  private trackQueryMetrics(metrics: QueryPerformanceMetrics): void {
    this.queryMetrics.push(metrics);
    
    // Keep only recent metrics
    if (this.queryMetrics.length > this.MAX_METRICS) {
      this.queryMetrics = this.queryMetrics.slice(-this.MAX_METRICS);
    }
  }

  async getPerformanceMetrics(): Promise<{
    averageQueryTime: number;
    cacheHitRate: number;
    slowQueries: QueryPerformanceMetrics[];
    totalQueries: number;
  }> {
    const totalQueries = this.queryMetrics.length;
    if (totalQueries === 0) {
      return {
        averageQueryTime: 0,
        cacheHitRate: 0,
        slowQueries: [],
        totalQueries: 0
      };
    }

    const averageQueryTime = this.queryMetrics.reduce((sum, m) => sum + m.queryTime, 0) / totalQueries;
    const cacheHits = this.queryMetrics.filter(m => m.cacheHit).length;
    const cacheHitRate = (cacheHits / totalQueries) * 100;
    const slowQueries = this.queryMetrics
      .filter(m => m.queryTime > 1000) // Queries slower than 1 second
      .sort((a, b) => b.queryTime - a.queryTime)
      .slice(0, 10);

    return {
      averageQueryTime: Math.round(averageQueryTime),
      cacheHitRate: Math.round(cacheHitRate * 100) / 100,
      slowQueries,
      totalQueries
    };
  }

  /**
   * Health check and cleanup
   */
  async healthCheck(): Promise<boolean> {
    try {
      if (!this.prisma) return false;
      await this.prisma.$queryRaw`SELECT 1`;
      return await cacheService.healthCheck();
    } catch (error) {
      console.error('Optimized database health check failed:', error);
      return false;
    }
  }

  async disconnect(): Promise<void> {
    if (this.prisma) {
      await this.prisma.$disconnect();
    }
    await cacheService.disconnect();
  }

  /**
   * Cache warming for common queries
   */
  async warmupCache(): Promise<void> {
    console.log('🔥 Starting database cache warmup...');
    
    try {
      // Warm up fantasy relevant players by position
      const positions: Position[] = ['QB', 'RB', 'WR', 'TE'];
      const warmupPromises = positions.map(position => 
        this.getOptimizedPlayers({
          position,
          fantasy_relevant: true,
          status: 'active',
          limit: 50,
          include_team: true,
          useCache: true
        })
      );

      await Promise.allSettled(warmupPromises);
      console.log('✅ Database cache warmup completed');
    } catch (error) {
      console.error('Database cache warmup failed:', error);
    }
  }
}

// Export singleton instance
export const optimizedDatabaseService = new OptimizedDatabaseService();