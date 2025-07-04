// Database Service Layer - Prisma integration for Django data access
// Provides TypeScript interface to Django NFL Assistant database

import { PrismaClient } from '@prisma/client';
import type {
  CompleteNFLPlayer,
  PlayerTransaction,
  InjuryReport,
  DepthChart,
  SeasonStats,
  NFLTeam
} from '@prisma/client';

// Type aliases for database string fields
export type Position = 'QB' | 'RB' | 'WR' | 'TE';
export type PlayerStatus = 'active' | 'injured' | 'suspended' | 'practice_squad' | 'ir' | 'retired' | 'free_agent';
export type InjuryStatus = 'healthy' | 'questionable' | 'doubtful' | 'out' | 'ir';

// Enhanced types for complex queries
export type PlayerWithRelations = CompleteNFLPlayer & {
  team_ref: NFLTeam;
  transactions: PlayerTransaction[];
  injury_reports: InjuryReport[];
  season_stats: SeasonStats[];
  depth_charts: DepthChart[];
};

export type PlayerQueryOptions = {
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
};

export type TransactionQueryOptions = {
  player_id?: string;
  transaction_type?: string;
  from_date?: Date;
  to_date?: Date;
  team?: string;
  limit?: number;
};

class DatabaseService {
  private prisma: PrismaClient;

  constructor() {
    try {
      this.prisma = new PrismaClient({
        log: ['query', 'info', 'warn', 'error'],
      });
    } catch (error) {
      console.warn('Prisma client initialization failed - using fallback mode:', error);
      // Create a mock prisma client that will throw errors to trigger fallback behavior
      this.prisma = null as any;
    }
  }

  private async safePrismaCall<T>(operation: () => Promise<T>, fallback: T): Promise<T> {
    try {
      if (!this.prisma) {
        throw new Error('Database not available');
      }
      return await operation();
    } catch (error) {
      console.warn('Database operation failed, using fallback:', error);
      return fallback;
    }
  }

  // ==============================================================================
  // PLAYER QUERIES
  // ==============================================================================

