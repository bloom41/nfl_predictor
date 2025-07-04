/**
 * Python ML Data Source
 * Pure data retrieval bridge to Flask ML service - no business logic
 * Refactored to be data-source only as part of ML services consolidation
 */

import axios, { AxiosResponse } from 'axios';
import type { Position } from '../shared/schemas/player';

interface FlaskRankingResponse {
  rankings: Array<{
    player_name: string;
    position: string;
    predicted_points: number;
    confidence: number;
    rank: number;
    team: string;
  }>;
  position: string;
  count: number;
  cached: boolean;
  database_stored: boolean;
}

interface FlaskPlayerResponse {
  prediction: {
    player_name: string;
    position: string;
    predicted_points: number;
    confidence: number;
    team: string;
  };
  features: Record<string, any>;
  model_version: string;
}

interface FlaskStatusResponse {
  status: string;
  systems_loaded: number;
  features: Record<string, boolean>;
  supported_positions: string[];
  version: string;
}

export class PythonMLDataSource {
  private baseUrl: string;
  private timeout: number;

  constructor(baseUrl = 'http://localhost:5000', timeout = 5000) {
    this.baseUrl = baseUrl;
    this.timeout = timeout;
  }

  /**
   * Check if Python ML service is available
   */
  async isAvailable(): Promise<boolean> {
    try {
      const response = await axios.get(`${this.baseUrl}/api/status`, {
        timeout: this.timeout
      });
      return response.data.status === 'active';
    } catch (error) {
      return false;
    }
  }

  /**
   * Get service status and capabilities
   */
  async getStatus(): Promise<FlaskStatusResponse | null> {
    try {
      const response: AxiosResponse<FlaskStatusResponse> = await axios.get(
        `${this.baseUrl}/api/status`,
        { timeout: this.timeout }
      );
      return response.data;
    } catch (error) {
      console.error('Failed to get ML service status:', error);
      return null;
    }
  }

  /**
   * Get raw ranking data from Flask ML service
   * Pure data retrieval - no business logic
   */
  async getRankingsData(
    position: Position,
    options: {
      limit?: number;
      week?: number;
      season?: number;
      scoring?: string;
    } = {}
  ): Promise<FlaskRankingResponse | null> {
    try {
      const params = new URLSearchParams({
        position,
        limit: (options.limit || 20).toString(),
        week: (options.week || 1).toString(),
        season: (options.season || 2024).toString(),
        scoring: options.scoring || 'half_ppr'
      });

      const response: AxiosResponse<FlaskRankingResponse> = await axios.get(
        `${this.baseUrl}/api/rankings?${params}`,
        { timeout: this.timeout }
      );

      return response.data;
    } catch (error) {
      console.error(`Failed to get ${position} rankings:`, error);
      return null;
    }
  }

  /**
   * Get batch ranking data for multiple positions
   * Pure data retrieval with parallel requests
   */
  async getBatchRankingsData(
    positions: Position[],
    options: {
      limit?: number;
      week?: number;
      season?: number;
      scoring?: string;
    } = {}
  ): Promise<Record<Position, FlaskRankingResponse> | null> {
    try {
      const results: Record<string, FlaskRankingResponse> = {};
      
      // Use Promise.all for parallel requests
      const requests = positions.map(position => 
        this.getRankingsData(position, options)
      );

      const responses = await Promise.all(requests);

      positions.forEach((position, index) => {
        if (responses[index]) {
          results[position] = responses[index]!;
        }
      });

      return results as Record<Position, FlaskRankingResponse>;
    } catch (error) {
      console.error('Failed to get batch rankings:', error);
      return null;
    }
  }

  /**
   * Get raw player data from Flask service
   * Pure data retrieval - no analysis logic
   */
  async getPlayerData(
    playerName: string,
    options: {
      week?: number;
      season?: number;
    } = {}
  ): Promise<FlaskPlayerResponse | null> {
    try {
      const params = new URLSearchParams({
        player: playerName,
        week: (options.week || 1).toString(),
        season: (options.season || 2024).toString()
      });

      const response: AxiosResponse<FlaskPlayerResponse> = await axios.get(
        `${this.baseUrl}/api/player?${params}`,
        { timeout: this.timeout }
      );

      return response.data;
    } catch (error) {
      console.error(`Failed to get analysis for ${playerName}:`, error);
      return null;
    }
  }


  /**
   * Performance benchmark test
   */
  async benchmark(): Promise<{
    available: boolean;
    response_times: Record<string, number>;
    total_time: number;
  }> {
    const startTime = Date.now();
    const results: Record<string, number> = {};

    // Test status endpoint
    const statusStart = Date.now();
    const isAvailable = await this.isAvailable();
    results.status = Date.now() - statusStart;

    if (!isAvailable) {
      return {
        available: false,
        response_times: results,
        total_time: Date.now() - startTime
      };
    }

    // Test rankings endpoint
    const rankingsStart = Date.now();
    await this.getRankingsData('QB', { limit: 5 });
    results.rankings = Date.now() - rankingsStart;

    // Test batch rankings
    const batchStart = Date.now();
    await this.getBatchRankingsData(['QB', 'RB'], { limit: 3 });
    results.batch_rankings = Date.now() - batchStart;

    return {
      available: true,
      response_times: results,
      total_time: Date.now() - startTime
    };
  }
}

// Singleton instance
export const pythonMLDataSource = new PythonMLDataSource();

// Legacy export for backward compatibility during transition
export const pythonMLBridge = pythonMLDataSource;