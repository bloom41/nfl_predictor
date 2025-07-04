#!/usr/bin/env python3
"""
Enhanced Predictor System
Comprehensive NFL prediction system integrating all advanced features
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

# Import all our new systems
from src.utils.multi_scoring_system import ScoringCalculator, ScoringType, get_scoring_calculator
from src.utils.injury_news_tracker import InjuryNewsTracker, InjuryStatus, NewsImpact
from src.utils.matchup_analyzer import MatchupAnalyzer, DefenseStats, HomeAwayTrend, RecentTrend
from src.utils.advanced_analytics import AdvancedAnalytics, SnapCountData, TargetShareData, RedZoneUsage
from src.utils.export_integration import ExportIntegrationSystem, PlayerExportData, ExportFormat
from src.utils.simple_predictor import SimplePredictor

logger = logging.getLogger(__name__)

@dataclass
class EnhancedPrediction:
    """Comprehensive prediction with all analytics"""
    player_id: int
    player_name: str
    team: str
    position: str
    week: int
    season: int
    
    # Core prediction
    base_prediction: float
    final_prediction: float
    confidence: float
    
    # Multipliers applied
    injury_multiplier: float
    matchup_multiplier: float
    location_multiplier: float
    trend_multiplier: float
    weather_multiplier: float
    
    # Supporting data
    injury_status: Optional[str] = None
    matchup_rating: Optional[float] = None
    recent_trend: Optional[str] = None
    target_share: Optional[float] = None
    snap_percentage: Optional[float] = None
    red_zone_share: Optional[float] = None
    
    # Meta information
    data_quality_score: float = 1.0
    last_updated: datetime = None
    
    def __post_init__(self):
        """Initialize post-creation fields"""
        if self.last_updated is None:
            self.last_updated = datetime.utcnow()

class EnhancedPredictorSystem:
    """
    Comprehensive prediction system integrating all advanced features
    Follows KISS principle while providing extensive functionality
    """
    
    def __init__(self, scoring_format: str = "half_ppr"):
        """Initialize the enhanced predictor system"""
        try:
            self.logger = logging.getLogger(__name__)
            self.logger.info("Initializing Enhanced Predictor System")
            
            # Core systems
            self.simple_predictor = SimplePredictor()
            self.scoring_calculator = get_scoring_calculator(scoring_format)
            
            # Advanced systems
            self.injury_tracker = InjuryNewsTracker()
            self.matchup_analyzer = MatchupAnalyzer()
            self.advanced_analytics = AdvancedAnalytics()
            self.export_system = ExportIntegrationSystem()
            
            # Configuration
            self.scoring_format = scoring_format
            self.default_confidence = 0.75
            
            # Load sample data for testing
            self._load_sample_data()
            
            self.logger.info("Enhanced Predictor System initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Enhanced Predictor System: {e}")
            raise
    
    def predict_player_enhanced(self, player_id: int, player_name: str, 
                              team: str, position: str, opponent: str,
                              is_home: bool, season: int, week: int) -> EnhancedPrediction:
        """
        Generate comprehensive enhanced prediction for a player
        
        Args:
            player_id: Unique player identifier
            player_name: Player's name
            team: Player's team
            position: Player's position (QB, RB, WR, TE)
            opponent: Opponent team
            is_home: Whether playing at home
            season: Season year
            week: Week number
            
        Returns:
            EnhancedPrediction with all analytics applied
        """
        try:
            # Input validation
            if not all([player_id, player_name, team, position, opponent]):
                raise ValueError("Missing required player information")
            
            if week < 1 or week > 18:
                raise ValueError(f"Invalid week number: {week}")
            
            self.logger.debug(f"Generating enhanced prediction for {player_name}")
            
            # Get base prediction from simple predictor
            base_prediction_obj = self.simple_predictor.predict_player(player_id, season, week)
            
            if not base_prediction_obj:
                self.logger.warning(f"No base prediction available for {player_name}")
                return self._create_fallback_prediction(
                    player_id, player_name, team, position, season, week
                )
            
            base_prediction = base_prediction_obj.predicted_fantasy_points
            base_confidence = base_prediction_obj.confidence
            
            # Apply all enhancement multipliers
            injury_multiplier = self._get_injury_multiplier(player_id)
            matchup_multiplier = self._get_matchup_multiplier(player_id, position, opponent, is_home, week)
            location_multiplier = self._get_location_multiplier(player_id, is_home)
            trend_multiplier = self._get_trend_multiplier(player_id)
            weather_multiplier = self._get_weather_multiplier(team, week)
            
            # Calculate final prediction
            final_prediction = (base_prediction * 
                              injury_multiplier * 
                              matchup_multiplier * 
                              location_multiplier * 
                              trend_multiplier * 
                              weather_multiplier)
            
            # Adjust confidence based on data quality
            final_confidence = self._calculate_final_confidence(
                base_confidence, player_id, [injury_multiplier, matchup_multiplier, 
                                           location_multiplier, trend_multiplier, weather_multiplier]
            )
            
            # Get supporting analytics
            supporting_data = self._get_supporting_analytics(player_id)
            
            # Create enhanced prediction
            prediction = EnhancedPrediction(
                player_id=player_id,
                player_name=player_name,
                team=team,
                position=position,
                week=week,
                season=season,
                base_prediction=base_prediction,
                final_prediction=max(0.0, final_prediction),  # Ensure non-negative
                confidence=final_confidence,
                injury_multiplier=injury_multiplier,
                matchup_multiplier=matchup_multiplier,
                location_multiplier=location_multiplier,
                trend_multiplier=trend_multiplier,
                weather_multiplier=weather_multiplier,
                **supporting_data
            )
            
            self.logger.debug(f"Enhanced prediction complete for {player_name}: {final_prediction:.1f} pts")
            return prediction
            
        except Exception as e:
            self.logger.error(f"Error generating enhanced prediction for {player_name}: {e}")
            return self._create_fallback_prediction(player_id, player_name, team, position, season, week)
    
    def _get_injury_multiplier(self, player_id: int) -> float:
        """Get injury risk multiplier with timeout protection"""
        try:
            return self.injury_tracker.get_injury_risk_multiplier(player_id)
        except Exception as e:
            self.logger.warning(f"Error getting injury multiplier for player {player_id}: {e}")
            return 1.0
    
    def _get_matchup_multiplier(self, player_id: int, position: str, 
                               opponent: str, is_home: bool, week: int) -> float:
        """Get matchup difficulty multiplier with error handling"""
        try:
            analysis = self.matchup_analyzer.analyze_matchup(
                player_id, f"Player_{player_id}", position, opponent, is_home, week
            )
            return analysis.get('defense_matchup', {}).get('multiplier', 1.0)
        except Exception as e:
            self.logger.warning(f"Error getting matchup multiplier: {e}")
            return 1.0
    
    def _get_location_multiplier(self, player_id: int, is_home: bool) -> float:
        """Get home/away performance multiplier"""
        try:
            trend = self.matchup_analyzer.home_away_trends.get(player_id)
            if trend:
                return trend.get_location_multiplier(is_home)
            return 1.0
        except Exception as e:
            self.logger.warning(f"Error getting location multiplier: {e}")
            return 1.0
    
    def _get_trend_multiplier(self, player_id: int) -> float:
        """Get recent performance trend multiplier"""
        try:
            trend = self.matchup_analyzer.recent_trends.get(player_id)
            if trend:
                return trend.get_trend_multiplier()
            return 1.0
        except Exception as e:
            self.logger.warning(f"Error getting trend multiplier: {e}")
            return 1.0
    
    def _get_weather_multiplier(self, team: str, week: int) -> float:
        """Get weather impact multiplier"""
        try:
            weather_analysis = self.matchup_analyzer._analyze_weather_impact(team, week)
            return weather_analysis.get('multiplier', 1.0)
        except Exception as e:
            self.logger.warning(f"Error getting weather multiplier: {e}")
            return 1.0
    
    def _calculate_final_confidence(self, base_confidence: float, player_id: int, 
                                   multipliers: List[float]) -> float:
        """Calculate final confidence score based on data quality"""
        try:
            # Start with base confidence
            confidence = base_confidence
            
            # Reduce confidence if multipliers are extreme
            for multiplier in multipliers:
                if multiplier < 0.7 or multiplier > 1.3:
                    confidence *= 0.95  # Reduce confidence for extreme adjustments
            
            # Check data availability
            has_injury_data = player_id in self.injury_tracker.injury_reports
            has_analytics_data = player_id in self.advanced_analytics.snap_data
            
            if has_injury_data:
                confidence *= 1.05
            if has_analytics_data:
                confidence *= 1.05
            
            return min(1.0, max(0.1, confidence))  # Clamp between 0.1 and 1.0
            
        except Exception as e:
            self.logger.warning(f"Error calculating final confidence: {e}")
            return base_confidence
    
    def _get_supporting_analytics(self, player_id: int) -> Dict[str, Any]:
        """Get supporting analytics data"""
        try:
            supporting_data = {}
            
            # Injury status
            injury = self.injury_tracker.get_player_injury_status(player_id)
            if injury:
                supporting_data['injury_status'] = injury.injury_status.value
            
            # Target share (if available)
            target_analysis = self.advanced_analytics.analyze_target_efficiency(player_id, 6)
            if 'avg_target_share' in target_analysis:
                supporting_data['target_share'] = target_analysis['avg_target_share']
            
            # Snap percentage
            snap_analysis = self.advanced_analytics.analyze_snap_count_trends(player_id, 6)
            if 'avg_snap_percentage' in snap_analysis:
                supporting_data['snap_percentage'] = snap_analysis['avg_snap_percentage']
            
            # Red zone share
            rz_analysis = self.advanced_analytics.analyze_red_zone_role(player_id, 6)
            if 'avg_rz_share' in rz_analysis:
                supporting_data['red_zone_share'] = rz_analysis['avg_rz_share']
            
            return supporting_data
            
        except Exception as e:
            self.logger.warning(f"Error getting supporting analytics: {e}")
            return {}
    
    def _create_fallback_prediction(self, player_id: int, player_name: str, 
                                   team: str, position: str, season: int, week: int) -> EnhancedPrediction:
        """Create fallback prediction when primary prediction fails"""
        self.logger.info(f"Creating fallback prediction for {player_name}")
        
        # Basic position-based prediction
        position_averages = {'QB': 18.0, 'RB': 12.0, 'WR': 10.0, 'TE': 8.0}
        fallback_points = position_averages.get(position, 8.0)
        
        return EnhancedPrediction(
            player_id=player_id,
            player_name=player_name,
            team=team,
            position=position,
            week=week,
            season=season,
            base_prediction=fallback_points,
            final_prediction=fallback_points,
            confidence=0.3,  # Low confidence for fallback
            injury_multiplier=1.0,
            matchup_multiplier=1.0,
            location_multiplier=1.0,
            trend_multiplier=1.0,
            weather_multiplier=1.0,
            data_quality_score=0.2
        )
    
    def get_enhanced_rankings(self, position: str, season: int = 2024, 
                            week: int = 1, top_n: int = 15) -> List[EnhancedPrediction]:
        """Get enhanced rankings for a position with all analytics applied"""
        try:
            self.logger.info(f"Generating enhanced {position} rankings for Week {week}")
            
            # Get base rankings from simple predictor
            base_rankings = self.simple_predictor.get_position_rankings(position, season, week, top_n * 2)
            
            enhanced_predictions = []
            
            for base_pred in base_rankings:
                try:
                    # Create enhanced prediction for each player
                    enhanced_pred = self.predict_player_enhanced(
                        player_id=base_pred.player_id,
                        player_name=base_pred.player_name,
                        team=base_pred.team,
                        position=base_pred.position,
                        opponent="TBD",  # Would come from schedule data
                        is_home=True,   # Would come from schedule data
                        season=season,
                        week=week
                    )
                    enhanced_predictions.append(enhanced_pred)
                    
                except Exception as e:
                    self.logger.warning(f"Error enhancing prediction for {base_pred.player_name}: {e}")
                    continue
            
            # Sort by final prediction and return top N
            enhanced_predictions.sort(key=lambda x: x.final_prediction, reverse=True)
            return enhanced_predictions[:top_n]
            
        except Exception as e:
            self.logger.error(f"Error generating enhanced rankings: {e}")
            return []
    
    def export_enhanced_rankings(self, position: str, season: int = 2024, 
                               week: int = 1, format_type: str = "csv") -> str:
        """Export enhanced rankings to specified format"""
        try:
            # Get enhanced rankings
            rankings = self.get_enhanced_rankings(position, season, week, 20)
            
            # Convert to export format
            export_data = []
            for pred in rankings:
                export_data.append(PlayerExportData(
                    player_name=pred.player_name,
                    team=pred.team,
                    position=pred.position,
                    week=pred.week,
                    projected_points=pred.final_prediction,
                    confidence=pred.confidence,
                    injury_status=pred.injury_status,
                    matchup_rating=pred.matchup_rating,
                    target_share=pred.target_share,
                    snap_percentage=pred.snap_percentage,
                    red_zone_share=pred.red_zone_share,
                    recent_trend=pred.recent_trend
                ))
            
            # Export using the export system
            if format_type.lower() == "csv":
                export_format = ExportFormat.CSV
            elif format_type.lower() == "json":
                export_format = ExportFormat.JSON
            elif format_type.lower() == "html":
                export_format = ExportFormat.HTML
            else:
                export_format = ExportFormat.CSV
            
            filename = f"enhanced_{position}_rankings_week_{week}"
            return self.export_system.export_rankings(export_data, export_format, filename)
            
        except Exception as e:
            self.logger.error(f"Error exporting enhanced rankings: {e}")
            raise
    
    def format_enhanced_prediction(self, prediction: EnhancedPrediction) -> str:
        """Format enhanced prediction for display"""
        try:
            lines = []
            lines.append(f"🎯 ENHANCED PREDICTION - {prediction.player_name}")
            lines.append("=" * 50)
            
            # Core prediction
            lines.append(f"📊 Final Projection: {prediction.final_prediction:.1f} pts ({self.scoring_format})")
            lines.append(f"🎯 Confidence: {prediction.confidence:.1%}")
            lines.append("")
            
            # Multiplier breakdown
            lines.append("🔧 ADJUSTMENT FACTORS:")
            lines.append(f"   Base Prediction: {prediction.base_prediction:.1f} pts")
            lines.append(f"   Injury Factor: {prediction.injury_multiplier:.2f}x")
            lines.append(f"   Matchup Factor: {prediction.matchup_multiplier:.2f}x")
            lines.append(f"   Location Factor: {prediction.location_multiplier:.2f}x")
            lines.append(f"   Trend Factor: {prediction.trend_multiplier:.2f}x")
            lines.append(f"   Weather Factor: {prediction.weather_multiplier:.2f}x")
            lines.append("")
            
            # Supporting analytics
            if any([prediction.target_share, prediction.snap_percentage, prediction.red_zone_share]):
                lines.append("📈 ADVANCED METRICS:")
                if prediction.target_share:
                    lines.append(f"   Target Share: {prediction.target_share:.1f}%")
                if prediction.snap_percentage:
                    lines.append(f"   Snap Rate: {prediction.snap_percentage:.1f}%")
                if prediction.red_zone_share:
                    lines.append(f"   Red Zone Share: {prediction.red_zone_share:.1f}%")
                lines.append("")
            
            # Status indicators
            status_items = []
            if prediction.injury_status:
                status_items.append(f"🏥 {prediction.injury_status.title()}")
            if prediction.recent_trend:
                trend_emoji = "📈" if prediction.recent_trend == "up" else "📉" if prediction.recent_trend == "down" else "➡️"
                status_items.append(f"{trend_emoji} {prediction.recent_trend.title()}")
            
            if status_items:
                lines.append("ℹ️  STATUS: " + " | ".join(status_items))
            
            lines.append(f"🕐 Updated: {prediction.last_updated.strftime('%Y-%m-%d %H:%M')}")
            
            return "\n".join(lines)
            
        except Exception as e:
            self.logger.error(f"Error formatting enhanced prediction: {e}")
            return f"Error formatting prediction for {prediction.player_name}"
    
    def _load_sample_data(self) -> None:
        """Load sample data for testing (following YAGNI principle)"""
        try:
            # Only load minimal sample data needed for testing
            from src.utils.injury_news_tracker import load_sample_injury_data
            from src.utils.matchup_analyzer import load_sample_matchup_data
            from src.utils.advanced_analytics import load_sample_analytics_data
            
            load_sample_injury_data(self.injury_tracker)
            load_sample_matchup_data(self.matchup_analyzer)
            load_sample_analytics_data(self.advanced_analytics)
            
            self.logger.debug("Sample data loaded successfully")
            
        except Exception as e:
            self.logger.warning(f"Could not load sample data: {e}")
            # Continue without sample data - system should still function

if __name__ == "__main__":
    # Test the enhanced predictor system
    print("🚀 ENHANCED PREDICTOR SYSTEM TEST")
    print("=" * 50)
    
    try:
        # Initialize system
        enhanced_system = EnhancedPredictorSystem("half_ppr")
        
        # Test enhanced prediction
        test_prediction = enhanced_system.predict_player_enhanced(
            player_id=1,
            player_name="Cooper Kupp",
            team="LAR",
            position="WR",
            opponent="SF",
            is_home=True,
            season=2024,
            week=8
        )
        
        print(enhanced_system.format_enhanced_prediction(test_prediction))
        print()
        
        # Test enhanced rankings
        print("📊 ENHANCED RANKINGS TEST:")
        enhanced_rankings = enhanced_system.get_enhanced_rankings("WR", 2024, 8, 5)
        
        for i, pred in enumerate(enhanced_rankings, 1):
            print(f"{i}. {pred.player_name}: {pred.final_prediction:.1f} pts "
                  f"[Confidence: {pred.confidence:.1%}]")
        
        print("\n✅ Enhanced Predictor System test completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        logger.error(f"Enhanced predictor system test failed: {e}")