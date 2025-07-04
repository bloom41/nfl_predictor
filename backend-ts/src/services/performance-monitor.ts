// Performance Monitoring Service
// Tracks database and cache optimization metrics for NFL Predictor

import { cacheService } from './cache-service';
// import { optimizedDatabaseService } from './optimized-database';

export type PerformanceMetric = {
  timestamp: number;
  operation: string;
  duration: number;
  success: boolean;
  cacheHit?: boolean;
  errorMessage?: string;
  metadata?: Record<string, any>;
};

export type PerformanceReport = {
  timeRange: {
    start: Date;
    end: Date;
    durationHours: number;
  };
  database: {
    totalQueries: number;
    averageQueryTime: number;
    slowQueries: number;
    errorRate: number;
    cacheHitRate: number;
  };
  cache: {
    hitRate: number;
    missRate: number;
    totalOperations: number;
    averageResponseTime: number;
    memoryUsage: number;
    errorRate: number;
  };
  api: {
    totalRequests: number;
    averageResponseTime: number;
    errorRate: number;
    throughput: number; // requests per minute
  };
  recommendations: string[];
};

export type OptimizationTarget = {
  metric: string;
  currentValue: number;
  targetValue: number;
  improvementPercent: number;
  status: 'on-track' | 'at-risk' | 'achieved';
};

class PerformanceMonitor {
  private metrics: PerformanceMetric[] = [];
  private readonly MAX_METRICS = 10000;
  private readonly SLOW_QUERY_THRESHOLD = 1000; // 1 second
  
  // Performance targets based on optimization plan
  private readonly TARGETS = {
    averageResponseTime: 100, // 100ms target
    cacheHitRate: 85, // 85% target
    databaseLoadReduction: 80, // 80% reduction target
    errorRate: 0.1 // 0.1% error rate target
  };

  constructor() {
    // Start periodic monitoring
    this.startPeriodicMonitoring();
  }

  /**
   * Record a performance metric
   */
  recordMetric(metric: PerformanceMetric): void {
    this.metrics.push({
      ...metric,
      timestamp: metric.timestamp || Date.now()
    });

    // Cleanup old metrics
    if (this.metrics.length > this.MAX_METRICS) {
      this.metrics = this.metrics.slice(-this.MAX_METRICS);
    }

    // Log slow operations
    if (metric.duration > this.SLOW_QUERY_THRESHOLD) {
      console.warn(`Slow operation detected: ${metric.operation} took ${metric.duration}ms`);
    }
  }

  /**
   * Record database query performance
   */
  recordDatabaseQuery(
    operation: string,
    duration: number,
    success: boolean,
    cacheHit: boolean = false,
    metadata?: Record<string, any>
  ): void {
    const metric: PerformanceMetric = {
      timestamp: Date.now(),
      operation: `db:${operation}`,
      duration,
      success,
      cacheHit,
      metadata: metadata || {}
    };
    this.recordMetric(metric);
  }

  /**
   * Record cache operation performance
   */
  recordCacheOperation(
    operation: string,
    duration: number,
    success: boolean,
    hit?: boolean,
    metadata?: Record<string, any>
  ): void {
    const metric: PerformanceMetric = {
      timestamp: Date.now(),
      operation: `cache:${operation}`,
      duration,
      success,
      cacheHit: hit || false,
      metadata: metadata || {}
    };
    this.recordMetric(metric);
  }

  /**
   * Record API request performance
   */
  recordAPIRequest(
    endpoint: string,
    duration: number,
    success: boolean,
    statusCode?: number,
    metadata?: Record<string, any>
  ): void {
    this.recordMetric({
      timestamp: Date.now(),
      operation: `api:${endpoint}`,
      duration,
      success,
      metadata: { ...metadata, statusCode }
    });
  }

