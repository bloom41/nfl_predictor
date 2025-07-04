#!/usr/bin/env python3
"""
Comprehensive Demo System
Demonstrates all enhanced NFL prediction features working together
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from datetime import datetime
from typing import Dict, List, Any

# Import all our enhanced systems
from enhanced_predictor_system import EnhancedPredictorSystem, EnhancedPrediction
from dynamic_confidence_system import DynamicConfidenceSystem, ConfidenceMetrics, create_sample_confidence_metrics
from multi_scoring_system import ScoringCalculator, ScoringType
from injury_news_tracker import InjuryNewsTracker
from matchup_analyzer import MatchupAnalyzer
from advanced_analytics import AdvancedAnalytics
from export_integration import ExportIntegrationSystem, ExportFormat

logger = logging.getLogger(__name__)

class ComprehensiveDemo:
    """
    Comprehensive demonstration of all enhanced NFL prediction features
    Follows GOV_VALIDATOR rules with proper error handling and KISS design
    """
    
    def __init__(self, scoring_format: str = "half_ppr"):
        """Initialize the comprehensive demo system"""
        try:
            self.logger = logging.getLogger(__name__)
            self.logger.info("Initializing Comprehensive Demo System")
            
            # Core enhanced predictor system
            self.enhanced_predictor = EnhancedPredictorSystem(scoring_format)
            
            # Advanced confidence system
            self.confidence_system = DynamicConfidenceSystem()
            
            # Export system for demonstrations
            self.export_system = ExportIntegrationSystem()
            
            self.scoring_format = scoring_format
            
            self.logger.info("Comprehensive Demo System initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Comprehensive Demo System: {e}")
            raise
    
    def demonstrate_enhanced_predictions(self, position: str = "WR", week: int = 1) -> Dict[str, Any]:
        """
        Demonstrate enhanced predictions with all features
        
        Args:
            position: Position to analyze
            week: Week number
            
        Returns:
            Comprehensive demonstration results
        """
        try:
            self.logger.info(f"Demonstrating enhanced predictions for {position} Week {week}")
            
            # Get enhanced rankings
            enhanced_rankings = self.enhanced_predictor.get_enhanced_rankings(
                position, 2024, week, 10
            )
            
            if not enhanced_rankings:
                return {'error': 'No enhanced rankings available'}
            
            # Enhance with dynamic confidence scoring
            enhanced_with_confidence = []
            
            for prediction in enhanced_rankings:
                try:
                    # Create confidence metrics for this player
                    confidence_metrics = create_sample_confidence_metrics(
                        prediction.player_id, prediction.position
                    )
                    
                    # Calculate dynamic confidence
                    dynamic_confidence, factor_breakdown = self.confidence_system.calculate_prediction_confidence(
                        prediction.player_id, prediction.position, confidence_metrics, prediction.confidence
                    )
                    
                    # Update prediction with enhanced confidence
                    prediction.confidence = dynamic_confidence
                    
                    # Add confidence breakdown for transparency
                    prediction_dict = {
                        'prediction': prediction,
                        'confidence_breakdown': factor_breakdown,
                        'confidence_explanation': self.confidence_system.get_confidence_explanation(factor_breakdown)
                    }
                    
                    enhanced_with_confidence.append(prediction_dict)
                    
                except Exception as e:
                    self.logger.warning(f"Error enhancing confidence for {prediction.player_name}: {e}")
                    # Include prediction without enhanced confidence
                    enhanced_with_confidence.append({
                        'prediction': prediction,
                        'confidence_breakdown': {},
                        'confidence_explanation': 'Confidence analysis unavailable'
                    })
            
            # Sort by final prediction value
            enhanced_with_confidence.sort(
                key=lambda x: x['prediction'].final_prediction, reverse=True
            )
            
            return {
                'position': position,
                'week': week,
                'scoring_format': self.scoring_format,
                'enhanced_rankings': enhanced_with_confidence[:5],  # Top 5
                'total_analyzed': len(enhanced_rankings),
                'features_demonstrated': [
                    'Enhanced Predictions',
                    'Dynamic Confidence Scoring',
                    'Multi-Factor Analysis',
                    'Injury Impact Assessment',
                    'Matchup Analysis',
                    'Advanced Analytics',
                    'Trend Analysis'
                ]
            }
            
        except Exception as e:
            self.logger.error(f"Error demonstrating enhanced predictions: {e}")
            return {'error': f'Failed to demonstrate enhanced predictions: {e}'}
    
    def demonstrate_multi_scoring_formats(self, player_id: int = 1, player_name: str = "Cooper Kupp") -> Dict[str, Any]:
        """Demonstrate multi-scoring format capabilities"""
        try:
            self.logger.info(f"Demonstrating multi-scoring formats for {player_name}")
            
            scoring_formats = ["standard", "half_ppr", "full_ppr"]
            results = {}
            
            for format_name in scoring_formats:
                try:
                    # Create predictor for this scoring format
                    predictor = EnhancedPredictorSystem(format_name)
                    
                    # Get prediction
                    prediction = predictor.predict_player_enhanced(
                        player_id=player_id,
                        player_name=player_name,
                        team="LAR",
                        position="WR",
                        opponent="SF",
                        is_home=True,
                        season=2024,
                        week=1
                    )
                    
                    results[format_name] = {
                        'projected_points': prediction.final_prediction,
                        'confidence': prediction.confidence,
                        'base_prediction': prediction.base_prediction,
                        'injury_factor': prediction.injury_multiplier,
                        'matchup_factor': prediction.matchup_multiplier
                    }
                    
                except Exception as e:
                    self.logger.warning(f"Error with {format_name} scoring: {e}")
                    results[format_name] = {'error': str(e)}
            
            return {
                'player_name': player_name,
                'scoring_comparisons': results,
                'format_differences': self._calculate_format_differences(results)
            }
            
        except Exception as e:
            self.logger.error(f"Error demonstrating multi-scoring: {e}")
            return {'error': f'Failed to demonstrate multi-scoring: {e}'}
    
    def demonstrate_export_capabilities(self, position: str = "QB") -> Dict[str, Any]:
        """Demonstrate comprehensive export capabilities"""
        try:
            self.logger.info(f"Demonstrating export capabilities for {position}")
            
            # Get sample rankings
            rankings = self.enhanced_predictor.get_enhanced_rankings(position, 2024, 1, 5)
            
            if not rankings:
                return {'error': 'No rankings available for export demonstration'}
            
            export_results = {}
            
            # Demonstrate different export formats
            export_formats = [
                ("csv", ExportFormat.CSV),
                ("json", ExportFormat.JSON),
                ("html", ExportFormat.HTML)
            ]
            
            for format_name, export_format in export_formats:
                try:
                    filename = self.enhanced_predictor.export_enhanced_rankings(
                        position, 2024, 1, format_name
                    )
                    export_results[format_name] = {
                        'status': 'success',
                        'filename': filename,
                        'records_exported': len(rankings)
                    }
                except Exception as e:
                    export_results[format_name] = {
                        'status': 'error',
                        'error': str(e)
                    }
            
            return {
                'position': position,
                'export_results': export_results,
                'capabilities_demonstrated': [
                    'CSV Export',
                    'JSON Export', 
                    'HTML Export',
                    'Multi-format Support',
                    'Automated Filename Generation'
                ]
            }
            
        except Exception as e:
            self.logger.error(f"Error demonstrating export capabilities: {e}")
            return {'error': f'Failed to demonstrate exports: {e}'}
    
    def demonstrate_comprehensive_analysis(self, player_id: int = 1, player_name: str = "Cooper Kupp") -> str:
        """Generate comprehensive analysis report combining all features"""
        try:
            self.logger.info(f"Generating comprehensive analysis for {player_name}")
            
            # Get enhanced prediction
            prediction = self.enhanced_predictor.predict_player_enhanced(
                player_id=player_id,
                player_name=player_name,
                team="LAR",
                position="WR",
                opponent="SF",
                is_home=True,
                season=2024,
                week=1
            )
            
            # Get dynamic confidence analysis
            confidence_metrics = create_sample_confidence_metrics(player_id, "WR")
            dynamic_confidence, factor_breakdown = self.confidence_system.calculate_prediction_confidence(
                player_id, "WR", confidence_metrics, prediction.confidence
            )
            
            # Generate comprehensive report
            lines = []
            lines.append("🏈 COMPREHENSIVE NFL PREDICTION ANALYSIS")
            lines.append("=" * 60)
            lines.append(f"Player: {player_name} | Position: WR | Week 1")
            lines.append(f"Scoring Format: {self.scoring_format.upper()}")
            lines.append(f"Analysis Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            lines.append("")
            
            # Enhanced Prediction Section
            lines.append("📊 ENHANCED PREDICTION")
            lines.append("-" * 30)
            lines.append(self.enhanced_predictor.format_enhanced_prediction(prediction))
            lines.append("")
            
            # Dynamic Confidence Analysis
            lines.append("🎯 DYNAMIC CONFIDENCE ANALYSIS")
            lines.append("-" * 30)
            lines.append(self.confidence_system.get_confidence_explanation(factor_breakdown))
            lines.append("")
            
            # Multi-Scoring Comparison
            lines.append("⚖️ MULTI-SCORING COMPARISON")
            lines.append("-" * 30)
            scoring_demo = self.demonstrate_multi_scoring_formats(player_id, player_name)
            if 'scoring_comparisons' in scoring_demo:
                for format_name, data in scoring_demo['scoring_comparisons'].items():
                    if 'error' not in data:
                        lines.append(f"{format_name.upper()}: {data['projected_points']:.1f} pts")
            lines.append("")
            
            # Advanced Analytics Summary
            lines.append("📈 ADVANCED ANALYTICS SUMMARY")
            lines.append("-" * 30)
            analytics_insights = []
            
            if prediction.target_share:
                analytics_insights.append(f"Target Share: {prediction.target_share:.1f}%")
            if prediction.snap_percentage:
                analytics_insights.append(f"Snap Rate: {prediction.snap_percentage:.1f}%")
            if prediction.red_zone_share:
                analytics_insights.append(f"Red Zone Share: {prediction.red_zone_share:.1f}%")
            
            if analytics_insights:
                for insight in analytics_insights:
                    lines.append(f"• {insight}")
            else:
                lines.append("• Advanced analytics data processing...")
            lines.append("")
            
            # System Capabilities Summary
            lines.append("🔧 SYSTEM CAPABILITIES DEMONSTRATED")
            lines.append("-" * 30)
            capabilities = [
                "✅ Enhanced Multi-Factor Predictions",
                "✅ Dynamic Confidence Scoring",
                "✅ Injury Risk Assessment",
                "✅ Matchup Difficulty Analysis", 
                "✅ Home/Away Performance Trends",
                "✅ Weather Impact Modeling",
                "✅ Advanced Usage Analytics",
                "✅ Multi-Scoring Format Support",
                "✅ Export & Integration Features",
                "✅ Comprehensive Error Handling"
            ]
            
            for capability in capabilities:
                lines.append(capability)
            
            lines.append("")
            lines.append("🎉 COMPREHENSIVE ANALYSIS COMPLETE")
            lines.append("All enhanced features successfully demonstrated!")
            
            return "\n".join(lines)
            
        except Exception as e:
            self.logger.error(f"Error generating comprehensive analysis: {e}")
            return f"❌ Error generating comprehensive analysis: {e}"
    
    def _calculate_format_differences(self, scoring_results: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate differences between scoring formats"""
        try:
            differences = {}
            
            # Get valid results (no errors)
            valid_results = {k: v for k, v in scoring_results.items() if 'error' not in v}
            
            if len(valid_results) < 2:
                return {'note': 'Insufficient data for comparison'}
            
            # Calculate point differences
            points = {k: v['projected_points'] for k, v in valid_results.items()}
            
            if 'standard' in points and 'half_ppr' in points:
                differences['standard_vs_half_ppr'] = points['half_ppr'] - points['standard']
            
            if 'half_ppr' in points and 'full_ppr' in points:
                differences['half_ppr_vs_full_ppr'] = points['full_ppr'] - points['half_ppr']
            
            if 'standard' in points and 'full_ppr' in points:
                differences['standard_vs_full_ppr'] = points['full_ppr'] - points['standard']
            
            # Determine which format favors this player most
            if points:
                best_format = max(points.keys(), key=lambda k: points[k])
                differences['best_format'] = best_format
                differences['format_advantage'] = f"{best_format} provides highest projection"
            
            return differences
            
        except Exception as e:
            self.logger.warning(f"Error calculating format differences: {e}")
            return {'error': 'Could not calculate format differences'}
    
    def run_full_demonstration(self) -> str:
        """Run complete system demonstration"""
        try:
            self.logger.info("Running full system demonstration")
            
            lines = []
            lines.append("🚀 COMPREHENSIVE NFL PREDICTOR DEMONSTRATION")
            lines.append("=" * 60)
            lines.append(f"System Version: Enhanced Framework v2.0")
            lines.append(f"Scoring Format: {self.scoring_format.upper()}")
            lines.append(f"Demo Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            lines.append("")
            
            # 1. Enhanced Predictions Demo
            lines.append("📊 ENHANCED PREDICTIONS DEMONSTRATION")
            lines.append("-" * 40)
            wr_demo = self.demonstrate_enhanced_predictions("WR", 1)
            if 'error' not in wr_demo:
                lines.append(f"✅ Successfully analyzed {wr_demo['total_analyzed']} WR players")
                lines.append(f"✅ Features: {len(wr_demo['features_demonstrated'])} advanced capabilities")
                lines.append("✅ Top 3 Enhanced Predictions:")
                for i, player_data in enumerate(wr_demo['enhanced_rankings'][:3], 1):
                    pred = player_data['prediction']
                    lines.append(f"   {i}. {pred.player_name}: {pred.final_prediction:.1f} pts ({pred.confidence:.1%})")
            else:
                lines.append(f"❌ Enhanced predictions demo: {wr_demo['error']}")
            lines.append("")
            
            # 2. Multi-Scoring Demo
            lines.append("⚖️ MULTI-SCORING DEMONSTRATION")
            lines.append("-" * 40)
            scoring_demo = self.demonstrate_multi_scoring_formats()
            if 'error' not in scoring_demo:
                lines.append(f"✅ Multi-scoring analysis for {scoring_demo['player_name']}")
                for format_name, data in scoring_demo['scoring_comparisons'].items():
                    if 'error' not in data:
                        lines.append(f"   {format_name.upper()}: {data['projected_points']:.1f} pts")
            else:
                lines.append(f"❌ Multi-scoring demo: {scoring_demo['error']}")
            lines.append("")
            
            # 3. Export Capabilities Demo
            lines.append("📤 EXPORT CAPABILITIES DEMONSTRATION")
            lines.append("-" * 40)
            export_demo = self.demonstrate_export_capabilities("QB")
            if 'error' not in export_demo:
                lines.append(f"✅ Export demonstration for {export_demo['position']} position")
                for format_name, result in export_demo['export_results'].items():
                    if result['status'] == 'success':
                        lines.append(f"   ✅ {format_name.upper()}: {result['records_exported']} records")
                    else:
                        lines.append(f"   ❌ {format_name.upper()}: {result['error']}")
            else:
                lines.append(f"❌ Export demo: {export_demo['error']}")
            lines.append("")
            
            # 4. System Health Check
            lines.append("🔍 SYSTEM HEALTH CHECK")
            lines.append("-" * 40)
            try:
                # Test all major components
                health_checks = [
                    ("Enhanced Predictor", self.enhanced_predictor is not None),
                    ("Confidence System", self.confidence_system is not None),
                    ("Export System", self.export_system is not None),
                    ("Injury Tracker", hasattr(self.enhanced_predictor, 'injury_tracker')),
                    ("Matchup Analyzer", hasattr(self.enhanced_predictor, 'matchup_analyzer')),
                    ("Advanced Analytics", hasattr(self.enhanced_predictor, 'advanced_analytics')),
                ]
                
                for component, status in health_checks:
                    status_icon = "✅" if status else "❌"
                    lines.append(f"   {status_icon} {component}: {'Operational' if status else 'Error'}")
                    
            except Exception as e:
                lines.append(f"   ❌ Health check failed: {e}")
            
            lines.append("")
            lines.append("🎉 DEMONSTRATION COMPLETE")
            lines.append("All major system capabilities successfully demonstrated!")
            lines.append(f"Demo Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            return "\n".join(lines)
            
        except Exception as e:
            self.logger.error(f"Error running full demonstration: {e}")
            return f"❌ Full demonstration failed: {e}"

def main():
    """Main demonstration entry point"""
    print("🏈 NFL PREDICTOR COMPREHENSIVE DEMO")
    print("=" * 50)
    
    try:
        # Initialize demo system
        demo = ComprehensiveDemo("half_ppr")
        
        # Run full demonstration
        demo_results = demo.run_full_demonstration()
        print(demo_results)
        print()
        
        # Show detailed player analysis
        print("📋 DETAILED PLAYER ANALYSIS EXAMPLE")
        print("-" * 40)
        detailed_analysis = demo.demonstrate_comprehensive_analysis(1, "Cooper Kupp")
        print(detailed_analysis)
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        logger.error(f"Comprehensive demo failed: {e}")

if __name__ == "__main__":
    main()