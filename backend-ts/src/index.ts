// NFL Predictor Backend Server Entry Point
// Secure server startup with configuration validation

import { createApp } from './app';
import { configService } from './services/config-init';
import { secretsManager } from './services/secrets-manager';

async function startServer() {
  try {
    console.log('🚀 Starting NFL Predictor Backend...');
    
    // Initialize secure configuration
    const config = await configService.initialize();
    
    // Verify secrets manager health
    const secretsHealthy = await secretsManager.healthCheck();
    if (!secretsHealthy) {
      console.warn('⚠️  Secrets manager health check failed - continuing with environment variables');
    }

    // Create and configure app
    const app = await createApp();
    
    // Print configuration summary
    configService.printConfigSummary();
    
    const server = app.listen(config.server.port, () => {
      console.log(`🚀 NFL Predictor Backend running on port ${config.server.port}`);
      console.log(`📊 Environment: ${config.server.environment}`);
      console.log(`🔗 API Base URL: http://localhost:${config.server.port}/api`);
      
      if (config.server.environment === 'development') {
        console.log(`📋 Available endpoints:`);
        console.log(`  GET  /api/status - Health check`);
        console.log(`  GET  /api/features - API capabilities`);
        console.log(`  GET  /api/rankings/:position - Player rankings`);
        console.log(`  GET  /api/player/:id/analysis - Player analysis`);
        console.log(`  GET  /api/injury - Injury analysis`);
        console.log(`  GET  /api/boom-bust - Volatility analysis`);
        console.log(`  GET  /api/matchup-analysis - Game insights`);
        console.log(`  GET  /api/projections - ML predictions`);
        console.log(`  POST /api/batch-rankings - Batch rankings`);
      }
    });

    // Graceful shutdown handling
    const shutdown = (signal: string) => {
      console.log(`\n🛑 Received ${signal}. Graceful shutdown...`);
      
      // Clear secrets cache for security
      secretsManager.clearCache();
      
      server.close(() => {
        console.log('✅ Server closed successfully');
        process.exit(0);
      });
    };

    process.on('SIGTERM', () => shutdown('SIGTERM'));
    process.on('SIGINT', () => shutdown('SIGINT'));

  } catch (error) {
    console.error('❌ Failed to start server:', error);
    process.exit(1);
  }
}

// Handle uncaught exceptions
process.on('uncaughtException', (error) => {
  console.error('❌ Uncaught Exception:', error);
  process.exit(1);
});

process.on('unhandledRejection', (reason, promise) => {
  console.error('❌ Unhandled Rejection at:', promise, 'reason:', reason);
  process.exit(1);
});

startServer();