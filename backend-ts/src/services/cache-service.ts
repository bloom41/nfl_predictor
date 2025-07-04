// High-Performance Cache Service with Redis Integration
// Provides multi-layer caching for NFL Predictor application

import { Redis } from 'ioredis';

// Cache configuration and types
export type CacheStats = {
  hitRate: number;
  missRate: number;
  totalHits: number;
  totalMisses: number;
  cacheSize: number;
  memoryUsage: number;
  uptime: number;
};

export type CacheOptions = {
  ttl?: number; // Time to live in seconds
  tags?: string[]; // Tags for group invalidation
  compress?: boolean; // Compress large objects
  serialize?: boolean; // Custom serialization
};

export type CacheKey = {
  // Player-related keys
  player: (id: string) => string;
  playerStats: (id: string, season: number, week?: number) => string;
  playerInjuries: (id: string, season: number) => string;
  playerTransactions: (id: string, limit?: number) => string;
  
  // Rankings and predictions
  rankings: (position: string, week: number, scoring: string, limit: number) => string;
  batchRankings: (positions: string[], week: number, scoring: string, limit: number) => string;
  projections: (position: string, week: number, scoring: string) => string;
  
  // Team and league data
  teamRoster: (team: string, position?: string) => string;
  depthChart: (team: string, week: number, season: number, position?: string) => string;
  injuries: (week: number, season: number) => string;
  weekStats: (week: number, season: number, position?: string) => string;
  
  // ML and analysis
  mlPredictions: (playerId: string, week: number, modelVersion: string) => string;
  boomBustAnalysis: (position: string, week: number) => string;
  matchupAnalysis: (team1: string, team2: string, week: number) => string;
};

class CacheService {
  private redis: Redis | null = null;
  private inMemoryCache: Map<string, { data: any; expiry: number; tags: string[] }> = new Map();
  private stats = {
    hits: 0,
    misses: 0,
    startTime: Date.now()
  };
  
  // Cache TTL defaults (in seconds)
  private readonly DEFAULT_TTL = {
    player: 86400,        // 24 hours - player info rarely changes
    playerStats: 14400,   // 4 hours - stats change during games
    rankings: 1800,       // 30 minutes - rankings update frequently
    injuries: 7200,       // 2 hours - injury reports update regularly
    depthChart: 21600,    // 6 hours - depth charts change weekly
    projections: 3600,    // 1 hour - ML predictions update hourly
    teamData: 43200,      // 12 hours - team data semi-static
    historical: 604800    // 1 week - historical data is immutable
  };

  constructor() {
    this.initializeRedis();
  }

  private async initializeRedis(): Promise<void> {
    try {
      // Try to connect to Redis if available
      const redisUrl = process.env.REDIS_URL || 'redis://localhost:6379';
      this.redis = new Redis(redisUrl, {
        maxRetriesPerRequest: 3,
        lazyConnect: true,
        connectTimeout: 10000,
        commandTimeout: 5000
      });

      this.redis.on('error', (error: any) => {
        console.warn('Redis connection error, falling back to in-memory cache:', error);
        this.redis = null;
      });

      this.redis.on('connect', () => {
        console.log('✅ Redis cache connected successfully');
      });

      // Test connection
      await this.redis.ping();
    } catch (error) {
      console.warn('Redis not available, using in-memory cache only:', error);
      this.redis = null;
    }
  }

  // Cache key generators
  readonly keys: CacheKey = {
    player: (id: string) => `nfl:player:${id}`,
    playerStats: (id: string, season: number, week?: number) => 
      `nfl:player:${id}:stats:${season}${week ? `:w${week}` : ''}`,
    playerInjuries: (id: string, season: number) => 
      `nfl:player:${id}:injuries:${season}`,
    playerTransactions: (id: string, limit = 10) => 
      `nfl:player:${id}:transactions:${limit}`,
    
    rankings: (position: string, week: number, scoring: string, limit: number) => 
      `nfl:rankings:${position}:w${week}:${scoring}:${limit}`,
    batchRankings: (positions: string[], week: number, scoring: string, limit: number) => 
      `nfl:batch:${positions.sort().join(',')}:w${week}:${scoring}:${limit}`,
    projections: (position: string, week: number, scoring: string) => 
      `nfl:proj:${position}:w${week}:${scoring}`,
    
    teamRoster: (team: string, position?: string) => 
      `nfl:team:${team}:roster${position ? `:${position}` : ''}`,
    depthChart: (team: string, week: number, season: number, position?: string) => 
      `nfl:depth:${team}:${season}:w${week}${position ? `:${position}` : ''}`,
    injuries: (week: number, season: number) => 
      `nfl:injuries:${season}:w${week}`,
    weekStats: (week: number, season: number, position?: string) => 
      `nfl:stats:${season}:w${week}${position ? `:${position}` : ''}`,
    
    mlPredictions: (playerId: string, week: number, modelVersion: string) => 
      `nfl:ml:${playerId}:w${week}:${modelVersion}`,
    boomBustAnalysis: (position: string, week: number) => 
      `nfl:boom:${position}:w${week}`,
    matchupAnalysis: (team1: string, team2: string, week: number) => 
      `nfl:matchup:${[team1, team2].sort().join('v')}:w${week}`
  };

