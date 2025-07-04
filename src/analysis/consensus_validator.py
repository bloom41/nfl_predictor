import pandas as pd
import numpy as np
import logging
from datetime import datetime
from src.database.database import db
from src.database.models import Player, Prediction
from src.models.prediction_model import NFLPredictionModel

class ConsensusValidator:
    """
    Validates system predictions against expert consensus rankings
    Provides benchmarking and accuracy comparison
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Expert consensus data (would be scraped from multiple sources in production)
        self.expert_rankings = {
            'QB': {
                'Josh Allen': {'rank': 1, 'projected_points': 24.5, 'confidence': 0.95},
                'Patrick Mahomes': {'rank': 2, 'projected_points': 23.8, 'confidence': 0.93},
                'Lamar Jackson': {'rank': 3, 'projected_points': 23.2, 'confidence': 0.90},
                'Jalen Hurts': {'rank': 4, 'projected_points': 22.1, 'confidence': 0.88},
                'Joe Burrow': {'rank': 5, 'projected_points': 21.5, 'confidence': 0.85}
            },
            'RB': {
                'Christian McCaffrey': {'rank': 1, 'projected_points': 26.8, 'confidence': 0.95},
                'Derrick Henry': {'rank': 2, 'projected_points': 24.2, 'confidence': 0.90},
                'Saquon Barkley': {'rank': 3, 'projected_points': 23.1, 'confidence': 0.88},
                'Josh Jacobs': {'rank': 4, 'projected_points': 22.5, 'confidence': 0.85},
                'Austin Ekeler': {'rank': 5, 'projected_points': 21.8, 'confidence': 0.83}
            },
            'WR': {
                'Cooper Kupp': {'rank': 1, 'projected_points': 20.5, 'confidence': 0.92},
                'Davante Adams': {'rank': 2, 'projected_points': 19.8, 'confidence': 0.90},
                'Tyreek Hill': {'rank': 3, 'projected_points': 19.2, 'confidence': 0.88},
                'CeeDee Lamb': {'rank': 4, 'projected_points': 18.7, 'confidence': 0.85},
                'Stefon Diggs': {'rank': 5, 'projected_points': 18.1, 'confidence': 0.83}
            },
            'TE': {
                'Travis Kelce': {'rank': 1, 'projected_points': 15.2, 'confidence': 0.95},
                'Mark Andrews': {'rank': 2, 'projected_points': 13.8, 'confidence': 0.88},
                'George Kittle': {'rank': 3, 'projected_points': 12.9, 'confidence': 0.85},
                'T.J. Hockenson': {'rank': 4, 'projected_points': 11.5, 'confidence': 0.80},
                'Kyle Pitts': {'rank': 5, 'projected_points': 10.8, 'confidence': 0.75}
            }
        }
    
    def validate_weekly_predictions(self, season, week):
        """
        Validate system predictions against expert consensus for a specific week
        """
        try:
            session = db.get_session()
            
            validation_results = {
                'total_compared': 0,
                'rank_correlation': {},
                'point_accuracy': {},
                'system_vs_expert': {},
                'recommendations': []
            }
            
            positions = ['QB', 'RB', 'WR', 'TE']
            
            for position in positions:
                print(f"\\n🔍 Validating {position} predictions against expert consensus...")
                
                # Get system predictions
                system_predictions = self._get_system_predictions(position, season, week, session)
                expert_consensus = self.expert_rankings.get(position, {})
                
                if not system_predictions or not expert_consensus:
                    continue
                
                # Compare rankings and points
                comparison = self._compare_predictions(system_predictions, expert_consensus, position)
                
                validation_results['rank_correlation'][position] = comparison['rank_correlation']
                validation_results['point_accuracy'][position] = comparison['point_accuracy']
                validation_results['system_vs_expert'][position] = comparison['detailed_comparison']
                validation_results['total_compared'] += comparison['players_compared']
                
                # Display results
                self._display_validation_results(position, comparison)
                
            # Generate overall assessment
            overall_assessment = self._generate_overall_assessment(validation_results)
            validation_results['overall_assessment'] = overall_assessment
            
            db.close_session(session)
            return validation_results
            
        except Exception as e:
            self.logger.error(f"Error in validation: {e}")
            if 'session' in locals():
                db.close_session(session)
            return None
    
    def _get_system_predictions(self, position, season, week, session):
        """Get system predictions for comparison"""
        try:
            model = NFLPredictionModel(position)
            players = session.query(Player).filter_by(position=position).limit(10).all()
            
            predictions = []
            for player in players:
                prediction = model.predict_with_feedback_enhancements(player.id, season, week)
                if prediction:
                    fp = prediction['predictions'].get('target_fantasy_points', 0)
                    conf = prediction['confidence']
                    
                    predictions.append({
                        'name': player.name,
                        'projected_points': fp,
                        'confidence': conf
                    })
            
            # Sort by projected points (highest first)
            predictions.sort(key=lambda x: x['projected_points'], reverse=True)
            
            # Add rank
            for i, pred in enumerate(predictions):
                pred['rank'] = i + 1
                
            return predictions
            
        except Exception as e:
            self.logger.error(f"Error getting system predictions: {e}")
            return []
    
    def _compare_predictions(self, system_preds, expert_consensus, position):
        """Compare system predictions with expert consensus"""
        try:
            # Find common players
            system_dict = {pred['name']: pred for pred in system_preds}
            common_players = []
            
            for player_name, expert_data in expert_consensus.items():
                if player_name in system_dict:
                    system_data = system_dict[player_name]
                    common_players.append({
                        'name': player_name,
                        'system_rank': system_data['rank'],
                        'expert_rank': expert_data['rank'],
                        'system_points': system_data['projected_points'],
                        'expert_points': expert_data['projected_points'],
                        'system_confidence': system_data['confidence'],
                        'expert_confidence': expert_data['confidence']
                    })
            
            if not common_players:
                return {
                    'rank_correlation': 0,
                    'point_accuracy': 0,
                    'detailed_comparison': [],
                    'players_compared': 0
                }
            
            # Calculate rank correlation (Spearman)
            system_ranks = [p['system_rank'] for p in common_players]
            expert_ranks = [p['expert_rank'] for p in common_players]
            
            rank_correlation = self._spearman_correlation(system_ranks, expert_ranks)
            
            # Calculate point accuracy (Mean Absolute Error)
            point_errors = [abs(p['system_points'] - p['expert_points']) for p in common_players]
            point_accuracy = np.mean(point_errors)
            
            return {
                'rank_correlation': rank_correlation,
                'point_accuracy': point_accuracy,
                'detailed_comparison': common_players,
                'players_compared': len(common_players)
            }
            
        except Exception as e:
            self.logger.error(f"Error comparing predictions: {e}")
            return {
                'rank_correlation': 0,
                'point_accuracy': float('inf'),
                'detailed_comparison': [],
                'players_compared': 0
            }
    
    def _spearman_correlation(self, ranks1, ranks2):
        """Calculate Spearman rank correlation"""
        try:
            n = len(ranks1)
            if n < 2:
                return 0
                
            d_squared = sum((r1 - r2) ** 2 for r1, r2 in zip(ranks1, ranks2))
            correlation = 1 - (6 * d_squared) / (n * (n**2 - 1))
            return correlation
            
        except Exception as e:
            self.logger.error(f"Error calculating correlation: {e}")
            return 0
    
    def _display_validation_results(self, position, comparison):
        """Display validation results for a position"""
        try:
            print(f"   📊 {position} Validation Results:")
            print(f"      Players Compared: {comparison['players_compared']}")
            print(f"      Rank Correlation: {comparison['rank_correlation']:.3f}")
            print(f"      Point Accuracy (MAE): {comparison['point_accuracy']:.2f}")
            
            if comparison['detailed_comparison']:
                print(f"      Detailed Comparison:")
                for player in comparison['detailed_comparison'][:3]:  # Top 3
                    sys_rank = player['system_rank']
                    exp_rank = player['expert_rank']
                    sys_pts = player['system_points']
                    exp_pts = player['expert_points']
                    
                    rank_diff = abs(sys_rank - exp_rank)
                    point_diff = abs(sys_pts - exp_pts)
                    
                    print(f"         {player['name']}: Rank {sys_rank} vs {exp_rank} (±{rank_diff}), "
                          f"Points {sys_pts:.1f} vs {exp_pts:.1f} (±{point_diff:.1f})")
            
        except Exception as e:
            self.logger.error(f"Error displaying results: {e}")
    
    def _generate_overall_assessment(self, validation_results):
        """Generate overall assessment and recommendations"""
        try:
            # Calculate averages
            correlations = list(validation_results['rank_correlation'].values())
            accuracies = list(validation_results['point_accuracy'].values())
            
            avg_correlation = np.mean(correlations) if correlations else 0
            avg_accuracy = np.mean(accuracies) if accuracies else float('inf')
            
            # Assessment criteria
            assessment = {
                'avg_rank_correlation': avg_correlation,
                'avg_point_accuracy': avg_accuracy,
                'grade': 'F',
                'strengths': [],
                'weaknesses': [],
                'recommendations': []
            }
            
            # Grading system
            if avg_correlation >= 0.8 and avg_accuracy <= 3.0:
                assessment['grade'] = 'A'
            elif avg_correlation >= 0.6 and avg_accuracy <= 4.0:
                assessment['grade'] = 'B'
            elif avg_correlation >= 0.4 and avg_accuracy <= 5.0:
                assessment['grade'] = 'C'
            elif avg_correlation >= 0.2 and avg_accuracy <= 6.0:
                assessment['grade'] = 'D'
            
            # Identify strengths and weaknesses
            for position, correlation in validation_results['rank_correlation'].items():
                accuracy = validation_results['point_accuracy'][position]
                
                if correlation >= 0.7:
                    assessment['strengths'].append(f"{position} ranking correlation excellent ({correlation:.2f})")
                elif correlation <= 0.3:
                    assessment['weaknesses'].append(f"{position} ranking correlation needs improvement ({correlation:.2f})")
                    
                if accuracy <= 3.0:
                    assessment['strengths'].append(f"{position} point accuracy excellent ({accuracy:.1f} MAE)")
                elif accuracy >= 5.0:
                    assessment['weaknesses'].append(f"{position} point accuracy needs improvement ({accuracy:.1f} MAE)")
            
            # Generate recommendations
            if avg_correlation < 0.5:
                assessment['recommendations'].append("Consider adjusting ranking algorithms")
            if avg_accuracy > 4.0:
                assessment['recommendations'].append("Fine-tune point projection models")
            if validation_results['total_compared'] < 15:
                assessment['recommendations'].append("Expand player coverage for better validation")
                
            return assessment
            
        except Exception as e:
            self.logger.error(f"Error generating assessment: {e}")
            return {}
    
    def run_weekly_validation_report(self, season=2024, week=9):
        """Generate comprehensive weekly validation report"""
        print("📈 EXPERT CONSENSUS VALIDATION REPORT")
        print("=" * 60)
        print(f"Season: {season}, Week: {week}")
        print(f"Validation Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Run validation
        results = self.validate_weekly_predictions(season, week)
        
        if not results:
            print("❌ Validation failed")
            return
            
        # Display overall assessment
        assessment = results.get('overall_assessment', {})
        
        print(f"\\n🎯 OVERALL ASSESSMENT")
        print("-" * 30)
        print(f"   Grade: {assessment.get('grade', 'N/A')}")
        print(f"   Average Rank Correlation: {assessment.get('avg_rank_correlation', 0):.3f}")
        print(f"   Average Point Accuracy: {assessment.get('avg_point_accuracy', 0):.2f} MAE")
        print(f"   Total Players Compared: {results['total_compared']}")
        
        # Strengths
        strengths = assessment.get('strengths', [])
        if strengths:
            print(f"\\n✅ STRENGTHS:")
            for strength in strengths:
                print(f"   • {strength}")
        
        # Weaknesses
        weaknesses = assessment.get('weaknesses', [])
        if weaknesses:
            print(f"\\n⚠️  AREAS FOR IMPROVEMENT:")
            for weakness in weaknesses:
                print(f"   • {weakness}")
        
        # Recommendations
        recommendations = assessment.get('recommendations', [])
        if recommendations:
            print(f"\\n💡 RECOMMENDATIONS:")
            for rec in recommendations:
                print(f"   • {rec}")
        
        print(f"\\n🏆 SYSTEM STATUS:")
        if assessment.get('grade', 'F') in ['A', 'B']:
            print("   ✅ System performing at professional level")
        elif assessment.get('grade', 'F') == 'C':
            print("   ⚠️  System performing adequately, room for improvement")
        else:
            print("   🔧 System needs significant improvement")
            
        return results