  async getPlayers(options: PlayerQueryOptions = {}): Promise<PlayerWithRelations[]> {
    return this.safePrismaCall(async () => {
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
      limit = 100
    } = options;

    const where: any = {
      position: { in: ['QB', 'RB', 'WR', 'TE'] } // Filter out FB and other positions
    };
    
    if (position) where.position = position;
    if (team) where.team_id = team;
    if (fantasy_relevant !== undefined) where.fantasy_relevant = fantasy_relevant;
    if (status) where.status = status;

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
      include.injury_reports = week ? 
        { where: { week, season }, orderBy: { date_reported: 'desc' } } :
        { orderBy: { date_reported: 'desc' }, take: 5 };
    }

    if (include_stats) {
      include.season_stats = week ?
        { where: { week, season } } :
        { where: { season }, orderBy: { week: 'desc' } };
    }

    if (include_depth_chart) {
      include.depth_charts = week ?
        { where: { week, season }, orderBy: { depth_order: 'asc' } } :
        { where: { season }, orderBy: { week: 'desc', depth_order: 'asc' }, take: 1 };
    }

    return this.prisma.completeNFLPlayer.findMany({
      where,
      include,
      orderBy: [
        { fantasy_relevant: 'desc' },
        { depth_chart_position: 'asc' },
        { full_name: 'asc' }
      ],
      take: limit
    }) as any;
    }, []); // Return empty array as fallback
  }

  async getPlayerById(playerId: string, options: PlayerQueryOptions = {}): Promise<PlayerWithRelations | null> {
    const {
      week,
      season = 2024,
      include_transactions = true,
      include_injuries = true,
      include_stats = true,
      include_depth_chart = true
    } = options;

    const include: any = {
      team_ref: true
    };

    if (include_transactions) {
      include.transactions = {
        orderBy: { transaction_date: 'desc' },
        take: 20
      };
    }

    if (include_injuries) {
      include.injury_reports = {
        where: { season },
        orderBy: { date_reported: 'desc' },
        take: 10
      };
    }

    if (include_stats) {
      include.season_stats = week ?
        { where: { week, season } } :
        { where: { season }, orderBy: { week: 'desc' } };
    }

    if (include_depth_chart) {
      include.depth_charts = week ?
        { where: { week, season } } :
        { where: { season }, orderBy: { week: 'desc' }, take: 5 };
    }

    if (!this.prisma) {
      throw new Error('Database not available');
    }

    return this.prisma.completeNFLPlayer.findUnique({
      where: { player_id: playerId },
      include
    }) as any;
  }

  async getFantasyRelevantPlayers(position?: Position, limit = 50): Promise<PlayerWithRelations[]> {
    const queryOptions: any = {
      fantasy_relevant: true,
      status: 'active',
      include_injuries: true,
      include_depth_chart: true,
      limit
    };
    if (position) {
      queryOptions.position = position;
    }
    return this.getPlayers(queryOptions);
  }

  async getPlayerByName(playerName: string, options: PlayerQueryOptions = {}): Promise<PlayerWithRelations | null> {
    try {
      return await this.prisma.completeNFLPlayer.findFirst({
        where: {
          full_name: {
            contains: playerName,
            mode: 'insensitive'
          }
        },
        include: {
          team_ref: options.include_team || false,
          transactions: options.include_transactions ? {
            orderBy: { transaction_date: 'desc' },
            take: 5
          } : false,
          season_stats: options.include_stats ? {
            where: { 
              season: options.season || 2024,
              ...(options.week && { week: options.week })
            },
            orderBy: { week: 'desc' }
          } : false,
          depth_charts: options.include_depth_chart ? {
            where: {
              season: options.season || 2024,
              ...(options.week && { week: options.week })
            },
            orderBy: { depth_order: 'asc' }
          } : false
        }
      }) as PlayerWithRelations | null;
    } catch (error) {
      console.error('Error finding player by name:', error);
      return null;
    }
  }

  // ==============================================================================
  // TRANSACTION QUERIES
  // ==============================================================================

  async getRecentTransactions(options: TransactionQueryOptions = {}): Promise<PlayerTransaction[]> {
    const {
      player_id,
      transaction_type,
      from_date,
      to_date,
      team,
      limit = 50
    } = options;

    const where: any = {};
    
    if (player_id) {
      const numericPlayerId = parseInt(player_id, 10);
      if (!isNaN(numericPlayerId)) {
        where.player_id = numericPlayerId;
      }
    }
    if (transaction_type) where.transaction_type = transaction_type;
    if (team) {
      where.OR = [
        { from_team_id: team },
        { to_team_id: team }
      ];
    }
    if (from_date || to_date) {
      where.transaction_date = {};
      if (from_date) where.transaction_date.gte = from_date;
      if (to_date) where.transaction_date.lte = to_date;
    }

    if (!this.prisma) {
      throw new Error('Database not available');
    }

    return this.prisma.playerTransaction.findMany({
      where,
      include: {
        player: true,
        from_team_ref: true,
        to_team_ref: true
      },
      orderBy: { transaction_date: 'desc' },
      take: limit
    });
  }

  async getTransactionsLastNDays(days: number): Promise<PlayerTransaction[]> {
    const fromDate = new Date();
    fromDate.setDate(fromDate.getDate() - days);

    return this.getRecentTransactions({
      from_date: fromDate,
      limit: 100
    });
  }

  // ==============================================================================
  // INJURY QUERIES
  // ==============================================================================

  async getInjuryReports(week?: number, season = 2024): Promise<InjuryReport[]> {
    const where: any = { season };
    if (week) where.week = week;

    return this.prisma.injuryReport.findMany({
      where,
      orderBy: { date_reported: 'desc' }
    });
  }

  async getPlayerInjuryHistory(playerId: string, season = 2024): Promise<InjuryReport[]> {
    // Convert string playerId to integer (database uses integer IDs)
    const numericPlayerId = parseInt(playerId, 10);
    if (isNaN(numericPlayerId)) {
      return [];
    }
    
    return this.prisma.injuryReport.findMany({
      where: {
        player_id: numericPlayerId,
        season
      },
      orderBy: { date_reported: 'desc' }
    });
  }

  async getInjuredPlayers(week?: number, season = 2024): Promise<InjuryReport[]> {
    const where: any = {
      season,
      injury_status: {
        in: ['questionable', 'doubtful', 'out', 'ir']
      }
    };
    if (week) where.week = week;

    return this.prisma.injuryReport.findMany({
      where,
      orderBy: { date_reported: 'desc' }
    });
  }

  // ==============================================================================
  // DEPTH CHART QUERIES
  // ==============================================================================

  async getDepthChart(team: string, position?: Position, week?: number, season = 2024): Promise<DepthChart[]> {
    const where: any = { team_id: team, season };
    if (position) where.position = position;
    if (week) where.week = week;

    return this.prisma.depthChart.findMany({
      where,
      include: {
        player: true,
        team_ref: true
      },
      orderBy: [
        { position: 'asc' },
        { depth_order: 'asc' }
      ]
    });
  }

  async getPlayerDepthPosition(playerId: string, week?: number, season = 2024): Promise<DepthChart | null> {
    // Convert string playerId to integer (database uses integer IDs)
    const numericPlayerId = parseInt(playerId, 10);
    if (isNaN(numericPlayerId)) {
      return null;
    }
    
    const where: any = { player_id: numericPlayerId, season };
    if (week) where.week = week;

    return this.prisma.depthChart.findFirst({
      where,
      include: {
        player: true,
        team_ref: true
      },
      orderBy: { week: 'desc' }
    });
  }

  // ==============================================================================
  // STATISTICS QUERIES
  // ==============================================================================

  async getSeasonStats(playerId: string, season = 2024): Promise<SeasonStats[]> {
    // Convert string playerId to integer (database uses integer IDs)
    const numericPlayerId = parseInt(playerId, 10);
    if (isNaN(numericPlayerId)) {
      return [];
    }
    
    return this.prisma.seasonStats.findMany({
      where: {
        player_id: numericPlayerId,
        season
      },
      include: {
        player: true
      },
      orderBy: { week: 'asc' }
    });
  }

  async getWeekStats(week: number, season = 2024): Promise<SeasonStats[]> {
    const where: any = { week, season };
    
    if (!this.prisma) {
      throw new Error('Database not available');
    }

    const include: any = {
      player: true
    };

    return this.prisma.seasonStats.findMany({
      where,
      include,
      orderBy: { fantasy_points_half_ppr: 'desc' }
    });
  }

  // ==============================================================================
  // TEAM QUERIES
  // ==============================================================================

  async getTeams(): Promise<NFLTeam[]> {
    return this.prisma.nFLTeam.findMany({
      orderBy: [
        { conference: 'asc' },
        { division: 'asc' },
        { city: 'asc' }
      ]
    });
  }

  async getTeamRoster(team: string, position?: Position): Promise<CompleteNFLPlayer[]> {
    const where: any = { 
      team_id: team,
      status: 'active',
      fantasy_relevant: true
    };
    if (position) where.position = position;

    return this.prisma.completeNFLPlayer.findMany({
      where,
      include: {
        team_ref: true
      },
      orderBy: [
        { position: 'asc' },
        { depth_chart_position: 'asc' },
        { full_name: 'asc' }
      ]
    });
  }

  // ==============================================================================
  // ANALYTICS QUERIES
  // ==============================================================================

  async getTopPerformers(position: Position, weeks: number[], season = 2024): Promise<any[]> {
    const stats = await this.prisma.seasonStats.findMany({
      where: {
        season,
        week: { in: weeks },
        player: { position }
      },
      include: {
        player: true
      }
    });

    // Group by player and calculate averages
    const playerStats = new Map();
    
    stats.forEach(stat => {
      const playerId = stat.player_id;
      if (!playerStats.has(playerId)) {
        playerStats.set(playerId, {
          player: stat.player,
          total_points: 0,
          games: 0,
          weeks: []
        });
      }
      
      const playerData = playerStats.get(playerId);
      playerData.total_points += stat.fantasy_points_half_ppr;
      playerData.games += 1;
      playerData.weeks.push(stat.week);
    });

    // Convert to array and calculate averages
    return Array.from(playerStats.values())
      .map(data => ({
        player: data.player,
        avg_points: data.total_points / data.games,
        total_points: data.total_points,
        games_played: data.games,
        weeks_played: data.weeks
      }))
      .sort((a, b) => b.avg_points - a.avg_points);
  }

  // ==============================================================================
  // BATCH OPERATIONS
  // ==============================================================================

  async getPlayersBatch(playerIds: string[], options: PlayerQueryOptions = {}): Promise<PlayerWithRelations[]> {
    return this.prisma.completeNFLPlayer.findMany({
      where: {
        player_id: { in: playerIds }
      },
      include: {
        team_ref: true,
        transactions: options.include_transactions ? {
          orderBy: { transaction_date: 'desc' },
          take: 5
        } : false,
        // Note: injury_reports relation not available in current schema
        // Would need to join manually if needed
        season_stats: options.include_stats ? {
          where: { 
            season: options.season || 2024,
            ...(options.week && { week: options.week })
          },
          orderBy: { week: 'desc' }
        } : false,
        depth_charts: options.include_depth_chart ? {
          where: { 
            season: options.season || 2024,
            ...(options.week && { week: options.week })
          },
          orderBy: { week: 'desc' },
          take: 1
        } : false
      }
    }) as Promise<PlayerWithRelations[]>;
  }

  // ==============================================================================
  // UTILITY METHODS
  // ==============================================================================

  async disconnect(): Promise<void> {
    if (this.prisma) {
      await this.prisma.$disconnect();
    }
  }

  async healthCheck(): Promise<boolean> {
    try {
      if (!this.prisma) {
        return false;
      }
      await this.prisma.$queryRaw`SELECT 1`;
      return true;
    } catch (error) {
      console.error('Database health check failed:', error);
      return false;
    }
  }

  // Get database statistics
  async getDatabaseStats(): Promise<any> {
    try {
      if (!this.prisma) {
        return this.getMockDatabaseStats();
      }

      const [playerCount, transactionCount, injuryCount, statsCount] = await Promise.all([
        this.prisma.completeNFLPlayer.count(),
        this.prisma.playerTransaction.count(),
        this.prisma.injuryReport.count(),
        this.prisma.seasonStats.count()
      ]);

      return {
        total_players: playerCount,
        total_transactions: transactionCount,
        total_injury_reports: injuryCount,
        total_stats_records: statsCount,
        last_updated: new Date().toISOString()
      };
    } catch (error) {
      console.warn('Database not available, returning mock stats:', error);
      return this.getMockDatabaseStats();
    }
  }

  private getMockDatabaseStats(): any {
    return {
      total_players: 3200,
      total_transactions: 1250,
      total_injury_reports: 890,
      total_stats_records: 15600,
      last_updated: new Date().toISOString(),
      note: 'Mock data - Database connection not available'
    };
  }
}

// Export singleton instance
export const databaseService = new DatabaseService();