  /**
   * Generate comprehensive performance report
   */
  async generateReport(hoursBack: number = 24): Promise<PerformanceReport> {
    const endTime = Date.now();
    const startTime = endTime - (hoursBack * 60 * 60 * 1000);
    
    const relevantMetrics = this.metrics.filter(m => m.timestamp >= startTime);
    
    // Database metrics
    const dbMetrics = relevantMetrics.filter(m => m.operation.startsWith('db:'));
    const dbQueryTimes = dbMetrics.filter(m => m.success).map(m => m.duration);
    const dbErrors = dbMetrics.filter(m => !m.success).length;
    const dbCacheHits = dbMetrics.filter(m => m.cacheHit).length;
    
    // Cache metrics
    const cacheMetrics = relevantMetrics.filter(m => m.operation.startsWith('cache:'));
    const cacheHits = cacheMetrics.filter(m => m.cacheHit === true).length;
    const cacheMisses = cacheMetrics.filter(m => m.cacheHit === false).length;
    const cacheErrors = cacheMetrics.filter(m => !m.success).length;
    const cacheResponseTimes = cacheMetrics.filter(m => m.success).map(m => m.duration);
    
    // API metrics
    const apiMetrics = relevantMetrics.filter(m => m.operation.startsWith('api:'));
    const apiErrors = apiMetrics.filter(m => !m.success).length;
    const apiResponseTimes = apiMetrics.filter(m => m.success).map(m => m.duration);
    
    // Get cache service stats
    const cacheStats = await cacheService.getStats();
    
    // Database performance metrics integrated into main report

    const report: PerformanceReport = {
      timeRange: {
        start: new Date(startTime),
        end: new Date(endTime),
        durationHours: hoursBack
      },
      database: {
        totalQueries: dbMetrics.length,
        averageQueryTime: this.calculateAverage(dbQueryTimes),
        slowQueries: dbQueryTimes.filter(t => t > this.SLOW_QUERY_THRESHOLD).length,
        errorRate: dbMetrics.length > 0 ? (dbErrors / dbMetrics.length) * 100 : 0,
        cacheHitRate: dbMetrics.length > 0 ? (dbCacheHits / dbMetrics.length) * 100 : 0
      },
      cache: {
        hitRate: cacheStats.hitRate,
        missRate: cacheStats.missRate,
        totalOperations: cacheHits + cacheMisses,
        averageResponseTime: this.calculateAverage(cacheResponseTimes),
        memoryUsage: cacheStats.memoryUsage,
        errorRate: cacheMetrics.length > 0 ? (cacheErrors / cacheMetrics.length) * 100 : 0
      },
      api: {
        totalRequests: apiMetrics.length,
        averageResponseTime: this.calculateAverage(apiResponseTimes),
        errorRate: apiMetrics.length > 0 ? (apiErrors / apiMetrics.length) * 100 : 0,
        throughput: hoursBack > 0 ? (apiMetrics.length / hoursBack / 60) : 0
      },
      recommendations: this.generateRecommendations(relevantMetrics, cacheStats)
    };

    return report;
  }

  /**
   * Get optimization progress against targets
   */
  async getOptimizationProgress(): Promise<OptimizationTarget[]> {
    const report = await this.generateReport(1); // Last hour
    
    const targets: OptimizationTarget[] = [
      {
        metric: 'Average API Response Time',
        currentValue: report.api.averageResponseTime,
        targetValue: this.TARGETS.averageResponseTime,
        improvementPercent: this.calculateImprovement(
          report.api.averageResponseTime,
          this.TARGETS.averageResponseTime,
          'lower'
        ),
        status: this.getTargetStatus(
          report.api.averageResponseTime,
          this.TARGETS.averageResponseTime,
          'lower'
        )
      },
      {
        metric: 'Cache Hit Rate',
        currentValue: report.cache.hitRate,
        targetValue: this.TARGETS.cacheHitRate,
        improvementPercent: this.calculateImprovement(
          report.cache.hitRate,
          this.TARGETS.cacheHitRate,
          'higher'
        ),
        status: this.getTargetStatus(
          report.cache.hitRate,
          this.TARGETS.cacheHitRate,
          'higher'
        )
      },
      {
        metric: 'Database Error Rate',
        currentValue: report.database.errorRate,
        targetValue: this.TARGETS.errorRate,
        improvementPercent: this.calculateImprovement(
          report.database.errorRate,
          this.TARGETS.errorRate,
          'lower'
        ),
        status: this.getTargetStatus(
          report.database.errorRate,
          this.TARGETS.errorRate,
          'lower'
        )
      },
      {
        metric: 'API Error Rate',
        currentValue: report.api.errorRate,
        targetValue: this.TARGETS.errorRate,
        improvementPercent: this.calculateImprovement(
          report.api.errorRate,
          this.TARGETS.errorRate,
          'lower'
        ),
        status: this.getTargetStatus(
          report.api.errorRate,
          this.TARGETS.errorRate,
          'lower'
        )
      }
    ];

    return targets;
  }

