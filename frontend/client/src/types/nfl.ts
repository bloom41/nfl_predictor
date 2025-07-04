// NFL Assistant TypeScript Type Definitions

export interface Player {
  id: string;
  name: string;
  team: string;
  position: 'QB' | 'RB' | 'WR' | 'TE' | 'K' | 'DST';
  bye_week?: number;
  fantasy_relevant?: boolean;
  depth_chart_position?: number;
  status?: 'active' | 'injured' | 'questionable' | 'doubtful' | 'out' | 'ir';
}

export interface PlayerRanking {
  rank: number;
  player: Player;
  predictedPoints: number;
  confidence: number;
  week: number;
  scoringFormat: ScoringFormat;
}

export interface RankingsResponse {
  rankings: PlayerRanking[];
  metadata: {
    position: string;
    week: number;
    scoring: string;
    limit: number;
    generatedAt: string;
    cached: boolean;
  };
}

export interface PlayerAnalysis {
  player: Player;
  week_projection: {
    predicted_points: number;
    confidence: number;
    floor: number;
    ceiling: number;
  };
  recent_performance: {
    last_5_games: number[];
    trend: 'up' | 'down' | 'stable';
    consistency_score: number;
  };
  matchup_analysis: {
    opponent: string;
    defense_rank: number;
    projected_game_script: string;
    weather_impact?: string;
  };
  injury_status: {
    status: string;
    impact_score: number;
    return_timeline?: string;
  };
  news_impact: {
    recent_news: string[];
    sentiment_score: number;
  };
}

export interface SystemStatus {
  status: 'operational' | 'degraded' | 'down';
  services: {
    express: {
      status: string;
      uptime: number;
      version: string;
      memory_usage?: any;
    };
    django: {
      status: string;
      database_status: string;
      elite_features: {
        [key: string]: boolean;
      };
      player_count: number;
      last_update: string;
    };
  };
  performance_metrics?: {
    response_time: number;
    error_rate: number;
    throughput: number;
  };
}

export interface BatchRankingsRequest {
  positions: string[];
  week?: number;
  scoring_format?: ScoringFormat;
  limit?: number;
}

export interface BatchRankingsResponse {
  rankings: {
    [position: string]: PlayerRanking[];
  };
  metadata: {
    positions: string[];
    week: number;
    scoring: string;
    limit: number;
    generatedAt: string;
    cached: boolean;
  };
}

export interface SearchResult {
  players: Player[];
  total_count: number;
  query: string;
  filters_applied: {
    position?: string;
    team?: string;
  };
}

export interface NewsItem {
  id: string;
  headline: string;
  description: string;
  url: string;
  published: string;
  source: string;
  importance: 'high' | 'medium' | 'low';
  players_affected: string[];
  categories: string[];
}

export interface ApiError {
  error: string;
  message?: string;
  details?: string;
  status?: number;
}

// Request/Response interfaces for API calls
export interface ApiResponse<T> {
  data?: T;
  error?: ApiError;
  loading: boolean;
}

// Fantasy football scoring formats
export type ScoringFormat = 'standard' | 'half_ppr' | 'ppr';

// NFL positions
export type Position = 'QB' | 'RB' | 'WR' | 'TE' | 'K' | 'DST';

// Week range for NFL season
export type Week = 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18;

// Team abbreviations
export type Team = 
  | 'ARI' | 'ATL' | 'BAL' | 'BUF' | 'CAR' | 'CHI' | 'CIN' | 'CLE' 
  | 'DAL' | 'DEN' | 'DET' | 'GB' | 'HOU' | 'IND' | 'JAX' | 'KC' 
  | 'LV' | 'LAC' | 'LAR' | 'MIA' | 'MIN' | 'NE' | 'NO' | 'NYG' 
  | 'NYJ' | 'PHI' | 'PIT' | 'SF' | 'SEA' | 'TB' | 'TEN' | 'WAS';

// Advanced Analysis Interfaces
export interface MLProjectionsResponse {
  week: number;
  projections: PlayerProjection[];
  metadata: {
    total_players: number;
    model_updated_at: string;
    feature_importance: FeatureImportance;
    position?: string;
    week: number;
  };
}

export interface PlayerProjection {
  player_id: string;
  player_name: string;
  position: Position;
  team: string;
  predicted_points: number;
  confidence: number;
  features: PlayerFeatures;
  model_version: string;
}

export interface PlayerFeatures {
  recent_performance: number;
  trend_direction: number;
  matchup_difficulty: number;
  injury_status: 'healthy' | 'questionable' | 'doubtful' | 'out';
}

export interface FeatureImportance {
  recent_performance: number;
  matchup_difficulty: number;
  injury_status: number;
  weather_conditions: number;
}

export interface InjuryAnalysisResponse {
  week: number;
  injury_analysis: {
    monitoring: string;
    features: string[];
    current_status: string;
  };
}

export interface BoomBustAnalysisResponse {
  position: string;
  week: number;
  boom_bust_analysis: {
    volatility_modeling: string;
    projections: {
      floor: string;
      base: string;
      ceiling: string;
    };
    features: string[];
  };
}

export interface MatchupAnalysisResponse {
  week: number;
  matchups: GameMatchup[];
  metadata: {
    total_games: number;
    analysis_date: string;
    week: number;
  };
}

export interface GameMatchup {
  home_team: string;
  away_team: string;
  game_info: {
    kickoff_time: string;
    weather_conditions: {
      temperature: number;
      wind_speed: number;
      precipitation: string;
      dome_game: boolean;
    };
    vegas_line: number;
  };
  analysis: {
    pace_analysis: {
      expected_plays: number;
      pace_rating: string;
    };
    scoring_environment: {
      total_points_projection: number;
      environment_rating: string;
    };
    weather_impact: string;
    key_factors: string[];
  };
}