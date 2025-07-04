// Elite NFL Analysis API - Enhanced endpoints with Django data integration
// Combines TypeScript ML projections with Django's comprehensive database

import { Router } from 'express';
import { unifiedMLEngine } from '../../services/unified-ml-engine';
import { databaseService } from '../../services/database';
import type { Position, Week, ScoringFormat } from '../../shared/schemas/player';

export const eliteRouter = Router();

// ==============================================================================
// ELITE PROJECTIONS ENDPOINT
// ==============================================================================

eliteRouter.get('/projections', async (req, res) => {
  try {
    const {
      position,
      week = '1',
      season = '2024',
      scoring_format = 'half_ppr',
      limit = '20',
      include_bench = 'false',
      min_confidence = '0.3'
    } = req.query;

    const options: any = {
      week: parseInt(week as string) as Week,
      season: parseInt(season as string),
      scoring_format: scoring_format as ScoringFormat,
      limit: parseInt(limit as string),
      include_bench_players: include_bench === 'true',
      min_confidence: parseFloat(min_confidence as string)
    };
    
    if (position && ['QB', 'RB', 'WR', 'TE'].includes(position as string)) {
      options.position = position as Position;
    }

    // Use fast predictions if Python ML service is available, fallback to full ensemble
    const projections = await unifiedMLEngine.getFastPredictions(options);

    res.json({
      success: true,
      data: projections,
      elite_features: {
        ensemble_modeling: true,
        django_data_integration: true,
        real_time_factors: true,
        confidence_intervals: true,
        volatility_analysis: true,
        depth_chart_analysis: true,
        injury_risk_assessment: true,
        transaction_monitoring: true
      }
    });
  } catch (error) {
    console.error('Elite projections error:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to generate elite projections',
      details: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

// ==============================================================================
// ELITE DATABASE STATS ENDPOINT
// ==============================================================================

eliteRouter.get('/database-stats', async (_req, res) => {
  try {
    const stats = await databaseService.getDatabaseStats();
    const healthCheck = await databaseService.healthCheck();

    res.json({
      success: true,
      data: {
        database_health: healthCheck ? 'healthy' : 'unhealthy',
        statistics: stats,
        capabilities: {
          total_nfl_players: stats.total_players,
          real_time_transactions: stats.total_transactions,
          injury_monitoring: stats.total_injury_reports,
          season_statistics: stats.total_stats_records,
          data_richness: 'comprehensive'
        }
      },
      metadata: {
        django_migration_status: 'active',
        prisma_integration: 'enabled',
        data_sources: ['django_database', 'real_time_monitoring'],
        last_updated: stats.last_updated
      }
    });
  } catch (error) {
    console.error('Elite database stats error:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to retrieve database statistics',
      details: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});