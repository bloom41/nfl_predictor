// Features service - minimal implementation to make tests pass

import { FeaturesResponse, ApiEndpoint } from '../../shared/schemas/player';
import packageJson from '../../../package.json';

class FeaturesService {
  async getFeatures(): Promise<FeaturesResponse> {
    return {
      endpoints: this.getAvailableEndpoints(),
      version: packageJson.version,
      capabilities: this.getCapabilities(),
      documentation: this.getDocumentation(),
    };
  }

  private getAvailableEndpoints(): ApiEndpoint[] {
    return [
      {
        path: '/api/rankings/:position',
        method: 'GET',
        description: 'Get player rankings by position with optional filters for week, scoring format, and limit',
        status: 'active',
      },
      {
        path: '/api/player/:playerId/analysis',
        method: 'GET', 
        description: 'Get detailed analysis for a specific player including predictions and recommendations',
        status: 'active',
      },
      {
        path: '/api/status',
        method: 'GET',
        description: 'Get system health status and service availability',
        status: 'active',
      },
      {
        path: '/api/features',
        method: 'GET',
        description: 'Get available API features and capabilities',
        status: 'active',
      },
      {
        path: '/api/injury',
        method: 'GET',
        description: 'Get injury analysis and monitoring status by week',
        status: 'active',
      },
      {
        path: '/api/injury/player/:playerId',
        method: 'GET',
        description: 'Get detailed injury analysis for a specific player',
        status: 'active',
      },
      {
        path: '/api/boom-bust',
        method: 'GET',
        description: 'Get boom-bust analysis with position-specific volatility modeling',
        status: 'active',
      },
      {
        path: '/api/boom-bust/player/:playerId',
        method: 'GET',
        description: 'Get detailed boom-bust analysis for a specific player with projections',
        status: 'active',
      },
      {
        path: '/api/boom-bust/batch',
        method: 'POST',
        description: 'Get boom-bust analysis for multiple players in a single request',
        status: 'active',
      },
      {
        path: '/api/batch-rankings',
        method: 'POST',
        description: 'Get rankings for multiple positions in a single request for performance optimization',
        status: 'active',
      },
      {
        path: '/api/matchup-analysis',
        method: 'GET',
        description: 'Get comprehensive matchup analysis for all games in a week',
        status: 'active',
      },
      {
        path: '/api/matchup-analysis/team/:teamCode',
        method: 'GET',
        description: 'Get detailed team-specific matchup analysis with fantasy implications',
        status: 'active',
      },
      {
        path: '/api/matchup-analysis/player/:playerId',
        method: 'GET',
        description: 'Get player-specific matchup analysis with performance outlook',
        status: 'active',
      },
      {
        path: '/api/projections',
        method: 'GET',
        description: 'Get ML-powered fantasy point projections with confidence intervals',
        status: 'active',
      },
      {
        path: '/api/projections/player/:playerId',
        method: 'GET',
        description: 'Get detailed ML projection for specific player with feature breakdown',
        status: 'active',
      },
      {
        path: '/api/projections/batch',
        method: 'POST',
        description: 'Get ML projections for multiple players efficiently',
        status: 'active',
      },
    ];
  }

  private getCapabilities() {
    return {
      rankings: {
        enabled: true,
        description: 'Player rankings by position with ML-powered projections',
      },
      playerAnalysis: {
        enabled: true,
        description: 'Individual player analysis with detailed recommendations',
      },
      injuryAnalysis: {
        enabled: true,
        description: 'Injury impact analysis and risk assessment with player-specific data',
      },
      boomBustAnalysis: {
        enabled: true,
        description: 'Boom/bust probability analysis with position-specific volatility modeling',
      },
      batchRankings: {
        enabled: true,
        description: 'Batch rankings endpoint for performance optimization across multiple positions',
      },
      matchupAnalysis: {
        enabled: true,
        description: 'Comprehensive game-specific insights with weather, pace, and fantasy implications',
      },
      mlProjections: {
        enabled: true,
        description: 'Machine learning-powered fantasy point predictions with confidence intervals and feature importance',
      },
    };
  }

  private getDocumentation() {
    return {
      apiDocs: '/api/docs',
      examples: '/api/examples',
    };
  }
}

export const featuresService = new FeaturesService();