  /**
   * Get real-time performance metrics
   */
  getRealTimeMetrics(): {
    last5MinuteMetrics: PerformanceMetric[];
    currentCacheHitRate: number;
    averageResponseTime: number;
    errorCount: number;
  } {
    const fiveMinutesAgo = Date.now() - (5 * 60 * 1000);
    const recentMetrics = this.metrics.filter(m => m.timestamp >= fiveMinutesAgo);
    
    const successfulRequests = recentMetrics.filter(m => m.success);
    const cacheHits = recentMetrics.filter(m => m.cacheHit === true).length;
    const cacheOperations = recentMetrics.filter(m => m.cacheHit !== undefined).length;
    const errors = recentMetrics.filter(m => !m.success).length;
    
    return {
      last5MinuteMetrics: recentMetrics,
      currentCacheHitRate: cacheOperations > 0 ? (cacheHits / cacheOperations) * 100 : 0,
      averageResponseTime: this.calculateAverage(successfulRequests.map(m => m.duration)),
      errorCount: errors
    };
  }

  /**
   * Check if performance alerts should be triggered
   */
  checkPerformanceAlerts(): {
    alerts: Array<{
      severity: 'warning' | 'critical';
      message: string;
      metric: string;
      value: number;
      threshold: number;
    }>;
  } {
    const realTimeMetrics = this.getRealTimeMetrics();
    const alerts: any[] = [];

    // Check response time
    if (realTimeMetrics.averageResponseTime > this.TARGETS.averageResponseTime * 2) {
      alerts.push({
        severity: 'critical',
        message: 'Average response time is critically high',
        metric: 'response_time',
        value: realTimeMetrics.averageResponseTime,
        threshold: this.TARGETS.averageResponseTime * 2
      });
    } else if (realTimeMetrics.averageResponseTime > this.TARGETS.averageResponseTime * 1.5) {
      alerts.push({
        severity: 'warning',
        message: 'Average response time is elevated',
        metric: 'response_time',
        value: realTimeMetrics.averageResponseTime,
        threshold: this.TARGETS.averageResponseTime * 1.5
      });
    }

    // Check cache hit rate
    if (realTimeMetrics.currentCacheHitRate < this.TARGETS.cacheHitRate * 0.7) {
      alerts.push({
        severity: 'critical',
        message: 'Cache hit rate is critically low',
        metric: 'cache_hit_rate',
        value: realTimeMetrics.currentCacheHitRate,
        threshold: this.TARGETS.cacheHitRate * 0.7
      });
    } else if (realTimeMetrics.currentCacheHitRate < this.TARGETS.cacheHitRate * 0.85) {
      alerts.push({
        severity: 'warning',
        message: 'Cache hit rate is below target',
        metric: 'cache_hit_rate',
        value: realTimeMetrics.currentCacheHitRate,
        threshold: this.TARGETS.cacheHitRate * 0.85
      });
    }

    // Check error count
    if (realTimeMetrics.errorCount > 10) {
      alerts.push({
        severity: 'critical',
        message: 'High error count detected',
        metric: 'error_count',
        value: realTimeMetrics.errorCount,
        threshold: 10
      });
    } else if (realTimeMetrics.errorCount > 5) {
      alerts.push({
        severity: 'warning',
        message: 'Elevated error count',
        metric: 'error_count',
        value: realTimeMetrics.errorCount,
        threshold: 5
      });
    }

    return { alerts };
  }

