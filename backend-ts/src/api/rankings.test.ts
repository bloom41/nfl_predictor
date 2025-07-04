// Test-driven development for Player Rankings API
// Following CLAUDE.md: behavior-driven testing, treating implementation as black box

import request from 'supertest';
import { app } from '../app';
import { 
  getMockQB,
  getMockRB,
  getMockWR
} from '../shared/test-utils/factories';

// This will fail initially - that's the point of TDD!
describe('Player Rankings API', () => {
  // Test the core business behavior: getting QB rankings
  describe('GET /api/rankings/QB', () => {
    it('should return QB rankings for week 1 with default scoring', async () => {
      // This test defines the expected behavior
      const response = await request(app)
        .get('/api/rankings/QB');

      expect(response.status).toBe(200);

      // Test business requirements - no schema validation needed for behavior testing
      expect(response.body.rankings).toHaveLength(10); // Default limit
      expect(response.body.metadata.position).toBe('QB');
      expect(response.body.metadata.week).toBe(1);
      expect(response.body.metadata.scoring).toBe('half_ppr');
      
      // All rankings should have required fields
      response.body.rankings.forEach((ranking: any) => {
        expect(ranking.rank).toBeGreaterThan(0);
        expect(ranking.player.position).toBe('QB');
        expect(ranking.predictedPoints).toBeGreaterThan(0);
        expect(ranking.confidence).toBeGreaterThanOrEqual(0);
        expect(ranking.confidence).toBeLessThanOrEqual(1);
      });
      
      // Rankings should be sorted by rank
      const ranks = response.body.rankings.map((r: any) => r.rank);
      expect(ranks).toEqual([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]);
    });

    it('should return RB rankings when position is RB', async () => {
      const response = await request(app)
        .get('/api/rankings/RB')
        .expect(200);
      
      expect(response.body.metadata.position).toBe('RB');
      response.body.rankings.forEach((ranking: any) => {
        expect(ranking.player.position).toBe('RB');
      });
    });

    it('should accept query parameters for week and scoring format', async () => {
      const response = await request(app)
        .get('/api/rankings/QB')
        .query({ week: 5, scoring: 'ppr', limit: 5 })
        .expect(200);
      
      expect(response.body.rankings).toHaveLength(5);
      expect(response.body.metadata.week).toBe(5);
      expect(response.body.metadata.scoring).toBe('ppr');
      expect(response.body.metadata.limit).toBe(5);
    });

    it('should reject invalid position', async () => {
      await request(app)
        .get('/api/rankings/INVALID')
        .expect(400);
    });

    it('should reject invalid week', async () => {
      await request(app)
        .get('/api/rankings/QB')
        .query({ week: 0 })
        .expect(400);
        
      await request(app)
        .get('/api/rankings/QB')
        .query({ week: 19 })
        .expect(400);
    });

    it('should reject invalid scoring format', async () => {
      await request(app)
        .get('/api/rankings/QB')
        .query({ scoring: 'invalid' })
        .expect(400);
    });

    it('should handle limit parameter correctly', async () => {
      const response = await request(app)
        .get('/api/rankings/QB')
        .query({ limit: 3 })
        .expect(200);

      expect(response.body.rankings).toHaveLength(3);
    });

    it('should include cache status in metadata', async () => {
      const response = await request(app)
        .get('/api/rankings/QB')
        .expect(200);

      expect(typeof response.body.metadata.cached).toBe('boolean');
    });

    it('should return higher predicted points for higher ranks', async () => {
      const response = await request(app)
        .get('/api/rankings/QB')
        .expect(200);

      const rankings = response.body.rankings;
      
      // Each subsequent ranking should have equal or lower predicted points
      for (let i = 1; i < rankings.length; i++) {
        expect(rankings[i].predictedPoints).toBeLessThanOrEqual(rankings[i - 1].predictedPoints);
      }
    });
  });

  // Test business behavior for different positions
  describe('Rankings for all positions', () => {
    const positions = ['QB', 'RB', 'WR', 'TE'] as const;
    
    positions.forEach((position) => {
      it(`should return valid rankings for ${position}`, async () => {
        const response = await request(app)
          .get(`/api/rankings/${position}`)
          .expect(200);
        
        expect(response.body.metadata.position).toBe(position);
        response.body.rankings.forEach((ranking: any) => {
          expect(ranking.player.position).toBe(position);
        });
      });
    });
  });

  // Test edge cases and error handling
  describe('Error handling', () => {
    it('should return 500 if service is unavailable', async () => {
      // This test will help us define error handling behavior
      // We'll mock service failures when we implement the service layer
    });

    it('should return empty array if no players found', async () => {
      // Test behavior when database has no players for a position
      // This defines the expected behavior for edge cases
    });
  });
});

// Test for player analysis endpoint
describe('Player Analysis API', () => {
  describe('GET /api/player/:playerId/analysis', () => {
    it('should return detailed player analysis', async () => {
      const mockPlayer = getMockQB();
      
      const response = await request(app)
        .get(`/api/player/${mockPlayer.id}/analysis`)
        .query({ week: 1 })
        .expect(200);

      // This test defines what player analysis should include
      expect(response.body).toHaveProperty('player');
      expect(response.body).toHaveProperty('prediction');
      expect(response.body).toHaveProperty('recentStats');
      expect(response.body).toHaveProperty('analysis');
      
      expect(response.body.player.id).toBe(mockPlayer.id);
      expect(response.body.analysis).toHaveProperty('recommendation');
      expect(['start', 'bench', 'flex', 'avoid']).toContain(response.body.analysis.recommendation);
    });

    it('should return 404 for non-existent player', async () => {
      await request(app)
        .get('/api/player/non-existent-id/analysis')
        .expect(404);
    });
  });
});

// Test system status endpoint
describe('System Status API', () => {
  describe('GET /api/status', () => {
    it('should return system health information', async () => {
      const response = await request(app)
        .get('/api/status')
        .expect(200);

      // Define what system status should include
      expect(response.body).toHaveProperty('status');
      expect(response.body).toHaveProperty('database');
      expect(response.body).toHaveProperty('cache');
      expect(response.body).toHaveProperty('mlService');
      expect(response.body).toHaveProperty('timestamp');
      
      expect(['healthy', 'degraded', 'down']).toContain(response.body.status);
    });
  });
});

