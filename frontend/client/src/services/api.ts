// NFL Assistant API Service
// Handles all communication with Express/Django backend

import axios, { AxiosInstance, AxiosError } from 'axios';
import {
  RankingsResponse,
  PlayerAnalysis,
  SystemStatus,
  BatchRankingsRequest,
  BatchRankingsResponse,
  SearchResult,
  ApiError,
  ScoringFormat,
  Position,
  Week
} from '../types/nfl';

class NFLApiService {
  private api: AxiosInstance;
  private baseURL: string;

  constructor() {
    this.baseURL = process.env.REACT_APP_API_URL || 'http://localhost:3002';
    
    this.api = axios.create({
      baseURL: this.baseURL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor for logging
    this.api.interceptors.request.use(
      (config) => {
        console.log(`🚀 API Request: ${config.method?.toUpperCase()} ${config.url}`);
        return config;
      },
      (error) => {
        console.error('API Request Error:', error);
        return Promise.reject(error);
      }
    );

    // Response interceptor for error handling
    this.api.interceptors.response.use(
      (response) => {
        console.log(`✅ API Response: ${response.status} ${response.config.url}`);
        return response;
      },
      (error: AxiosError) => {
        console.error(`❌ API Error: ${error.response?.status} ${error.config?.url}`, error.response?.data);
        return Promise.reject(this.handleApiError(error));
      }
    );
  }

  private handleApiError(error: AxiosError): ApiError {
    if (error.response) {
      // Server responded with error status
      const responseData = error.response.data as any;
      return {
        error: responseData?.error || 'API Error',
        message: responseData?.message || error.message,
        details: responseData?.details,
        status: error.response.status,
      };
    } else if (error.request) {
      // Network error
      return {
        error: 'Network Error',
        message: 'Unable to connect to NFL prediction service',
        details: 'Please check your internet connection and try again',
      };
    } else {
      // Other error
      return {
        error: 'Unknown Error',
        message: error.message,
        details: 'An unexpected error occurred',
      };
    }
  }

  /**
   * Get player rankings for a specific position
   */
  async getRankings(
    position: Position,
    week: Week = 1,
    scoring: ScoringFormat = 'half_ppr',
    limit: number = 20
  ): Promise<RankingsResponse> {
    const response = await this.api.get(`/api/rankings/${position.toLowerCase()}`, {
      params: { week, scoring, limit },
    });
    return response.data;
  }

  /**
   * Get batch rankings for multiple positions
   */
  async getBatchRankings(request: BatchRankingsRequest): Promise<BatchRankingsResponse> {
    const response = await this.api.post('/api/batch-rankings', request);
    return response.data;
  }

  /**
   * Get detailed player analysis
   */
  async getPlayerAnalysis(playerId: string, week: Week = 1): Promise<PlayerAnalysis> {
    const response = await this.api.get(`/api/player/${playerId}/analysis`, {
      params: { week },
    });
    return response.data;
  }

  /**
   * Search for players
   */
  async searchPlayers(
    query: string,
    position?: Position,
    limit: number = 10
  ): Promise<SearchResult> {
    const response = await this.api.get('/api/search/players', {
      params: { q: query, position, limit },
    });
    return response.data;
  }

  /**
   * Get system status
   */
  async getSystemStatus(): Promise<SystemStatus> {
    const response = await this.api.get('/api/status');
    return response.data;
  }

  /**
   * Generic NFL API proxy call
   */
  async callNFLApi(endpoint: string, params?: any): Promise<any> {
    const response = await this.api.get(`/api/nfl${endpoint}`, { params });
    return response.data;
  }

  /**
   * Get all positions rankings (convenience method)
   */
  async getAllPositionRankings(
    week: Week = 1,
    scoring: ScoringFormat = 'half_ppr',
    limit: number = 15
  ): Promise<BatchRankingsResponse> {
    return this.getBatchRankings({
      positions: ['QB', 'RB', 'WR', 'TE'],
      week,
      scoring_format: scoring,
      limit,
    });
  }

  /**
   * Get injury analysis
   */
  async getInjuryAnalysis(week: Week = 1): Promise<any> {
    const response = await this.api.get('/api/injury', {
      params: { week },
    });
    return response.data;
  }

  /**
   * Get boom-bust analysis
   */
  async getBoomBustAnalysis(
    position?: Position,
    week: Week = 1
  ): Promise<any> {
    const response = await this.api.get('/api/boom-bust', {
      params: { position, week },
    });
    return response.data;
  }

  /**
   * Get matchup analysis
   */
  async getMatchupAnalysis(week: Week = 1): Promise<any> {
    const response = await this.api.get('/api/matchup-analysis', {
      params: { week },
    });
    return response.data;
  }

  /**
   * Get ML projections
   */
  async getMLProjections(
    position?: Position,
    week: Week = 1,
    scoringFormat: ScoringFormat = 'half_ppr',
    limit: number = 20
  ): Promise<any> {
    const response = await this.api.get('/api/projections', {
      params: { position, week, scoring_format: scoringFormat, limit },
    });
    return response.data;
  }

  /**
   * Get player-specific ML projection
   */
  async getPlayerProjection(
    playerId: string,
    week: Week = 1,
    scoringFormat: ScoringFormat = 'half_ppr'
  ): Promise<any> {
    const response = await this.api.get(`/api/projections/player/${playerId}`, {
      params: { week, scoring_format: scoringFormat },
    });
    return response.data;
  }

  /**
   * Get API features and capabilities
   */
  async getFeatures(): Promise<any> {
    const response = await this.api.get('/api/features');
    return response.data;
  }

  /**
   * Health check for API connectivity
   */
  async healthCheck(): Promise<{ status: string; timestamp: string }> {
    try {
      const response = await this.api.get('/api/status', { timeout: 5000 });
      return response.data;
    } catch (error) {
      throw new Error('API health check failed');
    }
  }

  /**
   * Get API base URL (useful for debugging)
   */
  getBaseURL(): string {
    return this.baseURL;
  }

  /**
   * Update API configuration
   */
  updateConfig(config: { timeout?: number; baseURL?: string }) {
    if (config.timeout) {
      this.api.defaults.timeout = config.timeout;
    }
    if (config.baseURL) {
      this.baseURL = config.baseURL;
      this.api.defaults.baseURL = config.baseURL;
    }
  }
}

// Create and export a singleton instance
export const nflApi = new NFLApiService();

// Export the class for testing or custom instances
export default NFLApiService;

// Utility functions for common API operations
export const apiUtils = {
  /**
   * Format player name for display
   */
  formatPlayerName: (name: string): string => {
    return name
      .split(' ')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
      .join(' ');
  },

  /**
   * Get position color for UI
   */
  getPositionColor: (position: Position): string => {
    const colors = {
      QB: '#1976d2',   // Blue
      RB: '#4caf50',   // Green
      WR: '#f57c00',   // Orange
      TE: '#9c27b0',   // Purple
      K: '#757575',    // Grey
      DST: '#607d8b',  // Blue Grey
    };
    return colors[position] || '#757575';
  },

  /**
   * Format points with proper decimal places
   */
  formatPoints: (points: number): string => {
    return points.toFixed(1);
  },

  /**
   * Get scoring format display name
   */
  getScoringDisplayName: (scoring: ScoringFormat): string => {
    const names = {
      standard: 'Standard',
      half_ppr: 'Half PPR',
      ppr: 'Full PPR',
    };
    return names[scoring];
  },

  /**
   * Check if API error is a network error
   */
  isNetworkError: (error: ApiError): boolean => {
    return error.error === 'Network Error';
  },

  /**
   * Get user-friendly error message
   */
  getErrorMessage: (error: ApiError): string => {
    if (apiUtils.isNetworkError(error)) {
      return 'Unable to connect to NFL prediction service. Please check your internet connection.';
    }
    return error.message || error.error || 'An unexpected error occurred';
  },
};