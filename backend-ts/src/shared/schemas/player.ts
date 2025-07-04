import { z } from 'zod';

// Core NFL domain schemas - these are the source of truth for types

export const PositionSchema = z.enum(['QB', 'RB', 'WR', 'TE']);
export const ScoringFormatSchema = z.enum(['standard', 'half_ppr', 'ppr']);
export const WeekSchema = z.number().int().min(1).max(18);

export const PlayerStatsSchema = z.object({
  passingYards: z.number().min(0).default(0),
  passingTds: z.number().min(0).default(0),
  passingInterceptions: z.number().min(0).default(0),
  rushingYards: z.number().min(0).default(0),
  rushingTds: z.number().min(0).default(0),
  receivingYards: z.number().min(0).default(0),
  receivingTds: z.number().min(0).default(0),
  receptions: z.number().min(0).default(0),
  targets: z.number().min(0).default(0),
  fumbles: z.number().min(0).default(0),
});

export const PlayerSchema = z.object({
  id: z.string().cuid(),
  name: z.string().min(1),
  position: PositionSchema,
  team: z.string().length(3), // Three-letter team code
  isActive: z.boolean().default(true),
  createdAt: z.date(),
  updatedAt: z.date(),
});

export const PlayerRankingSchema = z.object({
  rank: z.number().int().positive(),
  player: PlayerSchema,
  predictedPoints: z.number().positive(),
  confidence: z.number().min(0).max(1),
  week: WeekSchema,
  scoringFormat: ScoringFormatSchema,
});

export const PlayerPredictionSchema = z.object({
  playerId: z.string().cuid(),
  week: WeekSchema,
  predictedPoints: z.number().positive(),
  confidence: z.number().min(0).max(1),
  features: z.object({
    recentPerformance: z.number(),
    trendDirection: z.number(),
    matchupDifficulty: z.number().min(0).max(1),
    injuryStatus: z.enum(['healthy', 'questionable', 'doubtful', 'out']).default('healthy'),
  }),
  createdAt: z.date(),
});

// API Request/Response schemas
export const GetRankingsParamsSchema = z.object({
  position: PositionSchema,
});

export const GetRankingsQuerySchema = z.object({
  week: WeekSchema.default(1),
  scoring: ScoringFormatSchema.default('half_ppr'),
  limit: z.number().int().min(1).max(50).default(10),
});

export const RankingsResponseSchema = z.object({
  rankings: z.array(PlayerRankingSchema),
  metadata: z.object({
    position: PositionSchema,
    week: WeekSchema,
    scoring: ScoringFormatSchema,
    limit: z.number().int(),
    generatedAt: z.string().datetime(),
    cached: z.boolean(),
    dataSource: z.enum(['cache', 'database', 'ml_engine', 'fallback']).optional(),
    totalPlayersEvaluated: z.number().optional(),
    includeProjections: z.boolean().optional(),
    includeInjuries: z.boolean().optional(),
  }),
});

export const PlayerAnalysisRequestSchema = z.object({
  playerId: z.string().cuid(),
  week: WeekSchema.default(1),
});

export const PlayerAnalysisResponseSchema = z.object({
  player: PlayerSchema,
  prediction: PlayerPredictionSchema,
  recentStats: z.array(PlayerStatsSchema),
  analysis: z.object({
    strengths: z.array(z.string()),
    concerns: z.array(z.string()),
    recommendation: z.enum(['start', 'bench', 'flex', 'avoid']),
  }),
});

export const SystemStatusSchema = z.object({
  status: z.enum(['healthy', 'degraded', 'down']),
  version: z.string(),
  uptime: z.number(),
  database: z.object({
    connected: z.boolean(),
    responseTime: z.number(),
  }),
  cache: z.object({
    connected: z.boolean(),
    hitRate: z.number().min(0).max(1),
  }),
  mlService: z.object({
    available: z.boolean(),
    responseTime: z.number().optional(),
  }),
  timestamp: z.string().datetime(),
});

export const ApiEndpointSchema = z.object({
  path: z.string(),
  method: z.enum(['GET', 'POST', 'PUT', 'DELETE', 'PATCH']),
  description: z.string(),
  status: z.enum(['active', 'beta', 'deprecated']),
});

export const CapabilitySchema = z.object({
  enabled: z.boolean(),
  description: z.string(),
});