// Test injury analysis endpoint
describe('Injury Analysis API', () => {
  describe('GET /api/injury', () => {
    it('should return basic injury monitoring status with default week', async () => {
      const response = await request(app)
        .get('/api/injury')
        .expect(200);

      // Define what injury analysis response should include
      expect(response.body).toHaveProperty('week');
      expect(response.body).toHaveProperty('injury_analysis');
      
      expect(response.body.week).toBe(1); // Default week
      expect(response.body.injury_analysis).toHaveProperty('monitoring');
      expect(response.body.injury_analysis).toHaveProperty('features');
      expect(response.body.injury_analysis).toHaveProperty('current_status');
      
      // Features should be an array
      expect(Array.isArray(response.body.injury_analysis.features)).toBe(true);
      expect(response.body.injury_analysis.features.length).toBeGreaterThan(0);
      
      // Should have expected monitoring features
      const features = response.body.injury_analysis.features;
      expect(features).toContain('Real-time status monitoring');
      expect(features).toContain('Impact assessment algorithms');
      
      // Status should indicate monitoring is active
      expect(response.body.injury_analysis.monitoring).toBe('active');
      expect(response.body.injury_analysis.current_status).toContain('Week 1');
    });

    it('should accept week parameter and update response accordingly', async () => {
      const response = await request(app)
        .get('/api/injury')
        .query({ week: 5 })
        .expect(200);

      expect(response.body.week).toBe(5);
      expect(response.body.injury_analysis.current_status).toContain('Week 5');
    });

    it('should validate week parameter range', async () => {
      // Test invalid week - too low
      await request(app)
        .get('/api/injury')
        .query({ week: 0 })
        .expect(400);

      // Test invalid week - too high  
      await request(app)
        .get('/api/injury')
        .query({ week: 19 })
        .expect(400);
    });

    it('should include all expected injury analysis features', async () => {
      const response = await request(app)
        .get('/api/injury')
        .expect(200);

      const features = response.body.injury_analysis.features;
      const expectedFeatures = [
        'Real-time status monitoring',
        'Impact assessment algorithms',
        'Recovery timeline modeling',
        'Data contamination filtering'
      ];

      expectedFeatures.forEach(feature => {
        expect(features).toContain(feature);
      });
    });

    it('should handle malformed week parameter gracefully', async () => {
      const response = await request(app)
        .get('/api/injury')
        .query({ week: 'invalid' })
        .expect(400);

      expect(response.body).toHaveProperty('error');
      expect(response.body.error).toContain('Invalid week parameter');
    });
  });

  // Future endpoint for player-specific injury analysis
  describe('GET /api/injury/player/:playerId', () => {
    it('should return player-specific injury analysis (future implementation)', async () => {
      const mockPlayer = getMockQB();
      
      const response = await request(app)
        .get(`/api/injury/player/${mockPlayer.id}`)
        .query({ week: 1 })
        .expect(200);

      // Define expected structure for player-specific analysis
      expect(response.body).toHaveProperty('player_info');
      expect(response.body).toHaveProperty('injury_status');
      expect(response.body).toHaveProperty('risk_assessment');
      expect(response.body).toHaveProperty('impact_analysis');
      
      expect(response.body.player_info.player_id).toBe(mockPlayer.id);
      expect(response.body.injury_status).toHaveProperty('current_status');
      expect(['healthy', 'questionable', 'doubtful', 'out', 'ir']).toContain(
        response.body.injury_status.current_status
      );
      
      expect(response.body.risk_assessment).toHaveProperty('overall_risk_level');
      expect(['low', 'moderate', 'high', 'critical']).toContain(
        response.body.risk_assessment.overall_risk_level
      );
      
      expect(response.body.impact_analysis).toHaveProperty('recommended_action');
      expect(['start', 'sit', 'monitor', 'avoid']).toContain(
        response.body.impact_analysis.recommended_action
      );
    });

    it('should return 404 for non-existent player', async () => {
      await request(app)
        .get('/api/injury/player/non-existent-id')
        .expect(404);
    });

    it('should validate week parameter for player analysis', async () => {
      const mockPlayer = getMockQB();
      
      await request(app)
        .get(`/api/injury/player/${mockPlayer.id}`)
        .query({ week: 0 })
        .expect(400);
    });
  });
});

