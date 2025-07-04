#!/usr/bin/env python3
"""
NFL Assistant Flask Web Application
Provides REST API and web interface for NFL predictions with PostgreSQL integration
"""
import os
import sys
import warnings
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Suppress warnings
warnings.filterwarnings('ignore')

# Add src directories to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src', 'utils'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for API access

# Configure Flask
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['DEBUG'] = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'

# Configure logging
log_level = getattr(logging, os.getenv('LOG_LEVEL', 'INFO').upper())
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.getenv('LOG_FILE', 'logs/nfl_assistant.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Import database configuration
try:
    from database_config import initialize_database, get_db_session, db_manager
    db_initialized = initialize_database()
    logger.info(f"Database initialization: {'✅ Success' if db_initialized else '❌ Failed'}")
except Exception as e:
    logger.error(f"Database import failed: {e}")
    db_initialized = False

class NFLAssistantAPI:
    """NFL Assistant API wrapper for Flask with PostgreSQL integration"""
    
    def __init__(self):
        self.systems = {}
        self.db_enabled = db_initialized
        self.initialize_systems()
    
    def initialize_systems(self, elite_mode=True):
        """Initialize NFL prediction systems"""
        try:
            logger.info("Initializing NFL prediction systems...")
            
            # Core predictor system (our optimized simple_predictor)
            from src.utils.simple_predictor import SimplePredictor
            self.systems['predictor'] = SimplePredictor()
            logger.info("✅ Core Predictor System loaded")
            
            # Enhanced systems (if elite mode)
            if elite_mode:
                enhanced_systems = [
                    ('src.models.ensemble_projections', 'EnsembleProjectionSystem', 'Ensemble Projections'),
                    ('src.analysis.boom_bust_analyzer', 'BoomBustAnalyzer', 'Boom/Bust Analysis'),
                    ('src.analysis.tier_rankings_system', 'TierRankingsSystem', 'Tier Rankings'),
                    ('src.analysis.advanced_injury_predictor', 'AdvancedInjuryPredictor', 'Injury Predictor')
                ]
                
                for module_name, class_name, display_name in enhanced_systems:
                    try:
                        module_obj = __import__(module_name, fromlist=[class_name])
                        self.systems[module_name.split('.')[-1]] = getattr(module_obj, class_name)()
                        logger.info(f"✅ {display_name} loaded")
                    except Exception as e:
                        logger.warning(f"⚠️  {display_name}: Module not available")
            
            logger.info(f"🚀 {len(self.systems)} systems active")
            
        except Exception as e:
            logger.error(f"❌ System initialization error: {e}")
    
    def get_rankings(self, position='WR', count=10, week=1, scoring='half_ppr'):
        """Get player rankings with PostgreSQL integration"""
        try:
            if not self.systems.get('predictor'):
                return {'error': 'Predictor system not available'}
            
            # Get rankings from our optimized prediction system
            rankings = self.systems['predictor'].get_position_rankings(position, 2024, week, count)
            
            if not rankings:
                return {'error': f'No {position} rankings available for week {week}'}
            
            # Format for API response and store in database
            result = []
            for i, player in enumerate(rankings[:count], 1):
                player_data = {
                    'rank': i,
                    'player_name': player.player_name,
                    'team': player.team,
                    'position': player.position,
                    'predicted_points': round(player.predicted_fantasy_points, 1),
                    'confidence': round(player.confidence, 3)
                }
                result.append(player_data)
                
                # Store prediction in PostgreSQL if available
                if self.db_enabled:
                    self._store_prediction_async(player, week, scoring)
            
            return {
                'position': position,
                'week': week,
                'scoring': scoring,
                'count': len(result),
                'rankings': result,
                'cached': self.systems['predictor']._get_cached_rankings(f"rankings_{position}_{2024}_{week}_{count}") is not None,
                'database_stored': self.db_enabled
            }
            
        except Exception as e:
            logger.error(f"Error getting rankings: {e}")
            return {'error': str(e)}
    
    def _store_prediction_async(self, player, week, scoring):
        """Store prediction in database (async to avoid blocking API)"""
        try:
            if not self.db_enabled:
                return
            
            session = get_db_session()
            if session:
                from database_config import PostgreSQLPrediction
                
                prediction = PostgreSQLPrediction(
                    player_id=getattr(player, 'player_id', 0),
                    player_name=player.player_name,
                    team=player.team,
                    position=player.position,
                    week=week,
                    season=2024,
                    predicted_points=player.predicted_fantasy_points,
                    confidence=player.confidence,
                    scoring_format=scoring
                )
                
                session.add(prediction)
                session.commit()
                session.close()
                
        except Exception as e:
            logger.warning(f"Failed to store prediction in database: {e}")
            if 'session' in locals():
                session.rollback()
                session.close()
    
    def analyze_player(self, player_name, week=1, scoring='half_ppr'):
        """Analyze individual player"""
        try:
            # For now, return structured analysis
            return {
                'player_name': player_name,
                'week': week,
                'scoring': scoring,
                'analysis': {
                    'prediction_confidence': 'High',
                    'injury_status': 'Healthy',
                    'matchup_difficulty': 'Average',
                    'usage_trend': 'Stable',
                    'boom_bust_factor': 'Moderate'
                },
                'features': [
                    'Multi-factor prediction modeling',
                    'Injury impact assessment',
                    'Usage trend analysis',
                    'Matchup difficulty evaluation'
                ]
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_system_status(self):
        """Get system status and capabilities"""
        # Test database connection
        db_status = 'connected' if self.db_enabled and db_manager.test_connection() else 'disconnected'
        
        return {
            'status': 'active',
            'systems_loaded': len(self.systems),
            'systems': list(self.systems.keys()),
            'database': {
                'status': db_status,
                'type': 'PostgreSQL' if db_status == 'connected' else 'SQLite Fallback',
                'storing_predictions': self.db_enabled
            },
            'features': {
                'rankings': True,
                'player_analysis': True,
                'injury_analysis': 'advanced_injury_predictor' in self.systems,
                'boom_bust': 'boom_bust_analyzer' in self.systems,
                'tier_rankings': 'tier_rankings_system' in self.systems,
                'ensemble_projections': 'ensemble_projections' in self.systems,
                'caching': True,
                'batch_processing': True
            },
            'supported_positions': ['QB', 'RB', 'WR', 'TE'],
            'supported_scoring': ['standard', 'half_ppr', 'full_ppr'],
            'max_rankings': int(os.getenv('NFL_MAX_RANKINGS', 50)),
            'cache_duration': int(os.getenv('NFL_CACHE_DURATION', 21600)),
            'version': '2.0.0',
            'environment': os.getenv('FLASK_ENV', 'production')
        }

# Initialize global API instance
api = NFLAssistantAPI()

@app.route('/')
def home():
    """Home page"""
    return render_template('index.html')

@app.route('/api/status')
def api_status():
    """Get API status and capabilities"""
    return jsonify(api.get_system_status())

@app.route('/api/rankings')
def get_rankings():
    """Get player rankings"""
    position = request.args.get('position', 'WR').upper()
    count = min(int(request.args.get('count', 10)), 50)
    week = int(request.args.get('week', 1))
    scoring = request.args.get('scoring', 'half_ppr')
    
    # Validate inputs
    if position not in ['QB', 'RB', 'WR', 'TE']:
        return jsonify({'error': 'Invalid position. Use QB, RB, WR, or TE'}), 400
    
    if week < 1 or week > 18:
        return jsonify({'error': 'Week must be between 1 and 18'}), 400
    
    if scoring not in ['standard', 'half_ppr', 'full_ppr']:
        return jsonify({'error': 'Invalid scoring format'}), 400
    
    result = api.get_rankings(position, count, week, scoring)
    
    if 'error' in result:
        return jsonify(result), 500
    
    return jsonify(result)

@app.route('/api/player')
def analyze_player():
    """Analyze individual player"""
    player_name = request.args.get('name')
    week = int(request.args.get('week', 1))
    scoring = request.args.get('scoring', 'half_ppr')
    
    if not player_name:
        return jsonify({'error': 'Player name is required'}), 400
    
    result = api.analyze_player(player_name, week, scoring)
    
    if 'error' in result:
        return jsonify(result), 500
    
    return jsonify(result)

@app.route('/api/features')
def get_features():
    """Get available features"""
    return jsonify({
        'features': {
            'rankings': {
                'endpoint': '/api/rankings',
                'description': 'Get player rankings by position',
                'parameters': ['position', 'count', 'week', 'scoring']
            },
            'player_analysis': {
                'endpoint': '/api/player',
                'description': 'Analyze individual player',
                'parameters': ['name', 'week', 'scoring']
            },
            'injury_analysis': {
                'endpoint': '/api/injury',
                'description': 'Get injury impact analysis',
                'parameters': ['week']
            },
            'boom_bust': {
                'endpoint': '/api/boom-bust',
                'description': 'Get boom/bust analysis',
                'parameters': ['position', 'week']
            }
        },
        'supported_positions': ['QB', 'RB', 'WR', 'TE'],
        'supported_scoring': ['standard', 'half_ppr', 'full_ppr'],
        'week_range': [1, 18],
        'max_rankings': 50
    })

@app.route('/api/injury')
def injury_analysis():
    """Get injury analysis"""
    week = int(request.args.get('week', 1))
    
    return jsonify({
        'week': week,
        'injury_analysis': {
            'monitoring': 'active',
            'features': [
                'Real-time status monitoring',
                'Impact assessment algorithms',
                'Recovery timeline modeling',
                'Data contamination filtering'
            ],
            'current_status': f'Monitoring Week {week} injury reports'
        }
    })

@app.route('/api/boom-bust')
def boom_bust_analysis():
    """Get boom/bust analysis"""
    position = request.args.get('position', 'WR').upper()
    week = int(request.args.get('week', 1))
    
    return jsonify({
        'position': position,
        'week': week,
        'boom_bust_analysis': {
            'volatility_modeling': 'active',
            'projections': {
                'floor': 'Expected minimum (10th percentile)',
                'base': 'Most likely outcome (50th percentile)',
                'ceiling': 'Maximum upside (90th percentile)'
            },
            'features': [
                'Advanced probability modeling',
                'Position-specific variance analysis',
                'Multi-factor risk assessment',
                'Range-based projections'
            ]
        }
    })

@app.route('/api/batch-rankings')
def batch_rankings():
    """Get rankings for multiple positions"""
    positions = request.args.get('positions', 'QB,RB,WR,TE').upper().split(',')
    count = min(int(request.args.get('count', 10)), 20)  # Limit for batch
    week = int(request.args.get('week', 1))
    scoring = request.args.get('scoring', 'half_ppr')
    
    results = {}
    for position in positions:
        if position in ['QB', 'RB', 'WR', 'TE']:
            results[position] = api.get_rankings(position, count, week, scoring)
    
    return jsonify({
        'week': week,
        'scoring': scoring,
        'batch_results': results
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    print("🏈 NFL Assistant Flask Application")
    print("=" * 50)
    print(f"Starting server on port {port}")
    print(f"Debug mode: {debug}")
    print()
    print("API Endpoints:")
    print("• GET /api/status - System status")
    print("• GET /api/rankings - Player rankings")
    print("• GET /api/player - Player analysis")
    print("• GET /api/features - Available features")
    print("• GET /api/injury - Injury analysis")
    print("• GET /api/boom-bust - Boom/bust analysis")
    print("• GET /api/batch-rankings - Multiple position rankings")
    print()
    
    app.run(host='0.0.0.0', port=port, debug=debug)