export const FeaturesResponseSchema = z.object({
  endpoints: z.array(ApiEndpointSchema),
  version: z.string(),
  capabilities: z.object({
    rankings: CapabilitySchema,
    playerAnalysis: CapabilitySchema,
    injuryAnalysis: CapabilitySchema,
    boomBustAnalysis: CapabilitySchema,
  }),
  documentation: z.object({
    apiDocs: z.string(),
    examples: z.string(),
  }),
});

export const InjuryStatusSchema = z.enum(['healthy', 'questionable', 'doubtful', 'out', 'ir']);
export const RiskLevelSchema = z.enum(['low', 'moderate', 'high', 'critical']);
export const RecommendationSchema = z.enum(['start', 'sit', 'monitor', 'avoid']);

export const BasicInjuryAnalysisSchema = z.object({
  week: WeekSchema,
  injury_analysis: z.object({
    monitoring: z.string(),
    features: z.array(z.string()),
    current_status: z.string(),
  }),
});

export const PlayerInjuryAnalysisSchema = z.object({
  player_info: z.object({
    player_id: z.string(),
    player_name: z.string(),
    position: PositionSchema,
    team: z.string(),
  }),
  injury_status: z.object({
    current_status: InjuryStatusSchema,
    description: z.string().optional(),
    body_part: z.string().optional(),
    week_designation: z.string().optional(),
  }),
  risk_assessment: z.object({
    overall_risk_level: RiskLevelSchema,
    overall_risk_probability: z.number().min(0).max(1),
    risk_factors: z.array(z.string()),
    injury_prone_rating: z.number().min(0).max(10),
    confidence_score: z.number().min(0).max(1),
  }),
  impact_analysis: z.object({
    fantasy_impact_score: z.number().min(0).max(10),
    recommended_action: RecommendationSchema,
    confidence: z.number().min(0).max(1),
  }),
});

export const BasicBoomBustAnalysisSchema = z.object({
  position: PositionSchema,
  week: WeekSchema,
  boom_bust_analysis: z.object({
    volatility_modeling: z.string(),
    projections: z.object({
      floor: z.string(),
      base: z.string(),
      ceiling: z.string(),
    }),
    features: z.array(z.string()),
  }),
});

export const PlayerBoomBustAnalysisSchema = z.object({
  player_info: z.object({
    player_id: z.string(),
    player_name: z.string(),
    position: PositionSchema,
    team: z.string(),
    week: WeekSchema,
  }),
  projections: z.object({
    base_projection: z.number().positive(),
    floor_projection: z.number().positive(),
    ceiling_projection: z.number().positive(),
  }),
  probabilities: z.object({
    boom_probability: z.number().min(0).max(1),
    bust_probability: z.number().min(0).max(1),
    normal_probability: z.number().min(0).max(1),
  }),
  analysis_metrics: z.object({
    volatility_score: z.number().min(0).max(1),
    consistency_score: z.number().min(0).max(1),
    upside_potential: z.number().positive(),
    downside_risk: z.number().positive(),
  }),
  contributing_factors: z.object({
    injury_risk_factor: z.number().min(0).max(1),
    matchup_factor: z.number().min(-0.5).max(0.5),
    usage_stability_factor: z.number().min(0).max(1),
    weather_factor: z.number().min(0).max(1).optional(),
    game_script_factor: z.number().min(-0.3).max(0.3).optional(),
  }),
});

export const BatchBoomBustRequestSchema = z.object({
  players: z.array(z.object({
    player_id: z.string(),
    base_projection: z.number().positive(),
  })),
  week: WeekSchema,
  scoring_format: ScoringFormatSchema.optional(),
});

export const BatchBoomBustResponseSchema = z.object({
  results: z.array(PlayerBoomBustAnalysisSchema),
});

// Batch rankings schemas
export const BatchRankingsRequestSchema = z.object({
  positions: z.array(PositionSchema).min(1, 'At least one position is required'),
  week: WeekSchema.optional().default(1),
  scoring_format: ScoringFormatSchema.optional().default('half_ppr'),
  limit: z.number().int().min(1).max(100).optional().default(10),
});

export const BatchRankingsResponseSchema = z.object({
  rankings: z.record(PositionSchema, z.array(PlayerRankingSchema)),
  metadata: z.object({
    positions: z.array(PositionSchema),
    week: WeekSchema,
    scoring: ScoringFormatSchema,
    limit: z.number().int(),
    generatedAt: z.string(),
    cached: z.boolean(),
  }),
});