// Test boom-bust analysis endpoint
describe('Boom-Bust Analysis API', () => {
  describe('GET /api/boom-bust', () => {
    it('should return basic boom-bust analysis with default parameters', async () => {
      const response = await request(app)
        .get('/api/boom-bust')
        .expect(200);

      // Define what boom-bust analysis response should include
      expect(response.body).toHaveProperty('position');
      expect(response.body).toHaveProperty('week');
      expect(response.body).toHaveProperty('boom_bust_analysis');
      
      expect(response.body.position).toBe('WR'); // Default position
      expect(response.body.week).toBe(1); // Default week
      
      const analysis = response.body.boom_bust_analysis;
      expect(analysis).toHaveProperty('volatility_modeling');
      expect(analysis).toHaveProperty('projections');
      expect(analysis).toHaveProperty('features');
      
      // Projections should include floor, base, ceiling
      expect(analysis.projections).toHaveProperty('floor');
      expect(analysis.projections).toHaveProperty('base');
      expect(analysis.projections).toHaveProperty('ceiling');
      
      // Features should be an array
      expect(Array.isArray(analysis.features)).toBe(true);
      expect(analysis.features).toContain('Advanced probability modeling');
      expect(analysis.features).toContain('Position-specific variance analysis');
      
      expect(analysis.volatility_modeling).toBe('active');
    });

    it('should accept position and week parameters', async () => {
      const response = await request(app)
        .get('/api/boom-bust')
        .query({ position: 'QB', week: 5 })
        .expect(200);

      expect(response.body.position).toBe('QB');
      expect(response.body.week).toBe(5);
    });

    it('should validate position parameter', async () => {
      await request(app)
        .get('/api/boom-bust')
        .query({ position: 'INVALID' })
        .expect(400);
    });

    it('should validate week parameter range', async () => {
      await request(app)
        .get('/api/boom-bust')
        .query({ week: 0 })
        .expect(400);

      await request(app)
        .get('/api/boom-bust')
        .query({ week: 19 })
        .expect(400);
    });

    it('should include all expected boom-bust features', async () => {
      const response = await request(app)
        .get('/api/boom-bust')
        .expect(200);

      const features = response.body.boom_bust_analysis.features;
      const expectedFeatures = [
        'Advanced probability modeling',
        'Position-specific variance analysis',
        'Multi-factor risk assessment',
        'Range-based projections'
      ];

      expectedFeatures.forEach(feature => {
        expect(features).toContain(feature);
      });
    });
  });

  // Player-specific boom-bust analysis endpoint
  describe('GET /api/boom-bust/player/:playerId', () => {
    it('should return detailed boom-bust analysis for specific player', async () => {
      const mockPlayer = getMockQB();
      
      const response = await request(app)
        .get(`/api/boom-bust/player/${mockPlayer.id}`)
        .query({ week: 1, base_projection: 22.5 })
        .expect(200);

      // Define expected structure for player-specific boom-bust analysis
      expect(response.body).toHaveProperty('player_info');
      expect(response.body).toHaveProperty('projections');
      expect(response.body).toHaveProperty('probabilities');
      expect(response.body).toHaveProperty('analysis_metrics');
      expect(response.body).toHaveProperty('contributing_factors');
      
      // Player info
      expect(response.body.player_info.player_id).toBe(mockPlayer.id);
      expect(response.body.player_info.position).toBe('QB');
      
      // Projections should include floor, base, ceiling
      const projections = response.body.projections;
      expect(projections).toHaveProperty('base_projection');
      expect(projections).toHaveProperty('floor_projection');
      expect(projections).toHaveProperty('ceiling_projection');
      expect(projections.floor_projection).toBeLessThan(projections.base_projection);
      expect(projections.ceiling_projection).toBeGreaterThan(projections.base_projection);
      
      // Probabilities should sum to approximately 1.0
      const probabilities = response.body.probabilities;
      expect(probabilities).toHaveProperty('boom_probability');
      expect(probabilities).toHaveProperty('bust_probability');
      expect(probabilities).toHaveProperty('normal_probability');
      
      const totalProb = probabilities.boom_probability + 
                       probabilities.bust_probability + 
                       probabilities.normal_probability;
      expect(totalProb).toBeCloseTo(1.0, 2);
      
      // Analysis metrics
      const metrics = response.body.analysis_metrics;
      expect(metrics).toHaveProperty('volatility_score');
      expect(metrics).toHaveProperty('consistency_score');
      expect(metrics).toHaveProperty('upside_potential');
      expect(metrics).toHaveProperty('downside_risk');
      
      expect(metrics.volatility_score).toBeGreaterThanOrEqual(0);
      expect(metrics.volatility_score).toBeLessThanOrEqual(1);
      expect(metrics.consistency_score).toBeGreaterThanOrEqual(0);
      expect(metrics.consistency_score).toBeLessThanOrEqual(1);
      
      // Contributing factors
      const factors = response.body.contributing_factors;
      expect(factors).toHaveProperty('injury_risk_factor');
      expect(factors).toHaveProperty('matchup_factor');
      expect(factors).toHaveProperty('usage_stability_factor');
    });

    it('should show position-specific volatility differences', async () => {
      const qbPlayer = getMockQB({ id: 'test-qb-player' });
      const rbPlayer = getMockRB({ id: 'test-rb-player' });
      
      const qbResponse = await request(app)
        .get(`/api/boom-bust/player/${qbPlayer.id}`)
        .query({ base_projection: 20.0 })
        .expect(200);
        
      const rbResponse = await request(app)
        .get(`/api/boom-bust/player/${rbPlayer.id}`)
        .query({ base_projection: 20.0 })
        .expect(200);

      // RBs should be more volatile than QBs
      expect(rbResponse.body.analysis_metrics.volatility_score)
        .toBeGreaterThan(qbResponse.body.analysis_metrics.volatility_score);
        
      // QBs should be more consistent than RBs
      expect(qbResponse.body.analysis_metrics.consistency_score)
        .toBeGreaterThan(rbResponse.body.analysis_metrics.consistency_score);
    });

    it('should return 404 for non-existent player', async () => {
      await request(app)
        .get('/api/boom-bust/player/non-existent-id')
        .query({ base_projection: 20.0 })
        .expect(404);
    });

    it('should require base_projection parameter', async () => {
      const mockPlayer = getMockQB();
      
      await request(app)
        .get(`/api/boom-bust/player/${mockPlayer.id}`)
        .expect(400);
    });

    it('should validate base_projection parameter', async () => {
      const mockPlayer = getMockQB();
      
      // Negative projection
      await request(app)
        .get(`/api/boom-bust/player/${mockPlayer.id}`)
        .query({ base_projection: -5 })
        .expect(400);
        
      // Invalid projection
      await request(app)
        .get(`/api/boom-bust/player/${mockPlayer.id}`)
        .query({ base_projection: 'invalid' })
        .expect(400);
    });

    it('should handle different scoring formats', async () => {
      const mockPlayer = getMockWR();
      
      const pprResponse = await request(app)
        .get(`/api/boom-bust/player/${mockPlayer.id}`)
        .query({ base_projection: 15.0, scoring_format: 'ppr' })
        .expect(200);
        
      const standardResponse = await request(app)
        .get(`/api/boom-bust/player/${mockPlayer.id}`)
        .query({ base_projection: 12.0, scoring_format: 'standard' })
        .expect(200);

      // PPR should generally show lower volatility for WRs due to reception floor
      expect(standardResponse.body.analysis_metrics.volatility_score)
        .toBeGreaterThanOrEqual(pprResponse.body.analysis_metrics.volatility_score - 0.1);
    });
  });

  // Batch boom-bust analysis endpoint
  describe('GET /api/boom-bust/batch', () => {
    it('should return boom-bust analysis for multiple players', async () => {
      const players = [
        { player_id: getMockQB().id, base_projection: 22.0 },
        { player_id: getMockRB().id, base_projection: 18.0 },
        { player_id: getMockWR().id, base_projection: 15.0 }
      ];
      
      const response = await request(app)
        .post('/api/boom-bust/batch')
        .send({ players, week: 1 })
        .expect(200);

      expect(response.body).toHaveProperty('results');
      expect(Array.isArray(response.body.results)).toBe(true);
      expect(response.body.results).toHaveLength(3);
      
      // Each result should have the same structure as individual analysis
      response.body.results.forEach((result: any) => {
        expect(result).toHaveProperty('player_info');
        expect(result).toHaveProperty('probabilities');
        expect(result).toHaveProperty('analysis_metrics');
      });
    });

    it('should handle empty player list', async () => {
      const response = await request(app)
        .post('/api/boom-bust/batch')
        .send({ players: [], week: 1 })
        .expect(200);

      expect(response.body.results).toHaveLength(0);
    });

    it('should validate batch request format', async () => {
      await request(app)
        .post('/api/boom-bust/batch')
        .send({ invalid: 'data' })
        .expect(400);
    });
  });
});

