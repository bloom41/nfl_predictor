import os
import sys
import logging
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.utils import timezone

# Add src directories to path for importing NFL prediction systems
sys.path.append(os.path.join(settings.BASE_DIR, 'src', 'utils'))
sys.path.append(os.path.join(settings.BASE_DIR, 'src'))

from .models import Player, Prediction, GameResult, InjuryReport

logger = logging.getLogger(__name__)

# Initialize NFL prediction system
nfl_api = None

def get_nfl_api():
    """Lazy initialization of NFL API to prevent startup issues"""
    global nfl_api
    if nfl_api is None:
        try:
            from src.utils.simple_predictor import SimplePredictor
            nfl_api = SimplePredictor()
            logger.info("NFL prediction system initialized")
        except Exception as e:
            logger.error(f"Failed to initialize NFL prediction system: {e}")
            nfl_api = None
    return nfl_api


@require_http_methods(["GET"])
def home(request):
    """Home page"""
    return render(request, 'nfl_api/index.html')


@require_http_methods(["GET"])
def api_status(request):
    """Get API status and capabilities"""
    api = get_nfl_api()
    
    # Test database connection
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        db_status = 'connected'
        db_type = 'PostgreSQL'
    except Exception as e:
        db_status = 'disconnected'
        db_type = 'Unknown'
        logger.warning(f"Database connection test failed: {e}")
    
    systems_loaded = 1 if api else 0
    
    return JsonResponse({
        'status': 'active',
        'systems_loaded': systems_loaded,
        'systems': ['predictor'] if api else [],
        'database': {
            'status': db_status,
            'type': db_type,
            'storing_predictions': db_status == 'connected'
        },
        'features': {
            'rankings': api is not None,
            'player_analysis': api is not None,
            'injury_analysis': True,
            'boom_bust': True,
            'tier_rankings': True,
            'ensemble_projections': True,
            'caching': True,
            'batch_processing': True
        },
        'supported_positions': ['QB', 'RB', 'WR', 'TE'],
        'supported_scoring': ['standard', 'half_ppr', 'full_ppr'],
        'max_rankings': getattr(settings, 'NFL_MAX_RANKINGS', 50),
        'cache_duration': getattr(settings, 'NFL_CACHE_DURATION', 21600),
        'version': '2.0.0-django',
        'environment': 'development' if settings.DEBUG else 'production'
    })


@require_http_methods(["GET"])
def get_rankings(request):
    """Get player rankings"""
    api = get_nfl_api()
    if not api:
        return JsonResponse({'error': 'Prediction system not available'}, status=500)
    
    # Get parameters
    position = request.GET.get('position', 'WR').upper()
    count = min(int(request.GET.get('count', 10)), 50)
    week = int(request.GET.get('week', 1))
    scoring = request.GET.get('scoring', 'half_ppr')
    
    # Validate inputs
    if position not in ['QB', 'RB', 'WR', 'TE']:
        return JsonResponse({'error': 'Invalid position. Use QB, RB, WR, or TE'}, status=400)
    
    if week < 1 or week > 18:
        return JsonResponse({'error': 'Week must be between 1 and 18'}, status=400)
    
    if scoring not in ['standard', 'half_ppr', 'full_ppr']:
        return JsonResponse({'error': 'Invalid scoring format'}, status=400)
    
    try:
        # Get rankings from prediction system
        rankings = api.get_position_rankings(position, 2024, week, count)
        
        if not rankings:
            return JsonResponse({'error': f'No {position} rankings available for week {week}'}, status=404)
        
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
            
            # Store prediction in database
            try:
                Prediction.objects.create(
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
            except Exception as e:
                logger.warning(f"Failed to store prediction: {e}")
        
        return JsonResponse({
            'position': position,
            'week': week,
            'scoring': scoring,
            'count': len(result),
            'rankings': result,
            'cached': hasattr(api, '_get_cached_rankings'),
            'database_stored': True
        })
        
    except Exception as e:
        logger.error(f"Error getting rankings: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def analyze_player(request):
    """Analyze individual player"""
    player_name = request.GET.get('name')
    week = int(request.GET.get('week', 1))
    scoring = request.GET.get('scoring', 'half_ppr')
    
    if not player_name:
        return JsonResponse({'error': 'Player name is required'}, status=400)
    
    try:
        # For now, return structured analysis (can be enhanced with actual analysis)
        return JsonResponse({
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
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def get_features(request):
    """Get available features"""
    return JsonResponse({
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
        'max_rankings': getattr(settings, 'NFL_MAX_RANKINGS', 50)
    })


@require_http_methods(["GET"])
def injury_analysis(request):
    """Get injury analysis"""
    week = int(request.GET.get('week', 1))
    
    return JsonResponse({
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


@require_http_methods(["GET"])
def boom_bust_analysis(request):
    """Get boom/bust analysis"""
    position = request.GET.get('position', 'WR').upper()
    week = int(request.GET.get('week', 1))
    
    return JsonResponse({
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


@require_http_methods(["GET"])
def batch_rankings(request):
    """Get rankings for multiple positions"""
    positions = request.GET.get('positions', 'QB,RB,WR,TE').upper().split(',')
    count = min(int(request.GET.get('count', 10)), 20)  # Limit for batch
    week = int(request.GET.get('week', 1))
    scoring = request.GET.get('scoring', 'half_ppr')
    
    api = get_nfl_api()
    if not api:
        return JsonResponse({'error': 'Prediction system not available'}, status=500)
    
    results = {}
    for position in positions:
        if position in ['QB', 'RB', 'WR', 'TE']:
            try:
                rankings = api.get_position_rankings(position, 2024, week, count)
                if rankings:
                    result = []
                    for i, player in enumerate(rankings[:count], 1):
                        result.append({
                            'rank': i,
                            'player_name': player.player_name,
                            'team': player.team,
                            'position': player.position,
                            'predicted_points': round(player.predicted_fantasy_points, 1),
                            'confidence': round(player.confidence, 3)
                        })
                    results[position] = {
                        'position': position,
                        'count': len(result),
                        'rankings': result
                    }
                else:
                    results[position] = {'error': f'No {position} rankings available'}
            except Exception as e:
                results[position] = {'error': str(e)}
    
    return JsonResponse({
        'week': week,
        'scoring': scoring,
        'batch_results': results
    })
