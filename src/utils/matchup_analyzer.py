#!/usr/bin/env python3
"""
Matchup Analysis System
Analyzes opponent defenses, home/away splits, and recent trends
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class DefenseRank(Enum):
    ELITE = "elite"           # Top 5
    GOOD = "good"             # 6-12
    AVERAGE = "average"       # 13-20  
    POOR = "poor"             # 21-27
    TERRIBLE = "terrible"     # 28-32

@dataclass
class DefenseStats:
    """Team defense statistics"""
    team: str
    position: str  # QB, RB, WR, TE
    
    # Core stats
    points_allowed_per_game: float
    yards_allowed_per_game: float
    touchdowns_allowed: int
    turnovers_forced: int
    
    # Position-specific
    fantasy_points_allowed_rank: int  # 1-32 rank
    fantasy_points_allowed_avg: float
    
    # Advanced metrics
    red_zone_defense_pct: float
    third_down_defense_pct: float
    pressure_rate: Optional[float] = None  # For QB analysis
    
    def get_defense_rank(self) -> DefenseRank:
        """Get defense ranking tier"""
        rank = self.fantasy_points_allowed_rank
        if rank <= 5:
            return DefenseRank.ELITE
        elif rank <= 12:
            return DefenseRank.GOOD
        elif rank <= 20:
            return DefenseRank.AVERAGE
        elif rank <= 27:
            return DefenseRank.POOR
        else:
            return DefenseRank.TERRIBLE

@dataclass
class HomeAwayTrend:
    """Home/Away performance trends"""
    player_id: int
    
    # Home stats
    home_games: int
    home_fantasy_avg: float
    
    # Away stats
    away_games: int
    away_fantasy_avg: float
    
    # Optional stats with defaults
    home_targets_avg: Optional[float] = None
    home_touches_avg: Optional[float] = None
    away_targets_avg: Optional[float] = None
    away_touches_avg: Optional[float] = None
    
    def get_home_away_difference(self) -> float:
        """Get home vs away fantasy point difference"""
        return self.home_fantasy_avg - self.away_fantasy_avg
    
    def get_location_multiplier(self, is_home: bool) -> float:
        """Get multiplier based on home/away performance"""
        if self.home_games == 0 or self.away_games == 0:
            return 1.0  # Not enough data
        
        difference = self.get_home_away_difference()
        
        if is_home:
            if difference > 3.0:
                return 1.15  # Strong home performer
            elif difference > 1.0:
                return 1.05  # Slight home advantage
            else:
                return 1.0
        else:  # Away
            if difference > 3.0:
                return 0.85  # Struggles away
            elif difference > 1.0:
                return 0.95  # Slight away disadvantage
            else:
                return 1.0

@dataclass
class RecentTrend:
    """Recent performance trends"""
    player_id: int
    games_analyzed: int
    
    # Trend analysis
    last_3_games_avg: float
    season_avg: float
    trending_direction: str  # 'up', 'down', 'stable'
    consistency_score: float  # 0-1, higher = more consistent
    
    # Usage trends
    target_share_trend: Optional[float] = None
    snap_count_trend: Optional[float] = None
    red_zone_usage_trend: Optional[float] = None
    
    def get_trend_multiplier(self) -> float:
        """Get multiplier based on recent trends"""
        recent_vs_season = self.last_3_games_avg / max(self.season_avg, 1.0)
        
        if self.trending_direction == 'up' and recent_vs_season > 1.2:
            return 1.1  # Hot streak
        elif self.trending_direction == 'down' and recent_vs_season < 0.8:
            return 0.9  # Cold streak
        else:
            return 1.0  # Stable performance

class MatchupAnalyzer:
    """Analyze player matchups and trends"""
    
    def __init__(self):
        self.defense_stats: Dict[Tuple[str, str], DefenseStats] = {}
        self.home_away_trends: Dict[int, HomeAwayTrend] = {}
        self.recent_trends: Dict[int, RecentTrend] = {}
        self.weather_data: Dict[str, Dict] = {}
        self.logger = logging.getLogger(__name__)
    
    def add_defense_stats(self, team: str, position: str, stats: DefenseStats) -> None:
        """Add defense statistics for team vs position"""
        self.defense_stats[(team, position)] = stats
        self.logger.info(f"Added defense stats for {team} vs {position}")
    
    def add_home_away_trend(self, player_id: int, trend: HomeAwayTrend) -> None:
        """Add home/away trend data for player"""
        self.home_away_trends[player_id] = trend
    
    def add_recent_trend(self, player_id: int, trend: RecentTrend) -> None:
        """Add recent performance trend for player"""
        self.recent_trends[player_id] = trend
    
    def analyze_matchup(self, player_id: int, player_name: str, position: str,
                       opponent_team: str, is_home: bool, week: int) -> Dict[str, Any]:
        """Comprehensive matchup analysis"""
        
        # Defense analysis
        defense_analysis = self._analyze_defense_matchup(opponent_team, position)
        
        # Home/Away analysis
        location_analysis = self._analyze_location_impact(player_id, is_home)
        
        # Recent trends analysis
        trend_analysis = self._analyze_recent_trends(player_id)
        
        # Weather analysis (for outdoor games)
        weather_analysis = self._analyze_weather_impact(opponent_team, week)
        
        # Overall matchup rating
        overall_rating = self._calculate_overall_rating(
            defense_analysis, location_analysis, trend_analysis, weather_analysis
        )
        
        return {
            'player_name': player_name,
            'opponent': opponent_team,
            'is_home': is_home,
            'defense_matchup': defense_analysis,
            'location_impact': location_analysis,
            'recent_trends': trend_analysis,
            'weather_impact': weather_analysis,
            'overall_rating': overall_rating,
            'recommendation': self._get_matchup_recommendation(overall_rating)
        }
    
    def _analyze_defense_matchup(self, opponent_team: str, position: str) -> Dict[str, Any]:
        """Analyze defensive matchup"""
        defense_key = (opponent_team, position)
        defense = self.defense_stats.get(defense_key)
        
        if not defense:
            return {
                'rank': 'unknown',
                'points_allowed_avg': 0.0,
                'difficulty_rating': 'average',
                'multiplier': 1.0
            }
        
        rank = defense.get_defense_rank()
        
        # Calculate difficulty multiplier
        multipliers = {
            DefenseRank.TERRIBLE: 1.15,  # Great matchup
            DefenseRank.POOR: 1.08,
            DefenseRank.AVERAGE: 1.0,
            DefenseRank.GOOD: 0.92,
            DefenseRank.ELITE: 0.85      # Tough matchup
        }
        
        return {
            'rank': rank.value,
            'rank_number': defense.fantasy_points_allowed_rank,
            'points_allowed_avg': defense.fantasy_points_allowed_avg,
            'difficulty_rating': rank.value,
            'multiplier': multipliers[rank],
            'red_zone_defense': defense.red_zone_defense_pct,
            'pressure_rate': defense.pressure_rate
        }
    
    def _analyze_location_impact(self, player_id: int, is_home: bool) -> Dict[str, Any]:
        """Analyze home/away impact"""
        trend = self.home_away_trends.get(player_id)
        
        if not trend:
            return {
                'has_data': False,
                'multiplier': 1.0,
                'notes': 'Insufficient home/away data'
            }
        
        multiplier = trend.get_location_multiplier(is_home)
        difference = trend.get_home_away_difference()
        
        location_type = 'home' if is_home else 'away'
        performance = 'better' if (is_home and difference > 1) or (not is_home and difference < -1) else 'similar'
        
        return {
            'has_data': True,
            'location': location_type,
            'home_avg': trend.home_fantasy_avg,
            'away_avg': trend.away_fantasy_avg,
            'difference': difference,
            'performance_vs_location': performance,
            'multiplier': multiplier
        }
    
    def _analyze_recent_trends(self, player_id: int) -> Dict[str, Any]:
        """Analyze recent performance trends"""
        trend = self.recent_trends.get(player_id)
        
        if not trend:
            return {
                'has_data': False,
                'multiplier': 1.0,
                'trending': 'stable'
            }
        
        multiplier = trend.get_trend_multiplier()
        
        return {
            'has_data': True,
            'last_3_avg': trend.last_3_games_avg,
            'season_avg': trend.season_avg,
            'trending': trend.trending_direction,
            'consistency': trend.consistency_score,
            'multiplier': multiplier,
            'target_share_trend': trend.target_share_trend,
            'usage_notes': self._generate_usage_notes(trend)
        }
    
    def _analyze_weather_impact(self, team: str, week: int) -> Dict[str, Any]:
        """Analyze weather impact (basic implementation)"""
        # This would integrate with weather APIs
        # For now, return basic analysis
        
        weather_key = f"{team}_week_{week}"
        weather = self.weather_data.get(weather_key, {})
        
        # Outdoor stadiums are more affected by weather
        outdoor_teams = ['GB', 'CHI', 'CLE', 'PIT', 'BUF', 'NE', 'DEN', 'KC', 'TEN', 'JAX', 'WAS', 'CAR', 'TB', 'MIA']
        
        is_outdoor = any(team in outdoor_teams for team in [team])
        
        if not is_outdoor:
            return {
                'impact': 'none',
                'notes': 'Indoor stadium',
                'multiplier': 1.0
            }
        
        # Default weather impact
        temp = weather.get('temperature', 65)
        wind = weather.get('wind_speed', 5)
        precipitation = weather.get('precipitation', 0)
        
        multiplier = 1.0
        impact_notes = []
        
        if temp < 32:
            multiplier *= 0.95
            impact_notes.append('Cold weather')
        elif temp > 85:
            multiplier *= 0.98
            impact_notes.append('Hot weather')
        
        if wind > 15:
            multiplier *= 0.92
            impact_notes.append('High winds')
        
        if precipitation > 0.1:
            multiplier *= 0.94
            impact_notes.append('Precipitation')
        
        return {
            'impact': 'minimal' if multiplier > 0.98 else 'moderate' if multiplier > 0.9 else 'significant',
            'temperature': temp,
            'wind_speed': wind,
            'precipitation': precipitation,
            'multiplier': multiplier,
            'notes': ', '.join(impact_notes) if impact_notes else 'Good conditions'
        }
    
    def _calculate_overall_rating(self, defense: Dict, location: Dict, 
                                trend: Dict, weather: Dict) -> float:
        """Calculate overall matchup rating (0-10 scale)"""
        base_rating = 5.0  # Average matchup
        
        # Defense impact (most important)
        defense_multiplier = defense.get('multiplier', 1.0)
        defense_impact = (defense_multiplier - 1.0) * 5  # Scale to +/- 2.5 points
        
        # Location impact
        location_multiplier = location.get('multiplier', 1.0)
        location_impact = (location_multiplier - 1.0) * 3  # Scale to +/- 1.5 points
        
        # Trend impact
        trend_multiplier = trend.get('multiplier', 1.0)
        trend_impact = (trend_multiplier - 1.0) * 2  # Scale to +/- 1 point
        
        # Weather impact
        weather_multiplier = weather.get('multiplier', 1.0)
        weather_impact = (weather_multiplier - 1.0) * 1  # Scale to +/- 0.5 points
        
        final_rating = base_rating + defense_impact + location_impact + trend_impact + weather_impact
        
        # Clamp to 0-10 range
        return max(0.0, min(10.0, final_rating))
    
    def _get_matchup_recommendation(self, rating: float) -> str:
        """Get recommendation based on matchup rating"""
        if rating >= 8.0:
            return "Excellent matchup - Strong start"
        elif rating >= 6.5:
            return "Good matchup - Solid play"
        elif rating >= 4.5:
            return "Average matchup - Proceed with caution"
        elif rating >= 3.0:
            return "Difficult matchup - Consider alternatives"
        else:
            return "Avoid if possible - Very tough matchup"
    
    def _generate_usage_notes(self, trend: RecentTrend) -> str:
        """Generate usage trend notes"""
        notes = []
        
        if trend.target_share_trend and trend.target_share_trend > 0.05:
            notes.append("Increasing target share")
        elif trend.target_share_trend and trend.target_share_trend < -0.05:
            notes.append("Decreasing target share")
        
        if trend.snap_count_trend and trend.snap_count_trend > 0.1:
            notes.append("More snaps")
        elif trend.snap_count_trend and trend.snap_count_trend < -0.1:
            notes.append("Fewer snaps")
        
        if trend.red_zone_usage_trend and trend.red_zone_usage_trend > 0.1:
            notes.append("Increased red zone usage")
        
        return ", ".join(notes) if notes else "Stable usage patterns"
    
    def get_matchup_summary(self, analysis: Dict[str, Any]) -> str:
        """Get formatted matchup summary"""
        lines = []
        lines.append(f"🎯 MATCHUP ANALYSIS - {analysis['player_name']}")
        lines.append(f"vs {analysis['opponent']} ({'Home' if analysis['is_home'] else 'Away'})")
        lines.append("=" * 45)
        
        # Overall rating
        rating = analysis['overall_rating']
        rating_emoji = "🔥" if rating >= 8 else "✅" if rating >= 6.5 else "⚠️" if rating >= 4.5 else "❌"
        lines.append(f"{rating_emoji} Overall Rating: {rating:.1f}/10")
        lines.append(f"📋 Recommendation: {analysis['recommendation']}")
        lines.append("")
        
        # Defense matchup
        defense = analysis['defense_matchup']
        if defense['rank'] != 'unknown':
            rank_emoji = "🟢" if defense['rank'] in ['terrible', 'poor'] else "🟡" if defense['rank'] == 'average' else "🔴"
            lines.append(f"{rank_emoji} Defense vs Position: {defense['rank'].title()} (#{defense['rank_number']})")
            lines.append(f"📊 Points Allowed Avg: {defense['points_allowed_avg']:.1f}")
        
        # Location impact
        location = analysis['location_impact']
        if location['has_data']:
            loc_emoji = "🏠" if analysis['is_home'] else "✈️"
            perf = location['performance_vs_location']
            lines.append(f"{loc_emoji} Location Impact: {perf} at {location['location']}")
        
        # Recent trends
        trends = analysis['recent_trends']
        if trends['has_data']:
            trend_emoji = "📈" if trends['trending'] == 'up' else "📉" if trends['trending'] == 'down' else "➡️"
            lines.append(f"{trend_emoji} Recent Form: {trends['trending']} ({trends['last_3_avg']:.1f} L3)")
        
        # Weather
        weather = analysis['weather_impact']
        if weather['impact'] != 'none':
            weather_emoji = "🌧️" if weather.get('precipitation', 0) > 0 else "💨" if weather.get('wind_speed', 0) > 15 else "🌤️"
            lines.append(f"{weather_emoji} Weather: {weather['notes']}")
        
        return "\n".join(lines)

# Sample data loading function
def load_sample_matchup_data(analyzer: MatchupAnalyzer) -> None:
    """Load sample matchup data for testing"""
    
    # Sample defense stats
    defense_data = [
        ('BAL', 'WR', DefenseStats('BAL', 'WR', 18.2, 220.0, 15, 12, 8, 12.5, 0.65, 0.42)),
        ('BAL', 'TE', DefenseStats('BAL', 'TE', 18.2, 220.0, 8, 12, 5, 8.1, 0.65, 0.42)),
        ('SF', 'RB', DefenseStats('SF', 'RB', 16.8, 95.0, 8, 15, 3, 15.8, 0.58, 0.48)),
        ('NYJ', 'QB', DefenseStats('NYJ', 'QB', 19.5, 210.0, 12, 18, 12, 14.2, 0.72, 0.38, 0.35)),
        ('MIA', 'WR', DefenseStats('MIA', 'WR', 24.1, 280.0, 20, 8, 28, 18.9, 0.45, 0.35)),
    ]
    
    for team, pos, stats in defense_data:
        analyzer.add_defense_stats(team, pos, stats)
    
    # Sample home/away trends
    home_away_data = [
        (1, HomeAwayTrend(1, 4, 18.2, 7.5, 12.0, 4, 15.1, 6.8, 10.5)),  # Better at home
        (2, HomeAwayTrend(2, 3, 22.5, 9.2, 15.0, 5, 21.8, 8.9, 14.2)),  # Similar home/away
        (3, HomeAwayTrend(3, 5, 16.3, 6.1, 8.5, 3, 19.7, 7.2, 10.1)),   # Better away
    ]
    
    for player_id, trend in home_away_data:
        analyzer.add_home_away_trend(player_id, trend)
    
    # Sample recent trends
    recent_trend_data = [
        (1, RecentTrend(1, 3, 21.3, 16.8, 'up', 0.75, 0.28, 0.05, 0.15)),     # Trending up
        (2, RecentTrend(2, 3, 18.9, 20.1, 'down', 0.68, 0.22, -0.03, -0.08)), # Trending down
        (3, RecentTrend(3, 3, 17.5, 17.2, 'stable', 0.82, 0.25, 0.01, 0.02)), # Stable
    ]
    
    for player_id, trend in recent_trend_data:
        analyzer.add_recent_trend(player_id, trend)

if __name__ == "__main__":
    print("🎯 MATCHUP ANALYSIS SYSTEM")
    print("=" * 40)
    
    analyzer = MatchupAnalyzer()
    load_sample_matchup_data(analyzer)
    
    # Test matchup analysis
    test_matchups = [
        (1, "Cooper Kupp", "WR", "BAL", True, 8),
        (2, "Travis Kelce", "TE", "SF", False, 8),
        (3, "Josh Allen", "QB", "NYJ", True, 8),
    ]
    
    for player_id, name, position, opponent, is_home, week in test_matchups:
        analysis = analyzer.analyze_matchup(player_id, name, position, opponent, is_home, week)
        print(analyzer.get_matchup_summary(analysis))
        print()