// Test features discovery endpoint
describe('Features API', () => {
  describe('GET /api/features', () => {
    it('should return available API features and capabilities', async () => {
      const response = await request(app)
        .get('/api/features')
        .expect(200);

      // Define what features response should include
      expect(response.body).toHaveProperty('endpoints');
      expect(response.body).toHaveProperty('version');
      expect(response.body).toHaveProperty('capabilities');
      expect(response.body).toHaveProperty('documentation');
      
      // Endpoints should be an array of available API endpoints
      expect(Array.isArray(response.body.endpoints)).toBe(true);
      expect(response.body.endpoints.length).toBeGreaterThan(0);
      
      // Each endpoint should have required properties
      response.body.endpoints.forEach((endpoint: any) => {
        expect(endpoint).toHaveProperty('path');
        expect(endpoint).toHaveProperty('method');
        expect(endpoint).toHaveProperty('description');
        expect(endpoint).toHaveProperty('status');
        expect(['active', 'beta', 'deprecated']).toContain(endpoint.status);
      });
      
      // Should include our implemented endpoints
      const endpointPaths = response.body.endpoints.map((e: any) => e.path);
      expect(endpointPaths).toContain('/api/rankings/:position');
      expect(endpointPaths).toContain('/api/player/:playerId/analysis');
      expect(endpointPaths).toContain('/api/status');
    });

    it('should return capabilities with feature flags', async () => {
      const response = await request(app)
        .get('/api/features')
        .expect(200);

      expect(response.body.capabilities).toHaveProperty('rankings');
      expect(response.body.capabilities).toHaveProperty('playerAnalysis');
      expect(response.body.capabilities).toHaveProperty('injuryAnalysis');
      expect(response.body.capabilities).toHaveProperty('boomBustAnalysis');
      
      // Each capability should have enabled status
      Object.values(response.body.capabilities).forEach((capability: any) => {
        expect(typeof capability.enabled).toBe('boolean');
        expect(capability).toHaveProperty('description');
      });
    });

    it('should include API documentation links', async () => {
      const response = await request(app)
        .get('/api/features')
        .expect(200);

      expect(response.body.documentation).toHaveProperty('apiDocs');
      expect(response.body.documentation).toHaveProperty('examples');
      expect(typeof response.body.documentation.apiDocs).toBe('string');
    });

    it('should return consistent version information', async () => {
      const response = await request(app)
        .get('/api/features')
        .expect(200);

      expect(typeof response.body.version).toBe('string');
      expect(response.body.version).toMatch(/^\d+\.\d+\.\d+$/); // Semantic versioning
    });
  });
});

