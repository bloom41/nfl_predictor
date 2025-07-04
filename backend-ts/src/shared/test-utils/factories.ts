// Test data factories following CLAUDE.md guidelines
// These factories provide complete objects with sensible defaults and optional overrides

import { 
  Player, 
  PlayerStats, 
  PlayerRanking, 
  PlayerPrediction, 
  Position, 
  ScoringFormat, 
  Week,
  SystemStatus,
  RankingsResponse 
} from '../schemas/player';

/**
 * Creates mock player data with sensible defaults
 * Always returns complete objects, accepts partial overrides
 */
export const getMockPlayer = (overrides?: Partial<Player>): Player => {
  return {
    id: 'clq1234567890',
    name: 'Test Player',
    position: 'QB',
    team: 'KAN', // 3-character team code
    isActive: true,
    createdAt: new Date('2024-01-01T00:00:00Z'),
    updatedAt: new Date('2024-01-01T00:00:00Z'),
    ...overrides,
  };
};

/**
 * Creates mock player stats with realistic values for testing
 */
export const getMockPlayerStats = (overrides?: Partial<PlayerStats>): PlayerStats => {
  return {
    passingYards: 280,
    passingTds: 2,
    passingInterceptions: 0,
    rushingYards: 15,
    rushingTds: 0,
    receivingYards: 0,
    receivingTds: 0,
    receptions: 0,
    targets: 0,
    fumbles: 0,
    ...overrides,
  };
};

/**
 * Creates mock QB player with appropriate stats
 */
export const getMockQB = (overrides?: Partial<Player>): Player => {
  return getMockPlayer({
    id: 'clq123456qb90',
    position: 'QB',
    name: 'Patrick Mahomes',
    team: 'KAN', // 3-character team code
    ...overrides,
  });
};

/**
 * Creates mock RB player with appropriate stats
 */
export const getMockRB = (overrides?: Partial<Player>): Player => {
  return getMockPlayer({
    id: 'clq123456rb90',
    position: 'RB',
    name: 'Christian McCaffrey',
    team: 'SFO', // 3-character team code
    ...overrides,
  });
};

/**
 * Creates mock WR player with appropriate stats
 */
export const getMockWR = (overrides?: Partial<Player>): Player => {
  return getMockPlayer({
    id: 'clq123456wr90',
    position: 'WR',
    name: 'Tyreek Hill',
    team: 'MIA', // 3-character team code
    ...overrides,
  });
};

/**
 * Creates mock TE player with appropriate stats
 */
export const getMockTE = (overrides?: Partial<Player>): Player => {
  return getMockPlayer({
    id: 'clq123456te90',
    position: 'TE',
    name: 'Travis Kelce',
    team: 'KAN', // 3-character team code
    ...overrides,
  });
};

/**
 * Creates mock player ranking with realistic prediction values
 */
export const getMockPlayerRanking = (overrides?: Partial<PlayerRanking>): PlayerRanking => {
  return {
    rank: 1,
    player: getMockQB(),
    predictedPoints: 22.5,
    confidence: 0.85,
    week: 1,
    scoringFormat: 'half_ppr',
    ...overrides,
  };
};

/**
 * Creates mock player prediction
 */
export const getMockPlayerPrediction = (overrides?: Partial<PlayerPrediction>): PlayerPrediction => {
  return {
    playerId: 'clq1234567890',
    week: 1,
    predictedPoints: 22.5,
    confidence: 0.85,
    features: {
      recentPerformance: 24.2,
      trendDirection: 1.05,
      matchupDifficulty: 0.3,
      injuryStatus: 'healthy',
    },
    createdAt: new Date('2024-01-01T12:00:00Z'),
    ...overrides,
  };
};

/**
 * Creates an array of mock player rankings for testing list endpoints
 */
export const getMockPlayerRankings = (
  count: number = 10,
  position: Position = 'QB',
  overrides?: Partial<PlayerRanking>
): PlayerRanking[] => {
  return Array.from({ length: count }, (_, index) => {
    const rank = index + 1;
    const basePlayer = position === 'QB' ? getMockQB() : 
                     position === 'RB' ? getMockRB() :
                     position === 'WR' ? getMockWR() :
                     getMockTE();
    
    return getMockPlayerRanking({
      rank,
      player: {
        ...basePlayer,
        id: `clq123456789${rank}`,
        name: `${position} Player ${rank}`,
      },
      predictedPoints: 30 - (rank * 1.5), // Decreasing points by rank
      confidence: 0.9 - (rank * 0.02), // Slightly decreasing confidence
      ...overrides,
    });
  });
};

/**
 * Creates mock rankings response with metadata
 */
export const getMockRankingsResponse = (
  overrides?: Partial<RankingsResponse>
): RankingsResponse => {
  return {
    rankings: getMockPlayerRankings(10, 'QB'),
    metadata: {
      position: 'QB',
      week: 1,
      scoring: 'half_ppr',
      limit: 10,
      generatedAt: new Date().toISOString(),
      cached: false,
    },
    ...overrides,
  };
};

/**
 * Creates mock system status for health check testing
 */
export const getMockSystemStatus = (overrides?: Partial<SystemStatus>): SystemStatus => {
  return {
    status: 'healthy',
    version: '1.0.0',
    uptime: 3600,
    database: {
      connected: true,
      responseTime: 5,
    },
    cache: {
      connected: true,
      hitRate: 0.85,
    },
    mlService: {
      available: true,
      responseTime: 150,
    },
    timestamp: new Date().toISOString(),
    ...overrides,
  };
};

/**
 * Creates mock data for different scoring formats
 */
export const getMockScoringFormats = (): ScoringFormat[] => {
  return ['standard', 'half_ppr', 'ppr'];
};

/**
 * Creates mock weeks for testing
 */
export const getMockWeeks = (): Week[] => {
  return Array.from({ length: 18 }, (_, i) => (i + 1) as Week);
};

/**
 * Creates mock team codes
 */
export const getMockTeams = (): string[] => {
  return [
    'KC', 'SF', 'BUF', 'PHI', 'DAL', 'MIA', 'CIN', 'BAL',
    'MIN', 'LAC', 'NYJ', 'DEN', 'SEA', 'JAX', 'GB', 'TEN',
    'LV', 'NE', 'IND', 'HOU', 'PIT', 'CLE', 'ATL', 'TB',
    'NO', 'CAR', 'WAS', 'NYG', 'DET', 'CHI', 'LAR', 'ARI'
  ];
};