  /**
   * Get value from cache
   */
  async get<T>(key: string): Promise<T | null> {
    try {
      // Try Redis first
      if (this.redis) {
        const value = await this.redis.get(key);
        if (value !== null) {
          this.stats.hits++;
          return JSON.parse(value) as T;
        }
      }

      // Fallback to in-memory cache
      const memoryItem = this.inMemoryCache.get(key);
      if (memoryItem && memoryItem.expiry > Date.now()) {
        this.stats.hits++;
        return memoryItem.data as T;
      }

      // Remove expired items
      if (memoryItem) {
        this.inMemoryCache.delete(key);
      }

      this.stats.misses++;
      return null;
    } catch (error) {
      console.error('Cache get error:', error);
      this.stats.misses++;
      return null;
    }
  }

  /**
   * Set value in cache
   */
  async set<T>(key: string, value: T, options: CacheOptions = {}): Promise<void> {
    try {
      const ttl = options.ttl || this.getDefaultTTL(key);
      const serializedValue = JSON.stringify(value);

      // Store in Redis if available
      if (this.redis) {
        await this.redis.setex(key, ttl, serializedValue);
      }

      // Always store in memory cache as backup
      this.inMemoryCache.set(key, {
        data: value,
        expiry: Date.now() + (ttl * 1000),
        tags: options.tags || []
      });

      // Prevent memory cache from growing too large
      if (this.inMemoryCache.size > 1000) {
        await this.cleanupMemoryCache();
      }
    } catch (error) {
      console.error('Cache set error:', error);
    }
  }

  /**
   * Delete specific key from cache
   */
  async del(key: string): Promise<void> {
    try {
      if (this.redis) {
        await this.redis.del(key);
      }
      this.inMemoryCache.delete(key);
    } catch (error) {
      console.error('Cache delete error:', error);
    }
  }

  /**
   * Invalidate cache by pattern
   */
  async invalidatePattern(pattern: string): Promise<void> {
    try {
      // Redis pattern invalidation
      if (this.redis) {
        const keys = await this.redis.keys(pattern);
        if (keys.length > 0) {
          await this.redis.del(...keys);
        }
      }

      // Memory cache pattern invalidation
      const regex = new RegExp(pattern.replace(/\*/g, '.*'));
      for (const key of this.inMemoryCache.keys()) {
        if (regex.test(key)) {
          this.inMemoryCache.delete(key);
        }
      }
    } catch (error) {
      console.error('Cache pattern invalidation error:', error);
    }
  }

  /**
   * Invalidate cache by tags
   */
  async invalidateByTags(tags: string[]): Promise<void> {
    try {
      // For Redis, we'd need a more sophisticated tagging system
      // For now, implement for memory cache
      for (const [key, item] of this.inMemoryCache.entries()) {
        if (item.tags.some(tag => tags.includes(tag))) {
          this.inMemoryCache.delete(key);
        }
      }
    } catch (error) {
      console.error('Cache tag invalidation error:', error);
    }
  }

  /**
   * Warm up cache with commonly accessed data
   */
  async warmup(warmupData: Record<string, any>): Promise<void> {
    try {
      console.log('🔥 Starting cache warmup...');
      const warmupPromises = Object.entries(warmupData).map(([key, value]) => 
        this.set(key, value, { ttl: this.getDefaultTTL(key) })
      );
      
      await Promise.allSettled(warmupPromises);
      console.log(`✅ Cache warmup completed: ${Object.keys(warmupData).length} items cached`);
    } catch (error) {
      console.error('Cache warmup error:', error);
    }
  }