// Test batch rankings endpoint for performance optimization
describe('Batch Rankings API', () => {
  describe('POST /api/batch-rankings', () => {
    it('should return rankings for multiple positions in one request', async () => {
      const response = await request(app)
        .post('/api/batch-rankings')
        .send({
          positions: ['QB', 'RB', 'WR'],
          week: 1,
          scoring_format: 'half_ppr',
          limit: 5
        })
        .expect(200);

      // Define expected structure for batch rankings response
      expect(response.body).toHaveProperty('rankings');
      expect(response.body).toHaveProperty('metadata');
      
      // Rankings should be grouped by position
      expect(response.body.rankings).toHaveProperty('QB');
      expect(response.body.rankings).toHaveProperty('RB');
      expect(response.body.rankings).toHaveProperty('WR');
      
      // Each position should have the requested limit
      expect(response.body.rankings.QB).toHaveLength(5);
      expect(response.body.rankings.RB).toHaveLength(5);
      expect(response.body.rankings.WR).toHaveLength(5);
      
      // Each ranking should have the same structure as individual rankings
      response.body.rankings.QB.forEach((ranking: any) => {
        expect(ranking.rank).toBeGreaterThan(0);
        expect(ranking.player.position).toBe('QB');
        expect(ranking.predictedPoints).toBeGreaterThan(0);
        expect(ranking.confidence).toBeGreaterThanOrEqual(0);
        expect(ranking.confidence).toBeLessThanOrEqual(1);
      });
      
      // Metadata should include request parameters
      expect(response.body.metadata.week).toBe(1);
      expect(response.body.metadata.scoring).toBe('half_ppr');
      expect(response.body.metadata.limit).toBe(5);
      expect(response.body.metadata.positions).toEqual(['QB', 'RB', 'WR']);
    });

    it('should handle single position in batch request', async () => {
      const response = await request(app)
        .post('/api/batch-rankings')
        .send({
          positions: ['TE'],
          week: 3,
          limit: 8
        })
        .expect(200);

      expect(response.body.rankings).toHaveProperty('TE');
      expect(response.body.rankings.TE).toHaveLength(8);
      expect(response.body.metadata.positions).toEqual(['TE']);
      expect(response.body.metadata.week).toBe(3);
    });

    it('should use default parameters when not specified', async () => {
      const response = await request(app)
        .post('/api/batch-rankings')
        .send({
          positions: ['QB', 'RB']
        })
        .expect(200);

      // Should use defaults: week 1, half_ppr scoring, limit 10
      expect(response.body.metadata.week).toBe(1);
      expect(response.body.metadata.scoring).toBe('half_ppr');
      expect(response.body.metadata.limit).toBe(10);
      expect(response.body.rankings.QB).toHaveLength(10);
      expect(response.body.rankings.RB).toHaveLength(10);
    });

    it('should validate positions array is required', async () => {
      await request(app)
        .post('/api/batch-rankings')
        .send({
          week: 1
        })
        .expect(400);
    });

    it('should validate positions array is not empty', async () => {
      await request(app)
        .post('/api/batch-rankings')
        .send({
          positions: [],
          week: 1
        })
        .expect(400);
    });

    it('should validate all positions are valid', async () => {
      await request(app)
        .post('/api/batch-rankings')
        .send({
          positions: ['QB', 'INVALID', 'RB'],
          week: 1
        })
        .expect(400);
    });

    it('should validate week parameter range in batch request', async () => {
      await request(app)
        .post('/api/batch-rankings')
        .send({
          positions: ['QB'],
          week: 0
        })
        .expect(400);

      await request(app)
        .post('/api/batch-rankings')
        .send({
          positions: ['QB'],
          week: 19
        })
        .expect(400);
    });

    it('should validate scoring format in batch request', async () => {
      await request(app)
        .post('/api/batch-rankings')
        .send({
          positions: ['QB'],
          scoring_format: 'invalid'
        })
        .expect(400);
    });

    it('should validate limit parameter in batch request', async () => {
      await request(app)
        .post('/api/batch-rankings')
        .send({
          positions: ['QB'],
          limit: 0
        })
        .expect(400);

      await request(app)
        .post('/api/batch-rankings')
        .send({
          positions: ['QB'],
          limit: 101
        })
        .expect(400);
    });

    it('should maintain ranking order consistency across positions', async () => {
      const response = await request(app)
        .post('/api/batch-rankings')
        .send({
          positions: ['QB', 'RB'],
          week: 1,
          limit: 3
        })
        .expect(200);

      // QB rankings should be ordered correctly
      const qbRanks = response.body.rankings.QB.map((r: any) => r.rank);
      expect(qbRanks).toEqual([1, 2, 3]);
      
      // RB rankings should be ordered correctly
      const rbRanks = response.body.rankings.RB.map((r: any) => r.rank);
      expect(rbRanks).toEqual([1, 2, 3]);
      
      // Points should be descending within each position
      const qbPoints = response.body.rankings.QB.map((r: any) => r.predictedPoints);
      for (let i = 1; i < qbPoints.length; i++) {
        expect(qbPoints[i]).toBeLessThanOrEqual(qbPoints[i - 1]);
      }
    });

    it('should include cache status for batch requests', async () => {
      const response = await request(app)
        .post('/api/batch-rankings')
        .send({
          positions: ['QB', 'RB']
        })
        .expect(200);

      expect(typeof response.body.metadata.cached).toBe('boolean');
      expect(response.body.metadata).toHaveProperty('generatedAt');
    });

    it('should handle all four positions in single batch request', async () => {
      const response = await request(app)
        .post('/api/batch-rankings')
        .send({
          positions: ['QB', 'RB', 'WR', 'TE'],
          week: 5,
          scoring_format: 'ppr',
          limit: 3
        })
        .expect(200);

      expect(Object.keys(response.body.rankings)).toEqual(['QB', 'RB', 'WR', 'TE']);
      
      // Each position should have correct data
      ['QB', 'RB', 'WR', 'TE'].forEach(position => {
        expect(response.body.rankings[position]).toHaveLength(3);
        response.body.rankings[position].forEach((ranking: any) => {
          expect(ranking.player.position).toBe(position);
          expect(ranking.week).toBe(5);
          expect(ranking.scoringFormat).toBe('ppr');
        });
      });
    });
  });
});

