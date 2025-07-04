// Cache Service Tests - TDD for high-performance caching
// Following CLAUDE.md: Test behavior, not implementation

import { cacheService } from './cache-service';

describe('CacheService', () => {
  beforeEach(async () => {
    // Clear cache before each test
    await cacheService.clearAll();
  });

  afterAll(async () => {
    // Cleanup connections
    await cacheService.disconnect();
  });

  describe('Basic caching operations', () => {
    it('should store and retrieve values correctly', async () => {
      const testKey = 'test:basic';
      const testValue = { message: 'hello', number: 42 };

      await cacheService.set(testKey, testValue);
      const retrieved = await cacheService.get(testKey);

      expect(retrieved).toEqual(testValue);
    });

    it('should return null for non-existent keys', async () => {
      const result = await cacheService.get('nonexistent:key');
      expect(result).toBeNull();
    });

    it('should respect TTL and expire values', async () => {
      const testKey = 'test:ttl';
      const testValue = { expiring: true };

      // Set with very short TTL
      await cacheService.set(testKey, testValue, { ttl: 1 });
      
      // Should exist immediately
      const immediate = await cacheService.get(testKey);
      expect(immediate).toEqual(testValue);

      // Wait for expiration
      await new Promise(resolve => setTimeout(resolve, 1100));
      
      // Should be expired
      const expired = await cacheService.get(testKey);
      expect(expired).toBeNull();
    });

    it('should delete values correctly', async () => {
      const testKey = 'test:delete';
      const testValue = { toDelete: true };

      await cacheService.set(testKey, testValue);
      expect(await cacheService.get(testKey)).toEqual(testValue);

      await cacheService.del(testKey);
      expect(await cacheService.get(testKey)).toBeNull();
    });
  });

  describe('Cache key generators', () => {
    it('should generate correct player cache keys', () => {
      const playerId = 'player123';
      const key = cacheService.keys.player(playerId);
      expect(key).toBe('nfl:player:player123');
    });

    it('should generate correct rankings cache keys', () => {
      const key = cacheService.keys.rankings('QB', 1, 'half_ppr', 10);
      expect(key).toBe('nfl:rankings:QB:w1:half_ppr:10');
    });

    it('should generate correct batch rankings cache keys', () => {
      const positions = ['QB', 'RB', 'WR'];
      const key = cacheService.keys.batchRankings(positions, 1, 'ppr', 20);
      expect(key).toBe('nfl:batch:QB,RB,WR:w1:ppr:20');
    });

    it('should generate correct player stats cache keys', () => {
      const key = cacheService.keys.playerStats('player123', 2024, 5);
      expect(key).toBe('nfl:player:player123:stats:2024:w5');
      
      const seasonKey = cacheService.keys.playerStats('player123', 2024);
      expect(seasonKey).toBe('nfl:player:player123:stats:2024');
    });
  });

  describe('Pattern invalidation', () => {
    it('should invalidate cache by pattern', async () => {
      // Set multiple related keys
      await cacheService.set('nfl:player:123:stats:2024', { week: 1 });
      await cacheService.set('nfl:player:123:stats:2025', { week: 1 });
      await cacheService.set('nfl:player:456:stats:2024', { week: 1 });
      await cacheService.set('nfl:team:LAR:roster', { players: [] });

      // Verify they exist
      expect(await cacheService.get('nfl:player:123:stats:2024')).toBeTruthy();
      expect(await cacheService.get('nfl:player:456:stats:2024')).toBeTruthy();
      expect(await cacheService.get('nfl:team:LAR:roster')).toBeTruthy();

      // Invalidate player 123 stats
      await cacheService.invalidatePattern('nfl:player:123:stats:*');

      // Player 123 stats should be gone, others remain
      expect(await cacheService.get('nfl:player:123:stats:2024')).toBeNull();
      expect(await cacheService.get('nfl:player:123:stats:2025')).toBeNull();
      expect(await cacheService.get('nfl:player:456:stats:2024')).toBeTruthy();
      expect(await cacheService.get('nfl:team:LAR:roster')).toBeTruthy();
    });

    it('should invalidate cache by tags', async () => {
      // Set values with tags
      await cacheService.set('key1', { data: 1 }, { tags: ['week:1', 'position:QB'] });
      await cacheService.set('key2', { data: 2 }, { tags: ['week:1', 'position:RB'] });
      await cacheService.set('key3', { data: 3 }, { tags: ['week:2', 'position:QB'] });

      // Verify they exist
      expect(await cacheService.get('key1')).toBeTruthy();
      expect(await cacheService.get('key2')).toBeTruthy();
      expect(await cacheService.get('key3')).toBeTruthy();

      // Invalidate by week:1 tag
      await cacheService.invalidateByTags(['week:1']);

      // Week 1 entries should be gone, week 2 remains
      expect(await cacheService.get('key1')).toBeNull();
      expect(await cacheService.get('key2')).toBeNull();
      expect(await cacheService.get('key3')).toBeTruthy();
    });
  });

  describe('Cache statistics', () => {
    it('should track hit and miss rates correctly', async () => {
      // Clear stats by getting initial state
      await cacheService.getStats();

      // Generate some hits and misses
      await cacheService.set('hit:test', { value: 1 });
      
      // These should be cache hits
      await cacheService.get('hit:test');
      await cacheService.get('hit:test');
      
      // These should be cache misses
      await cacheService.get('miss:test1');
      await cacheService.get('miss:test2');

      const stats = await cacheService.getStats();
      
      // Should have some hits and misses
      expect(stats.totalHits).toBeGreaterThan(0);
      expect(stats.totalMisses).toBeGreaterThan(0);
      expect(stats.hitRate).toBeGreaterThan(0);
      expect(stats.missRate).toBeGreaterThan(0);
      expect(stats.hitRate + stats.missRate).toBeCloseTo(100, 1);
    });

    it('should track cache size', async () => {
      const initialStats = await cacheService.getStats();
      const initialSize = initialStats.cacheSize;

      // Add some items
      await cacheService.set('size:test1', { data: 1 });
      await cacheService.set('size:test2', { data: 2 });

      const newStats = await cacheService.getStats();
      expect(newStats.cacheSize).toBeGreaterThanOrEqual(initialSize + 1);
    });
  });

  describe('Cache warmup', () => {
    it('should warm up cache with provided data', async () => {
      const warmupData = {
        'warm:key1': { data: 'value1' },
        'warm:key2': { data: 'value2' },
        'warm:key3': { data: 'value3' }
      };

      await cacheService.warmup(warmupData);

      // All warmed up data should be accessible
      for (const [key, expectedValue] of Object.entries(warmupData)) {
        const retrieved = await cacheService.get(key);
        expect(retrieved).toEqual(expectedValue);
      }
    });
  });

  describe('Health check', () => {
    it('should pass health check when functioning correctly', async () => {
      const isHealthy = await cacheService.healthCheck();
      expect(isHealthy).toBe(true);
    });
  });

  describe('Error handling', () => {
    it('should handle cache errors gracefully', async () => {
      // Test with invalid key patterns that might cause errors
      const result = await cacheService.get('');
      expect(result).toBeNull();
    });

    it('should not throw errors when setting invalid data', async () => {
      // Should handle various data types
      await expect(cacheService.set('test:null', null)).resolves.not.toThrow();
      await expect(cacheService.set('test:undefined', undefined)).resolves.not.toThrow();
      await expect(cacheService.set('test:function', () => {})).resolves.not.toThrow();
    });
  });

  describe('Performance characteristics', () => {
    it('should handle concurrent operations', async () => {
      const operations = Array.from({ length: 10 }, (_, i) => 
        cacheService.set(`concurrent:${i}`, { index: i })
      );

      await Promise.all(operations);

      // Verify all were stored
      for (let i = 0; i < 10; i++) {
        const value = await cacheService.get(`concurrent:${i}`);
        expect(value).toEqual({ index: i });
      }
    });

    it('should handle large objects efficiently', async () => {
      const largeObject = {
        data: Array.from({ length: 1000 }, (_, i) => ({
          id: i,
          name: `Player ${i}`,
          stats: Array.from({ length: 17 }, (_, week) => ({
            week: week + 1,
            points: Math.random() * 30
          }))
        }))
      };

      const startTime = Date.now();
      await cacheService.set('large:object', largeObject);
      const retrieved = await cacheService.get('large:object');
      const endTime = Date.now();

      expect(retrieved).toEqual(largeObject);
      expect(endTime - startTime).toBeLessThan(1000); // Should complete within 1 second
    });
  });

  describe('Memory management', () => {
    it('should handle memory cleanup appropriately', async () => {
      // Fill cache with many items
      const items = Array.from({ length: 50 }, (_, i) => 
        cacheService.set(`memory:test:${i}`, { data: `value${i}` }, { ttl: 1 })
      );

      await Promise.all(items);

      const beforeStats = await cacheService.getStats();
      expect(beforeStats.cacheSize).toBeGreaterThan(40);

      // Wait for expiration
      await new Promise(resolve => setTimeout(resolve, 1100));

      // Access a key to trigger cleanup
      await cacheService.get('memory:test:0');

      const afterStats = await cacheService.getStats();
      // Cache size should be significantly reduced due to cleanup
      expect(afterStats.cacheSize).toBeLessThan(beforeStats.cacheSize);
    });
  });
});