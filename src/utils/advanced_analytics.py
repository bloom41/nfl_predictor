#!/usr/bin/env python3
"""
Advanced Analytics System
Target share, red zone usage, snap counts, and advanced metrics
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import logging
import statistics

logger = logging.getLogger(__name__)

@dataclass
class SnapCountData:
    """Player snap count information"""
    player_id: int
    week: int
    season: int
    total_snaps: int
    offensive_snaps: int
    snap_percentage: float
    routes_run: Optional[int] = None
    route_participation: Optional[float] = None

@dataclass
class TargetShareData:
    """Target share and usage data"""
    player_id: int
    week: int
    season: int
    targets: int
    team_targets: int
    target_share: float
    air_yards: Optional[int] = None
    target_depth: Optional[float] = None
    slot_rate: Optional[float] = None
    
    def get_target_quality_score(self) -> float:
        """Calculate target quality score"""
        base_score = self.target_share * 100
        
        # Adjust for target depth (deeper targets generally better)
        if self.target_depth:
            if self.target_depth > 15:
                base_score *= 1.1  # Deep targets bonus
            elif self.target_depth < 5:
                base_score *= 0.9  # Short targets penalty
        
        return min(base_score, 100.0)

@dataclass
class RedZoneUsage:
    """Red zone usage analytics"""
    player_id: int
    week: int
    season: int
    red_zone_snaps: int
    red_zone_targets: int
    red_zone_carries: int
    goal_line_snaps: int
    red_zone_tds: int
    team_red_zone_plays: int
    
    def get_red_zone_share(self) -> float:
        """Calculate red zone opportunity share"""
        total_opportunities = self.red_zone_targets + self.red_zone_carries
        if self.team_red_zone_plays == 0:
            return 0.0
        return total_opportunities / self.team_red_zone_plays
    
    def get_goal_line_rate(self) -> float:
        """Calculate goal line snap rate"""
        if self.red_zone_snaps == 0:
            return 0.0
        return self.goal_line_snaps / self.red_zone_snaps

@dataclass
class PlayerUsageTrends:
    """Comprehensive player usage trends"""
    player_id: int
    player_name: str
    position: str
    
    # Historical data
    snap_data: List[SnapCountData]
    target_data: List[TargetShareData]
    red_zone_data: List[RedZoneUsage]
    
    # Calculated trends
    snap_trend: Optional[float] = None
    target_share_trend: Optional[float] = None
    red_zone_trend: Optional[float] = None
    consistency_score: Optional[float] = None

class AdvancedAnalytics:
    """Advanced fantasy football analytics"""
    
    def __init__(self):
        self.snap_data: Dict[int, List[SnapCountData]] = {}
        self.target_data: Dict[int, List[TargetShareData]] = {}
        self.red_zone_data: Dict[int, List[RedZoneUsage]] = {}
        self.logger = logging.getLogger(__name__)
    
    def add_snap_data(self, player_id: int, snap_data: SnapCountData) -> None:
        """Add snap count data for player"""
        if player_id not in self.snap_data:
            self.snap_data[player_id] = []
        self.snap_data[player_id].append(snap_data)
        self.snap_data[player_id].sort(key=lambda x: (x.season, x.week))
    
    def add_target_data(self, player_id: int, target_data: TargetShareData) -> None:
        """Add target share data for player"""
        if player_id not in self.target_data:
            self.target_data[player_id] = []
        self.target_data[player_id].append(target_data)
        self.target_data[player_id].sort(key=lambda x: (x.season, x.week))
    
    def add_red_zone_data(self, player_id: int, rz_data: RedZoneUsage) -> None:
        """Add red zone usage data for player"""
        if player_id not in self.red_zone_data:
            self.red_zone_data[player_id] = []
        self.red_zone_data[player_id].append(rz_data)
        self.red_zone_data[player_id].sort(key=lambda x: (x.season, x.week))
    
    def calculate_usage_trends(self, player_id: int, weeks_back: int = 6) -> PlayerUsageTrends:
        """Calculate comprehensive usage trends for player"""
        
        # Get recent data
        recent_snaps = self._get_recent_data(self.snap_data.get(player_id, []), weeks_back)
        recent_targets = self._get_recent_data(self.target_data.get(player_id, []), weeks_back)
        recent_rz = self._get_recent_data(self.red_zone_data.get(player_id, []), weeks_back)
        
        # Calculate trends
        snap_trend = self._calculate_trend([s.snap_percentage for s in recent_snaps])
        target_trend = self._calculate_trend([t.target_share for t in recent_targets])
        rz_trend = self._calculate_trend([r.get_red_zone_share() for r in recent_rz])
        
        # Calculate consistency
        consistency = self._calculate_consistency_score(player_id, weeks_back)
        
        return PlayerUsageTrends(
            player_id=player_id,
            player_name=f"Player_{player_id}",  # Would be filled from database
            position="Unknown",  # Would be filled from database
            snap_data=recent_snaps,
            target_data=recent_targets,
            red_zone_data=recent_rz,
            snap_trend=snap_trend,
            target_share_trend=target_trend,
            red_zone_trend=rz_trend,
            consistency_score=consistency
        )
    
    def _get_recent_data(self, data_list: List, weeks_back: int) -> List:
        """Get recent data points"""
        if not data_list:
            return []
        
        # Sort by season and week, take most recent
        sorted_data = sorted(data_list, key=lambda x: (x.season, x.week), reverse=True)
        return sorted_data[:weeks_back]
    
    def _calculate_trend(self, values: List[float]) -> Optional[float]:
        """Calculate trend direction (-1 to 1, where 1 is strongly increasing)"""
        if len(values) < 3:
            return None
        
        # Simple linear regression slope
        n = len(values)
        x_values = list(range(n))
        
        # Calculate slope
        x_mean = statistics.mean(x_values)
        y_mean = statistics.mean(values)
        
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, values))
        denominator = sum((x - x_mean) ** 2 for x in x_values)
        
        if denominator == 0:
            return 0.0
        
        slope = numerator / denominator
        
        # Normalize slope to -1 to 1 range based on the data range
        value_range = max(values) - min(values)
        if value_range == 0:
            return 0.0
        
        normalized_slope = slope / (value_range / n)
        return max(-1.0, min(1.0, normalized_slope))
    
    def _calculate_consistency_score(self, player_id: int, weeks_back: int) -> float:
        """Calculate player consistency score (0-1)"""
        # This would analyze variance in fantasy points, snap counts, etc.
        # For now, return a basic calculation
        
        recent_snaps = self._get_recent_data(self.snap_data.get(player_id, []), weeks_back)
        
        if len(recent_snaps) < 3:
            return 0.5  # Neutral score for insufficient data
        
        snap_percentages = [s.snap_percentage for s in recent_snaps]
        
        if not snap_percentages:
            return 0.5
        
        # Calculate coefficient of variation (lower is more consistent)
        mean_snap = statistics.mean(snap_percentages)
        if mean_snap == 0:
            return 0.5
        
        std_snap = statistics.stdev(snap_percentages) if len(snap_percentages) > 1 else 0
        cv = std_snap / mean_snap
        
        # Convert to 0-1 score (lower CV = higher consistency)
        consistency = max(0.0, 1.0 - cv)
        return min(1.0, consistency)
    
    def analyze_target_efficiency(self, player_id: int, weeks_back: int = 6) -> Dict[str, Any]:
        """Analyze target efficiency and quality"""
        recent_targets = self._get_recent_data(self.target_data.get(player_id, []), weeks_back)
        
        if not recent_targets:
            return {'error': 'No target data available'}
        
        # Calculate metrics
        total_targets = sum(t.targets for t in recent_targets)
        avg_target_share = statistics.mean([t.target_share for t in recent_targets])
        avg_depth = statistics.mean([t.target_depth for t in recent_targets if t.target_depth])
        quality_scores = [t.get_target_quality_score() for t in recent_targets]
        avg_quality = statistics.mean(quality_scores) if quality_scores else 0
        
        # Calculate target trends
        target_share_values = [t.target_share for t in recent_targets]
        share_trend = self._calculate_trend(target_share_values)
        
        return {
            'total_targets': total_targets,
            'avg_target_share': avg_target_share,
            'target_share_trend': share_trend,
            'avg_target_depth': avg_depth,
            'target_quality_score': avg_quality,
            'weeks_analyzed': len(recent_targets),
            'trend_direction': self._get_trend_description(share_trend)
        }
    
    def analyze_red_zone_role(self, player_id: int, weeks_back: int = 6) -> Dict[str, Any]:
        """Analyze red zone usage and efficiency"""
        recent_rz = self._get_recent_data(self.red_zone_data.get(player_id, []), weeks_back)
        
        if not recent_rz:
            return {'error': 'No red zone data available'}
        
        # Calculate metrics
        total_rz_opportunities = sum(r.red_zone_targets + r.red_zone_carries for r in recent_rz)
        total_rz_tds = sum(r.red_zone_tds for r in recent_rz)
        avg_rz_share = statistics.mean([r.get_red_zone_share() for r in recent_rz])
        avg_goal_line_rate = statistics.mean([r.get_goal_line_rate() for r in recent_rz])
        
        # Calculate efficiency
        rz_efficiency = (total_rz_tds / total_rz_opportunities) if total_rz_opportunities > 0 else 0
        
        # Calculate trends
        rz_share_values = [r.get_red_zone_share() for r in recent_rz]
        rz_trend = self._calculate_trend(rz_share_values)
        
        return {
            'total_rz_opportunities': total_rz_opportunities,
            'total_rz_touchdowns': total_rz_tds,
            'avg_rz_share': avg_rz_share,
            'avg_goal_line_rate': avg_goal_line_rate,
            'rz_efficiency': rz_efficiency,
            'rz_trend': rz_trend,
            'weeks_analyzed': len(recent_rz),
            'trend_direction': self._get_trend_description(rz_trend)
        }
    
    def analyze_snap_count_trends(self, player_id: int, weeks_back: int = 6) -> Dict[str, Any]:
        """Analyze snap count trends and usage"""
        recent_snaps = self._get_recent_data(self.snap_data.get(player_id, []), weeks_back)
        
        if not recent_snaps:
            return {'error': 'No snap count data available'}
        
        # Calculate metrics
        avg_snap_pct = statistics.mean([s.snap_percentage for s in recent_snaps])
        avg_routes = statistics.mean([s.routes_run for s in recent_snaps if s.routes_run])
        avg_route_participation = statistics.mean([s.route_participation for s in recent_snaps if s.route_participation])
        
        # Calculate trends
        snap_pct_values = [s.snap_percentage for s in recent_snaps]
        snap_trend = self._calculate_trend(snap_pct_values)
        
        # Determine usage tier
        usage_tier = self._get_usage_tier(avg_snap_pct)
        
        return {
            'avg_snap_percentage': avg_snap_pct,
            'avg_routes_run': avg_routes,
            'avg_route_participation': avg_route_participation,
            'snap_trend': snap_trend,
            'usage_tier': usage_tier,
            'weeks_analyzed': len(recent_snaps),
            'trend_direction': self._get_trend_description(snap_trend)
        }
    
    def _get_trend_description(self, trend_value: Optional[float]) -> str:
        """Get descriptive text for trend value"""
        if trend_value is None:
            return 'insufficient_data'
        elif trend_value > 0.3:
            return 'strongly_increasing'
        elif trend_value > 0.1:
            return 'increasing'
        elif trend_value > -0.1:
            return 'stable'
        elif trend_value > -0.3:
            return 'decreasing'
        else:
            return 'strongly_decreasing'
    
    def _get_usage_tier(self, snap_percentage: float) -> str:
        """Categorize usage level"""
        if snap_percentage >= 80:
            return 'bellcow'
        elif snap_percentage >= 60:
            return 'heavy_usage'
        elif snap_percentage >= 40:
            return 'moderate_usage'
        elif snap_percentage >= 20:
            return 'limited_usage'
        else:
            return 'minimal_usage'
    
    def generate_player_analytics_report(self, player_id: int, player_name: str, 
                                       position: str, weeks_back: int = 6) -> str:
        """Generate comprehensive analytics report for player"""
        
        usage_trends = self.calculate_usage_trends(player_id, weeks_back)
        target_analysis = self.analyze_target_efficiency(player_id, weeks_back)
        rz_analysis = self.analyze_red_zone_role(player_id, weeks_back)
        snap_analysis = self.analyze_snap_count_trends(player_id, weeks_back)
        
        lines = []
        lines.append(f"📊 ADVANCED ANALYTICS - {player_name} ({position})")
        lines.append("=" * 50)
        lines.append(f"📅 Analysis Period: Last {weeks_back} weeks")
        lines.append("")
        
        # Snap Count Analysis
        if 'error' not in snap_analysis:
            lines.append("⏱️  SNAP COUNT ANALYSIS")
            lines.append(f"   Usage Tier: {snap_analysis['usage_tier'].replace('_', ' ').title()}")
            lines.append(f"   Avg Snap %: {snap_analysis['avg_snap_percentage']:.1f}%")
            lines.append(f"   Trend: {snap_analysis['trend_direction'].replace('_', ' ').title()}")
            if snap_analysis['avg_routes_run']:
                lines.append(f"   Avg Routes: {snap_analysis['avg_routes_run']:.1f}")
            lines.append("")
        
        # Target Analysis (for skill positions)
        if position in ['WR', 'TE', 'RB'] and 'error' not in target_analysis:
            lines.append("🎯 TARGET ANALYSIS")
            lines.append(f"   Target Share: {target_analysis['avg_target_share']:.1f}%")
            lines.append(f"   Quality Score: {target_analysis['target_quality_score']:.1f}/100")
            if target_analysis['avg_target_depth']:
                lines.append(f"   Avg Depth: {target_analysis['avg_target_depth']:.1f} yards")
            lines.append(f"   Trend: {target_analysis['trend_direction'].replace('_', ' ').title()}")
            lines.append("")
        
        # Red Zone Analysis
        if 'error' not in rz_analysis:
            lines.append("🏈 RED ZONE ANALYSIS")
            lines.append(f"   RZ Share: {rz_analysis['avg_rz_share']:.1f}%")
            lines.append(f"   RZ TDs: {rz_analysis['total_rz_touchdowns']} in {rz_analysis['total_rz_opportunities']} opportunities")
            lines.append(f"   RZ Efficiency: {rz_analysis['rz_efficiency']:.1%}")
            lines.append(f"   Goal Line Rate: {rz_analysis['avg_goal_line_rate']:.1%}")
            lines.append(f"   Trend: {rz_analysis['trend_direction'].replace('_', ' ').title()}")
            lines.append("")
        
        # Overall Assessment
        lines.append("🔍 OVERALL ASSESSMENT")
        if usage_trends.consistency_score:
            consistency_desc = "High" if usage_trends.consistency_score > 0.7 else "Moderate" if usage_trends.consistency_score > 0.4 else "Low"
            lines.append(f"   Consistency: {consistency_desc} ({usage_trends.consistency_score:.2f})")
        
        # Key insights
        insights = self._generate_key_insights(usage_trends, target_analysis, rz_analysis, snap_analysis)
        if insights:
            lines.append("   Key Insights:")
            for insight in insights:
                lines.append(f"   • {insight}")
        
        return "\n".join(lines)
    
    def _generate_key_insights(self, usage: PlayerUsageTrends, targets: Dict, 
                             red_zone: Dict, snaps: Dict) -> List[str]:
        """Generate key insights from analytics data"""
        insights = []
        
        # Snap trend insights
        if snaps.get('snap_trend', 0) > 0.2:
            insights.append("Increasing snap share indicates growing role")
        elif snaps.get('snap_trend', 0) < -0.2:
            insights.append("Decreasing snaps suggest diminishing role")
        
        # Target insights
        if targets.get('target_share_trend', 0) > 0.15:
            insights.append("Target share trending up - positive sign")
        elif targets.get('avg_target_share', 0) > 20:
            insights.append("High target share indicates WR1/TE1 role")
        
        # Red zone insights
        if red_zone.get('avg_rz_share', 0) > 0.3:
            insights.append("Strong red zone role boosts TD upside")
        elif red_zone.get('rz_efficiency', 0) > 0.25:
            insights.append("Excellent red zone efficiency")
        
        # Usage tier insights
        usage_tier = snaps.get('usage_tier', '')
        if usage_tier == 'bellcow':
            insights.append("Bellcow usage provides high floor")
        elif usage_tier == 'minimal_usage':
            insights.append("Limited snaps cap fantasy ceiling")
        
        return insights

def load_sample_analytics_data(analytics: AdvancedAnalytics) -> None:
    """Load sample analytics data for testing"""
    
    # Sample snap count data
    snap_samples = [
        (1, [SnapCountData(1, w, 2024, 65, 62, 85.5 + w*2, 45, 90.0) for w in range(1, 7)]),
        (2, [SnapCountData(2, w, 2024, 48, 45, 68.2 - w*1.5, 32, 75.0) for w in range(1, 7)]),
        (3, [SnapCountData(3, w, 2024, 55, 52, 78.8, 38, 82.0) for w in range(1, 7)]),
    ]
    
    for player_id, snap_list in snap_samples:
        for snap_data in snap_list:
            analytics.add_snap_data(player_id, snap_data)
    
    # Sample target share data
    target_samples = [
        (1, [TargetShareData(1, w, 2024, 8-w//2, 35, (8-w//2)/35*100, 150, 12.5, 0.65) for w in range(1, 7)]),
        (2, [TargetShareData(2, w, 2024, 6+w//3, 30, (6+w//3)/30*100, 95, 8.2, 0.45) for w in range(1, 7)]),
    ]
    
    for player_id, target_list in target_samples:
        for target_data in target_list:
            analytics.add_target_data(player_id, target_data)
    
    # Sample red zone data
    rz_samples = [
        (1, [RedZoneUsage(1, w, 2024, 12, 3, 0, 4, 1, 18) for w in range(1, 7)]),
        (2, [RedZoneUsage(2, w, 2024, 8, 2, 2, 3, 1, 16) for w in range(1, 7)]),
        (3, [RedZoneUsage(3, w, 2024, 15, 0, 5, 6, 2, 20) for w in range(1, 7)]),
    ]
    
    for player_id, rz_list in rz_samples:
        for rz_data in rz_list:
            analytics.add_red_zone_data(player_id, rz_data)

if __name__ == "__main__":
    print("📊 ADVANCED ANALYTICS SYSTEM")
    print("=" * 40)
    
    analytics = AdvancedAnalytics()
    load_sample_analytics_data(analytics)
    
    # Test analytics reports
    test_players = [
        (1, "Cooper Kupp", "WR"),
        (2, "Travis Kelce", "TE"),
        (3, "Derrick Henry", "RB")
    ]
    
    for player_id, name, position in test_players:
        report = analytics.generate_player_analytics_report(player_id, name, position)
        print(report)
        print()