// Test matchup analysis endpoint for game-specific insights
describe('Matchup Analysis API', () => {
  describe('GET /api/matchup-analysis', () => {
    it('should return basic matchup analysis for current week', async () => {
      const response = await request(app)
        .get('/api/matchup-analysis')
        .expect(200);

      // Define expected structure for matchup analysis response
      expect(response.body).toHaveProperty('week');
      expect(response.body).toHaveProperty('matchups');
      expect(response.body).toHaveProperty('metadata');
      
      expect(response.body.week).toBe(1); // Default week
      expect(Array.isArray(response.body.matchups)).toBe(true);
      expect(response.body.matchups.length).toBeGreaterThan(0);
      
      // Each matchup should have required properties
      response.body.matchups.forEach((matchup: any) => {
        expect(matchup).toHaveProperty('home_team');
        expect(matchup).toHaveProperty('away_team');
        expect(matchup).toHaveProperty('game_info');
        expect(matchup).toHaveProperty('analysis');
        
        expect(matchup.game_info).toHaveProperty('kickoff_time');
        expect(matchup.game_info).toHaveProperty('weather_conditions');
        expect(matchup.game_info).toHaveProperty('vegas_line');
        
        expect(matchup.analysis).toHaveProperty('pace_analysis');
        expect(matchup.analysis).toHaveProperty('scoring_environment');
        expect(matchup.analysis).toHaveProperty('key_factors');
      });
      
      expect(response.body.metadata).toHaveProperty('total_games');
      expect(response.body.metadata).toHaveProperty('analysis_date');
    });

    it('should accept week parameter for historical matchups', async () => {
      const response = await request(app)
        .get('/api/matchup-analysis')
        .query({ week: 5 })
        .expect(200);

      expect(response.body.week).toBe(5);
      expect(response.body.metadata.week).toBe(5);
    });

    it('should validate week parameter range', async () => {
      await request(app)
        .get('/api/matchup-analysis')
        .query({ week: 0 })
        .expect(400);

      await request(app)
        .get('/api/matchup-analysis')
        .query({ week: 19 })
        .expect(400);
    });

    it('should include weather impact analysis', async () => {
      const response = await request(app)
        .get('/api/matchup-analysis')
        .expect(200);

      response.body.matchups.forEach((matchup: any) => {
        expect(matchup.game_info.weather_conditions).toHaveProperty('temperature');
        expect(matchup.game_info.weather_conditions).toHaveProperty('wind_speed');
        expect(matchup.game_info.weather_conditions).toHaveProperty('precipitation');
        expect(matchup.game_info.weather_conditions).toHaveProperty('dome_game');
        
        expect(matchup.analysis).toHaveProperty('weather_impact');
        expect(['minimal', 'moderate', 'significant']).toContain(matchup.analysis.weather_impact);
      });
    });

    it('should include pace and scoring environment analysis', async () => {
      const response = await request(app)
        .get('/api/matchup-analysis')
        .expect(200);

      response.body.matchups.forEach((matchup: any) => {
        expect(matchup.analysis.pace_analysis).toHaveProperty('expected_plays');
        expect(matchup.analysis.pace_analysis).toHaveProperty('pace_rating');
        expect(matchup.analysis.pace_analysis.expected_plays).toBeGreaterThan(0);
        expect(['slow', 'average', 'fast']).toContain(matchup.analysis.pace_analysis.pace_rating);
        
        expect(matchup.analysis.scoring_environment).toHaveProperty('total_points_projection');
        expect(matchup.analysis.scoring_environment).toHaveProperty('environment_rating');
        expect(['low', 'moderate', 'high']).toContain(matchup.analysis.scoring_environment.environment_rating);
      });
    });
  });

  describe('GET /api/matchup-analysis/team/:teamCode', () => {
    it('should return team-specific matchup analysis', async () => {
      const response = await request(app)
        .get('/api/matchup-analysis/team/KAN')
        .query({ week: 1 })
        .expect(200);

      // Define expected structure for team-specific matchup analysis
      expect(response.body).toHaveProperty('team_info');
      expect(response.body).toHaveProperty('opponent_info');
      expect(response.body).toHaveProperty('matchup_analysis');
      expect(response.body).toHaveProperty('fantasy_implications');
      
      expect(response.body.team_info.team_code).toBe('KAN');
      expect(response.body.team_info).toHaveProperty('team_name');
      expect(response.body.team_info).toHaveProperty('home_away');
      expect(['home', 'away']).toContain(response.body.team_info.home_away);
      
      expect(response.body.opponent_info).toHaveProperty('team_code');
      expect(response.body.opponent_info).toHaveProperty('team_name');
      
      expect(response.body.matchup_analysis).toHaveProperty('offensive_matchup');
      expect(response.body.matchup_analysis).toHaveProperty('defensive_matchup');
      expect(response.body.matchup_analysis).toHaveProperty('special_teams');
      
      expect(response.body.fantasy_implications).toHaveProperty('key_players');
      expect(response.body.fantasy_implications).toHaveProperty('position_outlooks');
      expect(Array.isArray(response.body.fantasy_implications.key_players)).toBe(true);
    });

    it('should return 404 for invalid team code', async () => {
      await request(app)
        .get('/api/matchup-analysis/team/INV')
        .expect(404);
    });

    it('should validate team code format', async () => {
      await request(app)
        .get('/api/matchup-analysis/team/KC') // 2 chars instead of 3
        .expect(400);

      await request(app)
        .get('/api/matchup-analysis/team/KANS') // 4 chars instead of 3
        .expect(400);
    });

    it('should include position-specific fantasy outlook', async () => {
      const response = await request(app)
        .get('/api/matchup-analysis/team/KAN')
        .expect(200);

      expect(response.body.fantasy_implications.position_outlooks).toHaveProperty('QB');
      expect(response.body.fantasy_implications.position_outlooks).toHaveProperty('RB');
      expect(response.body.fantasy_implications.position_outlooks).toHaveProperty('WR');
      expect(response.body.fantasy_implications.position_outlooks).toHaveProperty('TE');
      
      ['QB', 'RB', 'WR', 'TE'].forEach(position => {
        const outlook = response.body.fantasy_implications.position_outlooks[position];
        expect(outlook).toHaveProperty('outlook_rating');
        expect(outlook).toHaveProperty('key_factors');
        expect(['poor', 'below_average', 'average', 'above_average', 'excellent']).toContain(outlook.outlook_rating);
        expect(Array.isArray(outlook.key_factors)).toBe(true);
      });
    });

    it('should include offensive and defensive matchup details', async () => {
      const response = await request(app)
        .get('/api/matchup-analysis/team/KAN')
        .expect(200);

      const offensive = response.body.matchup_analysis.offensive_matchup;
      expect(offensive).toHaveProperty('pass_game_advantage');
      expect(offensive).toHaveProperty('run_game_advantage');
      expect(offensive).toHaveProperty('red_zone_efficiency');
      expect(['strong_disadvantage', 'disadvantage', 'neutral', 'advantage', 'strong_advantage']).toContain(offensive.pass_game_advantage);
      expect(['strong_disadvantage', 'disadvantage', 'neutral', 'advantage', 'strong_advantage']).toContain(offensive.run_game_advantage);
      
      const defensive = response.body.matchup_analysis.defensive_matchup;
      expect(defensive).toHaveProperty('pass_defense_strength');
      expect(defensive).toHaveProperty('run_defense_strength');
      expect(defensive).toHaveProperty('turnover_expectation');
      expect(['poor', 'below_average', 'average', 'above_average', 'elite']).toContain(defensive.pass_defense_strength);
      expect(['poor', 'below_average', 'average', 'above_average', 'elite']).toContain(defensive.run_defense_strength);
    });
  });

  describe('GET /api/matchup-analysis/player/:playerId', () => {
    it('should return player-specific matchup analysis', async () => {
      const mockPlayer = getMockQB();
      
      const response = await request(app)
        .get(`/api/matchup-analysis/player/${mockPlayer.id}`)
        .query({ week: 1 })
        .expect(200);

      // Define expected structure for player-specific matchup analysis
      expect(response.body).toHaveProperty('player_info');
      expect(response.body).toHaveProperty('matchup_details');
      expect(response.body).toHaveProperty('performance_outlook');
      expect(response.body).toHaveProperty('key_matchup_factors');
      
      expect(response.body.player_info.player_id).toBe(mockPlayer.id);
      expect(response.body.player_info).toHaveProperty('position');
      expect(response.body.player_info).toHaveProperty('team');
      
      expect(response.body.matchup_details).toHaveProperty('opponent_defense_rank');
      expect(response.body.matchup_details).toHaveProperty('target_share_opportunity');
      expect(response.body.matchup_details).toHaveProperty('game_script_projection');
      
      expect(response.body.performance_outlook).toHaveProperty('ceiling_multiplier');
      expect(response.body.performance_outlook).toHaveProperty('floor_multiplier');
      expect(response.body.performance_outlook).toHaveProperty('matchup_rating');
      expect(['avoid', 'poor', 'below_average', 'average', 'above_average', 'smash_spot']).toContain(response.body.performance_outlook.matchup_rating);
      
      expect(Array.isArray(response.body.key_matchup_factors)).toBe(true);
    });

    it('should return different analysis for different positions', async () => {
      const qbPlayer = getMockQB();
      const rbPlayer = getMockRB();
      
      const qbResponse = await request(app)
        .get(`/api/matchup-analysis/player/${qbPlayer.id}`)
        .expect(200);
        
      const rbResponse = await request(app)
        .get(`/api/matchup-analysis/player/${rbPlayer.id}`)
        .expect(200);

      // QB should have passing-specific factors
      expect(qbResponse.body.key_matchup_factors).toEqual(
        expect.arrayContaining([expect.stringMatching(/pass|passing|quarterback/i)])
      );
      
      // RB should have rushing-specific factors
      expect(rbResponse.body.key_matchup_factors).toEqual(
        expect.arrayContaining([expect.stringMatching(/rush|rushing|run/i)])
      );
    });

    it('should return 404 for non-existent player', async () => {
      await request(app)
        .get('/api/matchup-analysis/player/non-existent-id')
        .expect(404);
    });

    it('should validate week parameter for player matchup', async () => {
      const mockPlayer = getMockQB();
      
      await request(app)
        .get(`/api/matchup-analysis/player/${mockPlayer.id}`)
        .query({ week: 0 })
        .expect(400);
    });

    it('should include position-specific matchup metrics', async () => {
      const wrPlayer = getMockWR();
      
      const response = await request(app)
        .get(`/api/matchup-analysis/player/${wrPlayer.id}`)
        .expect(200);

      // WR-specific metrics
      expect(response.body.matchup_details).toHaveProperty('coverage_tendency');
      expect(response.body.matchup_details).toHaveProperty('target_competition');
      expect(['man', 'zone', 'mixed']).toContain(response.body.matchup_details.coverage_tendency);
      expect(['low', 'moderate', 'high']).toContain(response.body.matchup_details.target_competition);
    });
  });
});