// Matchup analysis schemas
export const WeatherConditionsSchema = z.object({
  temperature: z.number().optional(),
  wind_speed: z.number().min(0).optional(),
  precipitation: z.enum(['none', 'light', 'moderate', 'heavy']).optional(),
  dome_game: z.boolean(),
});

export const GameInfoSchema = z.object({
  kickoff_time: z.string(),
  weather_conditions: WeatherConditionsSchema,
  vegas_line: z.number().optional(),
});

export const PaceAnalysisSchema = z.object({
  expected_plays: z.number().positive(),
  pace_rating: z.enum(['slow', 'average', 'fast']),
});

export const ScoringEnvironmentSchema = z.object({
  total_points_projection: z.number().positive(),
  environment_rating: z.enum(['low', 'moderate', 'high']),
});

export const MatchupAnalysisSchema = z.object({
  pace_analysis: PaceAnalysisSchema,
  scoring_environment: ScoringEnvironmentSchema,
  weather_impact: z.enum(['minimal', 'moderate', 'significant']),
  key_factors: z.array(z.string()),
});

export const GameMatchupSchema = z.object({
  home_team: z.string().length(3),
  away_team: z.string().length(3),
  game_info: GameInfoSchema,
  analysis: MatchupAnalysisSchema,
});

export const WeekMatchupsResponseSchema = z.object({
  week: WeekSchema,
  matchups: z.array(GameMatchupSchema),
  metadata: z.object({
    total_games: z.number(),
    analysis_date: z.string(),
    week: WeekSchema,
  }),
});

export const AdvantageSchema = z.enum(['strong_disadvantage', 'disadvantage', 'neutral', 'advantage', 'strong_advantage']);
export const DefenseStrengthSchema = z.enum(['poor', 'below_average', 'average', 'above_average', 'elite']);

export const OffensiveMatchupSchema = z.object({
  pass_game_advantage: AdvantageSchema,
  run_game_advantage: AdvantageSchema,
  red_zone_efficiency: z.number().min(0).max(1),
});

export const DefensiveMatchupSchema = z.object({
  pass_defense_strength: DefenseStrengthSchema,
  run_defense_strength: DefenseStrengthSchema,
  turnover_expectation: z.number().min(0),
});

export const SpecialTeamsSchema = z.object({
  field_goal_advantage: AdvantageSchema,
  return_game_impact: z.enum(['minimal', 'moderate', 'significant']),
});

export const OutlookRatingSchema = z.enum(['poor', 'below_average', 'average', 'above_average', 'excellent']);

export const PositionOutlookSchema = z.object({
  outlook_rating: OutlookRatingSchema,
  key_factors: z.array(z.string()),
});

export const FantasyImplicationsSchema = z.object({
  key_players: z.array(z.string()),
  position_outlooks: z.object({
    QB: PositionOutlookSchema,
    RB: PositionOutlookSchema,
    WR: PositionOutlookSchema,
    TE: PositionOutlookSchema,
  }),
});

export const TeamMatchupAnalysisSchema = z.object({
  team_info: z.object({
    team_code: z.string().length(3),
    team_name: z.string(),
    home_away: z.enum(['home', 'away']),
  }),
  opponent_info: z.object({
    team_code: z.string().length(3),
    team_name: z.string(),
  }),
  matchup_analysis: z.object({
    offensive_matchup: OffensiveMatchupSchema,
    defensive_matchup: DefensiveMatchupSchema,
    special_teams: SpecialTeamsSchema,
  }),
  fantasy_implications: FantasyImplicationsSchema,
});

export const MatchupRatingSchema = z.enum(['avoid', 'poor', 'below_average', 'average', 'above_average', 'smash_spot']);
export const CoverageSchema = z.enum(['man', 'zone', 'mixed']);
export const CompetitionLevelSchema = z.enum(['low', 'moderate', 'high']);

export const PlayerMatchupDetailsSchema = z.object({
  opponent_defense_rank: z.number().int().min(1).max(32),
  target_share_opportunity: z.number().min(0).max(1),
  game_script_projection: z.enum(['negative', 'neutral', 'positive']),
  coverage_tendency: CoverageSchema.optional(),
  target_competition: CompetitionLevelSchema.optional(),
});

export const PerformanceOutlookSchema = z.object({
  ceiling_multiplier: z.number().positive(),
  floor_multiplier: z.number().positive(),
  matchup_rating: MatchupRatingSchema,
});