  // Private helper methods
  private calculateAverage(numbers: number[]): number {
    if (numbers.length === 0) return 0;
    return Math.round(numbers.reduce((sum, n) => sum + n, 0) / numbers.length);
  }

  private calculateImprovement(current: number, target: number, direction: 'higher' | 'lower'): number {
    if (direction === 'higher') {
      return current >= target ? 100 : Math.round((current / target) * 100);
    } else {
      return current <= target ? 100 : Math.round((target / current) * 100);
    }
  }

  private getTargetStatus(current: number, target: number, direction: 'higher' | 'lower'): 'on-track' | 'at-risk' | 'achieved' {
    const improvement = this.calculateImprovement(current, target, direction);
    
    if (improvement >= 100) return 'achieved';
    if (improvement >= 80) return 'on-track';
    return 'at-risk';
  }

  private generateRecommendations(metrics: PerformanceMetric[], cacheStats: any): string[] {
    const recommendations: string[] = [];
    
    const dbMetrics = metrics.filter(m => m.operation.startsWith('db:'));
    // Cache metrics used for analysis
    const apiMetrics = metrics.filter(m => m.operation.startsWith('api:'));
    
    // Database recommendations
    const slowDbQueries = dbMetrics.filter(m => m.duration > this.SLOW_QUERY_THRESHOLD).length;
    if (slowDbQueries > dbMetrics.length * 0.1) {
      recommendations.push('Consider adding database indexes for frequently slow queries');
    }
    
    const dbCacheHitRate = dbMetrics.filter(m => m.cacheHit).length / Math.max(dbMetrics.length, 1) * 100;
    if (dbCacheHitRate < 70) {
      recommendations.push('Increase database query caching to improve performance');
    }
    
    // Cache recommendations
    if (cacheStats.hitRate < 80) {
      recommendations.push('Review cache TTL settings and cache key strategies');
    }
    
    if (cacheStats.memoryUsage > 100) {
      recommendations.push('Monitor cache memory usage and consider implementing cache eviction policies');
    }
    
    // API recommendations
    const avgApiTime = this.calculateAverage(apiMetrics.filter(m => m.success).map(m => m.duration));
    if (avgApiTime > 200) {
      recommendations.push('Optimize API endpoints with longer response times');
    }
    
    const apiErrorRate = apiMetrics.filter(m => !m.success).length / Math.max(apiMetrics.length, 1) * 100;
    if (apiErrorRate > 2) {
      recommendations.push('Investigate and resolve high API error rates');
    }
    
    if (recommendations.length === 0) {
      recommendations.push('Performance is within acceptable ranges - continue monitoring');
    }
    
    return recommendations;
  }

  private startPeriodicMonitoring(): void {
    // Check performance every 5 minutes
    setInterval(async () => {
      const alerts = this.checkPerformanceAlerts();
      if (alerts.alerts.length > 0) {
        console.warn('Performance alerts detected:', alerts.alerts);
      }
    }, 5 * 60 * 1000);
  }

  /**
   * Export metrics for external monitoring systems
   */
  exportMetrics(format: 'json' | 'csv' = 'json'): string {
    if (format === 'json') {
      return JSON.stringify(this.metrics, null, 2);
    } else {
      // CSV export
      const headers = ['timestamp', 'operation', 'duration', 'success', 'cacheHit', 'errorMessage'];
      const csvLines = [headers.join(',')];
      
      this.metrics.forEach(metric => {
        const row = [
          metric.timestamp,
          metric.operation,
          metric.duration,
          metric.success,
          metric.cacheHit || '',
          metric.errorMessage || ''
        ];
        csvLines.push(row.join(','));
      });
      
      return csvLines.join('\n');
    }
  }

  /**
   * Clear old metrics (for maintenance)
   */
  clearOldMetrics(olderThanHours: number = 168): void { // Default 1 week
    const cutoffTime = Date.now() - (olderThanHours * 60 * 60 * 1000);
    this.metrics = this.metrics.filter(m => m.timestamp >= cutoffTime);
    console.log(`Cleared metrics older than ${olderThanHours} hours`);
  }
}

// Export singleton instance
export const performanceMonitor = new PerformanceMonitor();