#!/usr/bin/env node
/**
 * NFL Predictor - Quick Predictions CLI
 * TypeScript equivalent of Python prediction scripts
 * 
 * Usage:
 *   npx ts-node scripts/quick-predictions.ts [position] [limit]
 *   npx ts-node scripts/quick-predictions.ts QB 5
 */

import { databaseService } from '../src/services/database';
import { unifiedMLEngine } from '../src/services/unified-ml-engine';
import type { Position } from '../src/shared/schemas/player';

interface PredictionResult {
  player_name: string;
  position: string;
  team: string;
  predicted_points: number;
  confidence: number;
  model_version: string;
}

async function generateQuickPredictions(position?: Position, limit: number = 5): Promise<void> {
  console.log('🏈 NFL Predictor - Quick Predictions');
  console.log('=====================================');
  
  try {
    // Test database connection
    const stats = await databaseService.getDatabaseStats();
    console.log(`📊 Database: ${stats.total_players} players, ${stats.total_stats_records} stats records\n`);

    if (position) {
      // Get predictions for specific position
      console.log(`🎯 Getting ${position} predictions (limit: ${limit})...\n`);
      
      const projections = await unifiedMLEngine.getUnifiedProjections({
        position,
        week: 1,
        season: 2024,
        scoring_format: 'half_ppr',
        limit,
        include_bench_players: false,
        min_confidence: 0.3
      });

      if (projections.projections.length === 0) {
        console.log(`❌ No predictions available for ${position}`);
        console.log('💡 This might be because:');
        console.log('   - Database is empty (run population script)');
        console.log('   - No players meet confidence threshold');
        console.log('   - Position filter too restrictive\n');
        
        // Try to get some players from database directly
        const players = await databaseService.getPlayers({ 
          position, 
          limit: 3,
          include_stats: false 
        });
        
        if (players.length > 0) {
          console.log(`📋 Found ${players.length} ${position} players in database:`);
          players.forEach((player, index) => {
            console.log(`  ${index + 1}. ${player.full_name} (${player.team_id})`);
          });
        } else {
          console.log(`📋 No ${position} players found in database`);
        }
        
        return;
      }

      console.log(`✅ Generated ${projections.projections.length} predictions:\n`);
      
      projections.projections.forEach((proj, index) => {
        console.log(`${index + 1}. ${proj.player_name} (${proj.position})`);
        console.log(`   Team: ${proj.team}`);
        console.log(`   Projected Points: ${proj.predicted_points.toFixed(1)}`);
        console.log(`   Confidence: ${(proj.confidence * 100).toFixed(1)}%`);
        console.log(`   Model: ${proj.model_version}\n`);
      });

    } else {
      // Get predictions for all positions
      console.log(`🎯 Getting predictions for all positions (${limit} each)...\n`);
      
      const positions: Position[] = ['QB', 'RB', 'WR', 'TE'];
      
      for (const pos of positions) {
        console.log(`\n📍 ${pos} PREDICTIONS:`);
        console.log('─'.repeat(30));
        
        const projections = await unifiedMLEngine.getUnifiedProjections({
          position: pos,
          week: 1,
          season: 2024,
          scoring_format: 'half_ppr',
          limit: Math.min(limit, 3), // Limit to 3 per position for overview
          include_bench_players: false,
          min_confidence: 0.3
        });

        if (projections.projections.length === 0) {
          console.log(`❌ No ${pos} predictions available`);
          continue;
        }

        projections.projections.forEach((proj, index) => {
          console.log(`  ${index + 1}. ${proj.player_name}: ${proj.predicted_points.toFixed(1)} pts (${(proj.confidence * 100).toFixed(1)}%)`);
        });
      }
    }

    console.log('\n💡 Elite Features Available:');
    console.log('   - Enhanced ML with Django data integration');
    console.log('   - Real-time injury and transaction monitoring');
    console.log('   - Ensemble modeling with confidence intervals');
    console.log('   - Access via /api/elite/projections endpoint');
    
  } catch (error) {
    console.error('❌ Error generating predictions:', error);
    console.log('\n🔧 Troubleshooting:');
    console.log('   1. Ensure backend server is running (npm start)');
    console.log('   2. Check database connection');
    console.log('   3. Verify Django database is populated');
    console.log('   4. Run: npm run typecheck');
  }
}

async function main() {
  const args = process.argv.slice(2);
  const position = args[0] as Position | undefined;
  const limit = parseInt(args[1]) || 5;

  // Validate position if provided
  if (position && !['QB', 'RB', 'WR', 'TE'].includes(position)) {
    console.error('❌ Invalid position. Use: QB, RB, WR, or TE');
    process.exit(1);
  }

  await generateQuickPredictions(position, limit);
  process.exit(0);
}

// Only run if this file is executed directly
if (require.main === module) {
  main().catch(console.error);
}

export { generateQuickPredictions };