export const PlayerMatchupAnalysisSchema = z.object({
  player_info: z.object({
    player_id: z.string(),
    position: PositionSchema,
    team: z.string().length(3),
  }),
  matchup_details: PlayerMatchupDetailsSchema,
  performance_outlook: PerformanceOutlookSchema,
  key_matchup_factors: z.array(z.string()),
});

// Derive TypeScript types from schemas
export type Position = z.infer<typeof PositionSchema>;
export type ScoringFormat = z.infer<typeof ScoringFormatSchema>;
export type Week = z.infer<typeof WeekSchema>;
export type PlayerStats = z.infer<typeof PlayerStatsSchema>;
export type Player = z.infer<typeof PlayerSchema>;
export type PlayerRanking = z.infer<typeof PlayerRankingSchema>;
export type PlayerPrediction = z.infer<typeof PlayerPredictionSchema>;
export type GetRankingsParams = z.infer<typeof GetRankingsParamsSchema>;
export type GetRankingsQuery = z.infer<typeof GetRankingsQuerySchema>;
export type RankingsResponse = z.infer<typeof RankingsResponseSchema>;
export type PlayerAnalysisRequest = z.infer<typeof PlayerAnalysisRequestSchema>;
export type PlayerAnalysisResponse = z.infer<typeof PlayerAnalysisResponseSchema>;
export type SystemStatus = z.infer<typeof SystemStatusSchema>;
export type ApiEndpoint = z.infer<typeof ApiEndpointSchema>;
export type Capability = z.infer<typeof CapabilitySchema>;
export type FeaturesResponse = z.infer<typeof FeaturesResponseSchema>;
export type InjuryStatus = z.infer<typeof InjuryStatusSchema>;
export type RiskLevel = z.infer<typeof RiskLevelSchema>;
export type Recommendation = z.infer<typeof RecommendationSchema>;
export type BasicInjuryAnalysis = z.infer<typeof BasicInjuryAnalysisSchema>;
export type PlayerInjuryAnalysis = z.infer<typeof PlayerInjuryAnalysisSchema>;
export type BasicBoomBustAnalysis = z.infer<typeof BasicBoomBustAnalysisSchema>;
export type PlayerBoomBustAnalysis = z.infer<typeof PlayerBoomBustAnalysisSchema>;
export type BatchBoomBustRequest = z.infer<typeof BatchBoomBustRequestSchema>;
export type BatchBoomBustResponse = z.infer<typeof BatchBoomBustResponseSchema>;
export type BatchRankingsRequest = z.infer<typeof BatchRankingsRequestSchema>;
export type BatchRankingsResponse = z.infer<typeof BatchRankingsResponseSchema>;
export type WeatherConditions = z.infer<typeof WeatherConditionsSchema>;
export type GameInfo = z.infer<typeof GameInfoSchema>;
export type PaceAnalysis = z.infer<typeof PaceAnalysisSchema>;
export type ScoringEnvironment = z.infer<typeof ScoringEnvironmentSchema>;
export type MatchupAnalysis = z.infer<typeof MatchupAnalysisSchema>;
export type GameMatchup = z.infer<typeof GameMatchupSchema>;
export type WeekMatchupsResponse = z.infer<typeof WeekMatchupsResponseSchema>;
export type Advantage = z.infer<typeof AdvantageSchema>;
export type DefenseStrength = z.infer<typeof DefenseStrengthSchema>;
export type OffensiveMatchup = z.infer<typeof OffensiveMatchupSchema>;
export type DefensiveMatchup = z.infer<typeof DefensiveMatchupSchema>;
export type SpecialTeams = z.infer<typeof SpecialTeamsSchema>;
export type OutlookRating = z.infer<typeof OutlookRatingSchema>;
export type PositionOutlook = z.infer<typeof PositionOutlookSchema>;
export type FantasyImplications = z.infer<typeof FantasyImplicationsSchema>;
export type TeamMatchupAnalysis = z.infer<typeof TeamMatchupAnalysisSchema>;
export type MatchupRating = z.infer<typeof MatchupRatingSchema>;
export type Coverage = z.infer<typeof CoverageSchema>;
export type CompetitionLevel = z.infer<typeof CompetitionLevelSchema>;
export type PlayerMatchupDetails = z.infer<typeof PlayerMatchupDetailsSchema>;
export type PerformanceOutlook = z.infer<typeof PerformanceOutlookSchema>;
export type PlayerMatchupAnalysis = z.infer<typeof PlayerMatchupAnalysisSchema>;