// Test ML projections endpoint for fantasy points predictions
describe('ML Projections API', () => {
  describe('GET /api/projections', () => {
    it('should return projections for current week with default parameters', async () => {
      const response = await request(app)
        .get('/api/projections')
        .expect(200);

      // Define expected structure for projections response
      expect(response.body).toHaveProperty('week');
      expect(response.body).toHaveProperty('projections');
      expect(response.body).toHaveProperty('metadata');
      
      expect(response.body.week).toBe(1); // Default week
      expect(Array.isArray(response.body.projections)).toBe(true);
      expect(response.body.projections.length).toBeGreaterThan(0);
      
      // Each projection should have required ML prediction fields
      response.body.projections.forEach((projection: any) => {
        expect(projection).toHaveProperty('player_id');
        expect(projection).toHaveProperty('player_name');
        expect(projection).toHaveProperty('position');
        expect(projection).toHaveProperty('team');
        expect(projection).toHaveProperty('predicted_points');
        expect(projection).toHaveProperty('confidence');
        expect(projection).toHaveProperty('features');
        expect(projection).toHaveProperty('model_version');
        
        expect(projection.predicted_points).toBeGreaterThan(0);
        expect(projection.confidence).toBeGreaterThanOrEqual(0);
        expect(projection.confidence).toBeLessThanOrEqual(1);
        expect(['QB', 'RB', 'WR', 'TE']).toContain(projection.position);
      });
      
      expect(response.body.metadata).toHaveProperty('total_players');
      expect(response.body.metadata).toHaveProperty('model_updated_at');
      expect(response.body.metadata).toHaveProperty('feature_importance');
    });

    it('should accept position filter for specific position projections', async () => {
      const response = await request(app)
        .get('/api/projections')
        .query({ position: 'QB' })
        .expect(200);

      expect(response.body.metadata.position).toBe('QB');
      response.body.projections.forEach((projection: any) => {
        expect(projection.position).toBe('QB');
      });
    });

    it('should accept week parameter for historical projections', async () => {
      const response = await request(app)
        .get('/api/projections')
        .query({ week: 5 })
        .expect(200);

      expect(response.body.week).toBe(5);
      expect(response.body.metadata.week).toBe(5);
    });

    it('should validate week parameter range', async () => {
      await request(app)
        .get('/api/projections')
        .query({ week: 0 })
        .expect(400);

      await request(app)
        .get('/api/projections')
        .query({ week: 19 })
        .expect(400);
    });

    it('should validate position parameter', async () => {
      await request(app)
        .get('/api/projections')
        .query({ position: 'INVALID' })
        .expect(400);
    });

    it('should include ML feature importance data', async () => {
      const response = await request(app)
        .get('/api/projections')
        .expect(200);

      expect(response.body.metadata.feature_importance).toHaveProperty('recent_performance');
      expect(response.body.metadata.feature_importance).toHaveProperty('matchup_difficulty');
      expect(response.body.metadata.feature_importance).toHaveProperty('injury_status');
      expect(response.body.metadata.feature_importance).toHaveProperty('weather_conditions');
      
      // Feature importance values should sum to approximately 1.0
      const importance = response.body.metadata.feature_importance;
      const total = Object.values(importance).reduce((sum: number, val: any) => sum + val, 0);
      expect(total).toBeCloseTo(1.0, 1);
    });

    it('should include player-specific features in projections', async () => {
      const response = await request(app)
        .get('/api/projections')
        .query({ position: 'QB', limit: 5 })
        .expect(200);

      response.body.projections.forEach((projection: any) => {
        expect(projection.features).toHaveProperty('recent_performance');
        expect(projection.features).toHaveProperty('trend_direction');
        expect(projection.features).toHaveProperty('matchup_difficulty');
        expect(projection.features).toHaveProperty('injury_status');
        
        expect(projection.features.recent_performance).toBeGreaterThanOrEqual(0);
        expect(projection.features.trend_direction).toBeGreaterThanOrEqual(-1);
        expect(projection.features.trend_direction).toBeLessThanOrEqual(1);
        expect(projection.features.matchup_difficulty).toBeGreaterThanOrEqual(0);
        expect(projection.features.matchup_difficulty).toBeLessThanOrEqual(1);
        expect(['healthy', 'questionable', 'doubtful', 'out']).toContain(projection.features.injury_status);
      });
    });

    it('should support scoring format parameter', async () => {
      const pprResponse = await request(app)
        .get('/api/projections')
        .query({ position: 'WR', scoring_format: 'ppr' })
        .expect(200);
        
      const standardResponse = await request(app)
        .get('/api/projections')
        .query({ position: 'WR', scoring_format: 'standard' })
        .expect(200);

      // PPR should generally show higher points for WRs due to reception bonuses
      const pprAvg = pprResponse.body.projections.reduce((sum: number, p: any) => sum + p.predicted_points, 0) / pprResponse.body.projections.length;
      const standardAvg = standardResponse.body.projections.reduce((sum: number, p: any) => sum + p.predicted_points, 0) / standardResponse.body.projections.length;
      
      expect(pprAvg).toBeGreaterThan(standardAvg);
    });
  });

  describe('GET /api/projections/player/:playerId', () => {
    it('should return detailed ML projection for specific player', async () => {
      const mockPlayer = getMockQB();
      
      const response = await request(app)
        .get(`/api/projections/player/${mockPlayer.id}`)
        .query({ week: 1 })
        .expect(200);

      // Define expected structure for individual player projection
      expect(response.body).toHaveProperty('player_info');
      expect(response.body).toHaveProperty('prediction');
      expect(response.body).toHaveProperty('model_details');
      expect(response.body).toHaveProperty('feature_breakdown');
      
      expect(response.body.player_info.player_id).toBe(mockPlayer.id);
      expect(response.body.player_info).toHaveProperty('position');
      expect(response.body.player_info).toHaveProperty('team');
      
      expect(response.body.prediction).toHaveProperty('predicted_points');
      expect(response.body.prediction).toHaveProperty('confidence');
      expect(response.body.prediction).toHaveProperty('range');
      expect(response.body.prediction.range).toHaveProperty('floor');
      expect(response.body.prediction.range).toHaveProperty('ceiling');
      
      expect(response.body.model_details).toHaveProperty('model_version');
      expect(response.body.model_details).toHaveProperty('training_date');
      expect(response.body.model_details).toHaveProperty('accuracy_metrics');
      
      expect(response.body.feature_breakdown).toHaveProperty('recent_games');
      expect(response.body.feature_breakdown).toHaveProperty('season_trends');
      expect(response.body.feature_breakdown).toHaveProperty('matchup_analysis');
    });

    it('should return 404 for non-existent player', async () => {
      await request(app)
        .get('/api/projections/player/non-existent-id')
        .expect(404);
    });

    it('should validate week parameter for player projections', async () => {
      const mockPlayer = getMockQB();
      
      await request(app)
        .get(`/api/projections/player/${mockPlayer.id}`)
        .query({ week: 0 })
        .expect(400);
    });

    it('should include position-specific prediction details', async () => {
      const qbPlayer = getMockQB();
      const rbPlayer = getMockRB();
      
      const qbResponse = await request(app)
        .get(`/api/projections/player/${qbPlayer.id}`)
        .expect(200);
        
      const rbResponse = await request(app)
        .get(`/api/projections/player/${rbPlayer.id}`)
        .expect(200);

      // QB should have passing-specific features
      expect(qbResponse.body.feature_breakdown.season_trends).toHaveProperty('passing_yards_trend');
      expect(qbResponse.body.feature_breakdown.season_trends).toHaveProperty('passing_td_trend');
      
      // RB should have rushing-specific features
      expect(rbResponse.body.feature_breakdown.season_trends).toHaveProperty('rushing_yards_trend');
      expect(rbResponse.body.feature_breakdown.season_trends).toHaveProperty('rushing_td_trend');
    });

    it('should include confidence intervals and model uncertainty', async () => {
      const mockPlayer = getMockQB();
      
      const response = await request(app)
        .get(`/api/projections/player/${mockPlayer.id}`)
        .expect(200);

      expect(response.body.prediction.range.floor).toBeLessThan(response.body.prediction.predicted_points);
      expect(response.body.prediction.range.ceiling).toBeGreaterThan(response.body.prediction.predicted_points);
      
      expect(response.body.model_details.accuracy_metrics).toHaveProperty('rmse');
      expect(response.body.model_details.accuracy_metrics).toHaveProperty('mae');
      expect(response.body.model_details.accuracy_metrics).toHaveProperty('r2_score');
      
      expect(response.body.model_details.accuracy_metrics.r2_score).toBeGreaterThanOrEqual(0);
      expect(response.body.model_details.accuracy_metrics.r2_score).toBeLessThanOrEqual(1);
    });
  });

  describe('POST /api/projections/batch', () => {
    it('should return projections for multiple players efficiently', async () => {
      const players = [
        getMockQB().id,
        getMockRB().id,
        getMockWR().id
      ];
      
      const response = await request(app)
        .post('/api/projections/batch')
        .send({ player_ids: players, week: 1 })
        .expect(200);

      expect(response.body).toHaveProperty('projections');
      expect(Array.isArray(response.body.projections)).toBe(true);
      expect(response.body.projections).toHaveLength(3);
      
      // Each projection should have the same structure as individual projections
      response.body.projections.forEach((projection: any) => {
        expect(projection).toHaveProperty('player_info');
        expect(projection).toHaveProperty('prediction');
        expect(projection).toHaveProperty('model_details');
      });
    });

    it('should handle empty player list', async () => {
      const response = await request(app)
        .post('/api/projections/batch')
        .send({ player_ids: [], week: 1 })
        .expect(200);

      expect(response.body.projections).toHaveLength(0);
    });

    it('should validate batch request format', async () => {
      await request(app)
        .post('/api/projections/batch')
        .send({ invalid: 'data' })
        .expect(400);
    });

    it('should filter out non-existent players without failing', async () => {
      const players = [
        getMockQB().id,
        'non-existent-id',
        getMockRB().id
      ];
      
      const response = await request(app)
        .post('/api/projections/batch')
        .send({ player_ids: players, week: 1 })
        .expect(200);

      // Should return projections for valid players only
      expect(response.body.projections).toHaveLength(2);
    });
  });
});

// These tests will fail initially because we haven't implemented the app yet
// That's exactly what TDD requires - write failing tests first!

// TODO: The next step is to create the minimal implementation to make these tests pass
// Following CLAUDE.md principles:
// 1. Create Express app structure
// 2. Add route handlers with minimal logic
// 3. Implement services to make tests pass
// 4. Refactor while keeping tests green