  /**
   * Get cache statistics
   */
  async getStats(): Promise<CacheStats> {
    const total = this.stats.hits + this.stats.misses;
    const hitRate = total > 0 ? (this.stats.hits / total) * 100 : 0;
    const uptime = (Date.now() - this.stats.startTime) / 1000;

    if (this.redis) {
      try {
        await this.redis.info('memory');
      } catch (error) {
        console.warn('Could not get Redis stats:', error);
      }
    }

    return {
      hitRate: Math.round(hitRate * 100) / 100,
      missRate: Math.round((100 - hitRate) * 100) / 100,
      totalHits: this.stats.hits,
      totalMisses: this.stats.misses,
      cacheSize: this.inMemoryCache.size,
      memoryUsage: this.calculateMemoryUsage(),
      uptime: Math.round(uptime)
    };
  }

  /**
   * Clear all caches
   */
  async clearAll(): Promise<void> {
    try {
      if (this.redis) {
        await this.redis.flushdb();
      }
      this.inMemoryCache.clear();
      this.stats.hits = 0;
      this.stats.misses = 0;
      console.log('🧹 All caches cleared');
    } catch (error) {
      console.error('Cache clear error:', error);
    }
  }

  /**
   * Health check for cache service
   */
  async healthCheck(): Promise<boolean> {
    try {
      // Test Redis connection
      if (this.redis) {
        await this.redis.ping();
      }

      // Test memory cache
      const testKey = 'health:test';
      const testValue = { test: true, timestamp: Date.now() };
      await this.set(testKey, testValue, { ttl: 10 });
      
      const retrieved = await this.get<{ test: boolean; timestamp: number }>(testKey);
      await this.del(testKey);
      
      return retrieved !== null && retrieved?.test === true;
    } catch (error) {
      console.error('Cache health check failed:', error);
      return false;
    }
  }

  // Private helper methods
  private getDefaultTTL(key: string): number {
    if (key.includes(':player:') && key.includes(':stats:')) return this.DEFAULT_TTL.playerStats;
    if (key.includes(':player:')) return this.DEFAULT_TTL.player;
    if (key.includes(':rankings:')) return this.DEFAULT_TTL.rankings;
    if (key.includes(':injuries:')) return this.DEFAULT_TTL.injuries;
    if (key.includes(':depth:')) return this.DEFAULT_TTL.depthChart;
    if (key.includes(':proj:') || key.includes(':ml:')) return this.DEFAULT_TTL.projections;
    if (key.includes(':team:')) return this.DEFAULT_TTL.teamData;
    
    return this.DEFAULT_TTL.playerStats; // Default fallback
  }

  private async cleanupMemoryCache(): Promise<void> {
    const now = Date.now();
    let cleaned = 0;
    
    for (const [key, item] of this.inMemoryCache.entries()) {
      if (item.expiry <= now) {
        this.inMemoryCache.delete(key);
        cleaned++;
      }
    }

    // If still too large, remove oldest items
    if (this.inMemoryCache.size > 800) {
      const entries = Array.from(this.inMemoryCache.entries())
        .sort((a, b) => a[1].expiry - b[1].expiry)
        .slice(0, this.inMemoryCache.size - 800);
      
      entries.forEach(([key]) => this.inMemoryCache.delete(key));
    }
    
    if (cleaned > 0) {
      console.log(`🧹 Cleaned ${cleaned} expired items from memory cache`);
    }
  }

  private calculateMemoryUsage(): number {
    // Rough estimation of memory usage in MB
    let totalSize = 0;
    for (const [key, item] of this.inMemoryCache.entries()) {
      totalSize += key.length * 2; // UTF-16 characters
      totalSize += JSON.stringify(item.data).length * 2;
      totalSize += item.tags.join('').length * 2;
    }
    return Math.round(totalSize / 1024 / 1024 * 100) / 100; // MB
  }

  /**
   * Disconnect from Redis (cleanup)
   */
  async disconnect(): Promise<void> {
    if (this.redis) {
      await this.redis.quit();
      this.redis = null;
    }
  }
}

// Export singleton instance
export const cacheService = new CacheService();