// ML Projections schemas
export const PlayerFeaturesSchema = z.object({
  recent_performance: z.number().min(0),
  trend_direction: z.number().min(-1).max(1),
  matchup_difficulty: z.number().min(0).max(1),
  injury_status: z.enum(['healthy', 'questionable', 'doubtful', 'out']),
});

export const ModelAccuracyMetricsSchema = z.object({
  rmse: z.number().positive(),
  mae: z.number().positive(),
  r2_score: z.number().min(0).max(1),
});

export const ModelDetailsSchema = z.object({
  model_version: z.string(),
  training_date: z.string(),
  accuracy_metrics: ModelAccuracyMetricsSchema,
});

export const PredictionRangeSchema = z.object({
  floor: z.number().positive(),
  ceiling: z.number().positive(),
});

export const PlayerProjectionSchema = z.object({
  player_id: z.string(),
  player_name: z.string(),
  position: PositionSchema,
  team: z.string().length(3),
  predicted_points: z.number().positive(),
  confidence: z.number().min(0).max(1),
  features: PlayerFeaturesSchema,
  model_version: z.string(),
});

export const FeatureImportanceSchema = z.object({
  recent_performance: z.number().min(0).max(1),
  matchup_difficulty: z.number().min(0).max(1),
  injury_status: z.number().min(0).max(1),
  weather_conditions: z.number().min(0).max(1),
});

export const ProjectionsResponseSchema = z.object({
  week: WeekSchema,
  projections: z.array(PlayerProjectionSchema),
  metadata: z.object({
    total_players: z.number().int(),
    model_updated_at: z.string(),
    feature_importance: FeatureImportanceSchema,
    position: PositionSchema.optional(),
    week: WeekSchema,
  }),
});

export const SeasonTrendsSchema = z.object({
  passing_yards_trend: z.number().optional(),
  passing_td_trend: z.number().optional(),
  rushing_yards_trend: z.number().optional(),
  rushing_td_trend: z.number().optional(),
  receiving_yards_trend: z.number().optional(),
  receiving_td_trend: z.number().optional(),
});

export const FeatureBreakdownSchema = z.object({
  recent_games: z.array(z.object({
    week: WeekSchema,
    fantasy_points: z.number(),
    opponent: z.string().length(3),
  })),
  season_trends: SeasonTrendsSchema,
  matchup_analysis: z.object({
    difficulty_score: z.number().min(0).max(1),
    key_factors: z.array(z.string()),
  }),
});

export const PlayerProjectionDetailSchema = z.object({
  player_info: z.object({
    player_id: z.string(),
    position: PositionSchema,
    team: z.string().length(3),
  }),
  prediction: z.object({
    predicted_points: z.number().positive(),
    confidence: z.number().min(0).max(1),
    range: PredictionRangeSchema,
  }),
  model_details: ModelDetailsSchema,
  feature_breakdown: FeatureBreakdownSchema,
});

export const BatchProjectionsRequestSchema = z.object({
  player_ids: z.array(z.string()),
  week: WeekSchema,
  scoring_format: ScoringFormatSchema.optional().default('half_ppr'),
});

export const BatchProjectionsResponseSchema = z.object({
  projections: z.array(PlayerProjectionDetailSchema),
});

export type PlayerFeatures = z.infer<typeof PlayerFeaturesSchema>;
export type ModelAccuracyMetrics = z.infer<typeof ModelAccuracyMetricsSchema>;
export type ModelDetails = z.infer<typeof ModelDetailsSchema>;
export type PredictionRange = z.infer<typeof PredictionRangeSchema>;
export type PlayerProjection = z.infer<typeof PlayerProjectionSchema>;
export type FeatureImportance = z.infer<typeof FeatureImportanceSchema>;
export type ProjectionsResponse = z.infer<typeof ProjectionsResponseSchema>;
export type SeasonTrends = z.infer<typeof SeasonTrendsSchema>;
export type FeatureBreakdown = z.infer<typeof FeatureBreakdownSchema>;
export type PlayerProjectionDetail = z.infer<typeof PlayerProjectionDetailSchema>;
export type BatchProjectionsRequest = z.infer<typeof BatchProjectionsRequestSchema>;
export type BatchProjectionsResponse = z.infer<typeof BatchProjectionsResponseSchema>;