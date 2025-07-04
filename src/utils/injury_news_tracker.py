#!/usr/bin/env python3
"""
Injury and News Tracking System
Tracks player injury status, news sentiment, and impact analysis
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

class InjuryStatus(Enum):
    HEALTHY = "healthy"
    QUESTIONABLE = "questionable"  # Q
    DOUBTFUL = "doubtful"         # D
    OUT = "out"                   # O
    IR = "injured_reserve"        # IR
    PUP = "physically_unable"     # PUP
    NFI = "non_football_injury"   # NFI

class NewsImpact(Enum):
    VERY_POSITIVE = "very_positive"  # +2
    POSITIVE = "positive"            # +1
    NEUTRAL = "neutral"              # 0
    NEGATIVE = "negative"            # -1
    VERY_NEGATIVE = "very_negative"  # -2

@dataclass
class InjuryReport:
    """Player injury information"""
    player_id: int
    player_name: str
    injury_status: InjuryStatus
    body_part: Optional[str] = None
    description: Optional[str] = None
    week_designation: Optional[str] = None
    last_updated: datetime = None
    source: str = "manual"
    
    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.utcnow()

@dataclass
class NewsItem:
    """Player news item"""
    player_id: int
    player_name: str
    headline: str
    content: str
    impact: NewsImpact
    confidence: float  # 0.0 to 1.0
    timestamp: datetime
    source: str
    categories: List[str]  # ['injury', 'trade', 'suspension', 'performance']
    
    def get_fantasy_impact_score(self) -> float:
        """Get numerical impact score for fantasy purposes"""
        impact_values = {
            NewsImpact.VERY_POSITIVE: 2.0,
            NewsImpact.POSITIVE: 1.0,
            NewsImpact.NEUTRAL: 0.0,
            NewsImpact.NEGATIVE: -1.0,
            NewsImpact.VERY_NEGATIVE: -2.0
        }
        return impact_values[self.impact] * self.confidence

class InjuryNewsTracker:
    """Track and analyze player injuries and news"""
    
    def __init__(self):
        self.injury_reports: Dict[int, InjuryReport] = {}
        self.news_items: List[NewsItem] = []
        self.logger = logging.getLogger(__name__)
    
    def update_injury_status(self, player_id: int, player_name: str, 
                           status: InjuryStatus, **kwargs) -> None:
        """Update player injury status"""
        self.injury_reports[player_id] = InjuryReport(
            player_id=player_id,
            player_name=player_name,
            injury_status=status,
            **kwargs
        )
        
        self.logger.info(f"Updated injury status for {player_name}: {status.value}")
    
    def add_news_item(self, player_id: int, player_name: str, headline: str,
                     content: str, impact: NewsImpact, confidence: float = 0.8,
                     source: str = "manual", categories: List[str] = None) -> None:
        """Add news item for player"""
        if categories is None:
            categories = ['general']
        
        news_item = NewsItem(
            player_id=player_id,
            player_name=player_name,
            headline=headline,
            content=content,
            impact=impact,
            confidence=confidence,
            timestamp=datetime.utcnow(),
            source=source,
            categories=categories
        )
        
        self.news_items.append(news_item)
        self.logger.info(f"Added news for {player_name}: {headline}")
    
    def get_player_injury_status(self, player_id: int) -> Optional[InjuryReport]:
        """Get current injury status for player"""
        return self.injury_reports.get(player_id)
    
    def get_recent_news(self, player_id: int, days: int = 7) -> List[NewsItem]:
        """Get recent news for player"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        return [
            news for news in self.news_items
            if news.player_id == player_id and news.timestamp >= cutoff_date
        ]
    
    def calculate_player_news_impact(self, player_id: int, days: int = 3) -> float:
        """Calculate overall news impact score for player"""
        recent_news = self.get_recent_news(player_id, days)
        
        if not recent_news:
            return 0.0
        
        # Weight recent news more heavily
        total_impact = 0.0
        total_weight = 0.0
        
        for news in recent_news:
            # More recent news gets higher weight
            age_hours = (datetime.utcnow() - news.timestamp).total_seconds() / 3600
            weight = max(0.1, 1.0 - (age_hours / (days * 24)))
            
            impact_score = news.get_fantasy_impact_score()
            total_impact += impact_score * weight
            total_weight += weight
        
        return total_impact / total_weight if total_weight > 0 else 0.0
    
    def get_injury_risk_multiplier(self, player_id: int) -> float:
        """Get risk multiplier based on injury status"""
        injury = self.get_player_injury_status(player_id)
        
        if not injury:
            return 1.0
        
        risk_multipliers = {
            InjuryStatus.HEALTHY: 1.0,
            InjuryStatus.QUESTIONABLE: 0.85,
            InjuryStatus.DOUBTFUL: 0.4,
            InjuryStatus.OUT: 0.0,
            InjuryStatus.IR: 0.0,
            InjuryStatus.PUP: 0.0,
            InjuryStatus.NFI: 0.0
        }
        
        return risk_multipliers.get(injury.injury_status, 0.5)
    
    def analyze_injury_trends(self, player_id: int) -> Dict[str, Any]:
        """Analyze injury patterns for a player"""
        # This would analyze historical injury data
        # For now, return basic analysis
        
        injury = self.get_player_injury_status(player_id)
        recent_news = self.get_recent_news(player_id, 14)
        
        injury_related_news = [
            news for news in recent_news 
            if 'injury' in news.categories
        ]
        
        return {
            'current_status': injury.injury_status.value if injury else 'healthy',
            'injury_news_count': len(injury_related_news),
            'overall_trend': self._get_injury_trend(injury_related_news),
            'risk_level': self._assess_injury_risk(injury, injury_related_news)
        }
    
    def _get_injury_trend(self, injury_news: List[NewsItem]) -> str:
        """Determine if injury trend is improving or worsening"""
        if not injury_news:
            return 'stable'
        
        # Sort by timestamp, most recent first
        sorted_news = sorted(injury_news, key=lambda x: x.timestamp, reverse=True)
        
        if len(sorted_news) < 2:
            return 'stable'
        
        recent_impact = sorted_news[0].get_fantasy_impact_score()
        older_impact = sorted_news[-1].get_fantasy_impact_score()
        
        if recent_impact > older_impact + 0.5:
            return 'improving'
        elif recent_impact < older_impact - 0.5:
            return 'worsening'
        else:
            return 'stable'
    
    def _assess_injury_risk(self, injury: Optional[InjuryReport], 
                          injury_news: List[NewsItem]) -> str:
        """Assess overall injury risk level"""
        if injury and injury.injury_status in [InjuryStatus.OUT, InjuryStatus.IR]:
            return 'high'
        
        if injury and injury.injury_status == InjuryStatus.DOUBTFUL:
            return 'medium-high'
        
        if injury and injury.injury_status == InjuryStatus.QUESTIONABLE:
            return 'medium'
        
        # Check news sentiment
        negative_news_count = sum(
            1 for news in injury_news 
            if news.impact in [NewsImpact.NEGATIVE, NewsImpact.VERY_NEGATIVE]
        )
        
        if negative_news_count >= 2:
            return 'medium'
        
        return 'low'
    
    def get_player_status_summary(self, player_id: int, player_name: str) -> str:
        """Get formatted status summary for player"""
        injury = self.get_player_injury_status(player_id)
        news_impact = self.calculate_player_news_impact(player_id)
        risk_multiplier = self.get_injury_risk_multiplier(player_id)
        
        lines = [f"📊 {player_name} STATUS REPORT"]
        lines.append("-" * 30)
        
        # Injury status
        if injury:
            status_emoji = {
                InjuryStatus.HEALTHY: "✅",
                InjuryStatus.QUESTIONABLE: "⚠️",
                InjuryStatus.DOUBTFUL: "🔶",
                InjuryStatus.OUT: "❌",
                InjuryStatus.IR: "🚫",
                InjuryStatus.PUP: "🚫",
                InjuryStatus.NFI: "🚫"
            }
            
            emoji = status_emoji.get(injury.injury_status, "❓")
            lines.append(f"{emoji} Status: {injury.injury_status.value.title()}")
            
            if injury.body_part:
                lines.append(f"🏥 Injury: {injury.body_part}")
        else:
            lines.append("✅ Status: Healthy")
        
        # News impact
        if abs(news_impact) > 0.1:
            impact_emoji = "📈" if news_impact > 0 else "📉"
            lines.append(f"{impact_emoji} News Impact: {news_impact:+.1f}")
        
        # Risk assessment
        risk_emoji = "🟢" if risk_multiplier > 0.8 else "🟡" if risk_multiplier > 0.4 else "🔴"
        lines.append(f"{risk_emoji} Play Risk: {risk_multiplier:.0%}")
        
        return "\n".join(lines)

# Sample data for testing
def load_sample_injury_data(tracker: InjuryNewsTracker) -> None:
    """Load sample injury and news data"""
    
    # Sample injury reports
    sample_injuries = [
        (1, "Christian McCaffrey", InjuryStatus.QUESTIONABLE, {"body_part": "hamstring"}),
        (2, "Ja'Marr Chase", InjuryStatus.HEALTHY),
        (3, "Cooper Kupp", InjuryStatus.DOUBTFUL, {"body_part": "ankle"}),
        (4, "Jonathan Taylor", InjuryStatus.OUT, {"body_part": "back"}),
    ]
    
    for player_id, name, status, kwargs in sample_injuries:
        tracker.update_injury_status(player_id, name, status, **kwargs)
    
    # Sample news items
    sample_news = [
        (1, "Christian McCaffrey", "CMC practices in limited capacity", 
         "Participated in walkthrough", NewsImpact.POSITIVE, 0.7, ['injury']),
        (2, "Ja'Marr Chase", "Chase targets increase with Burrow healthy",
         "Expected heavy target share", NewsImpact.POSITIVE, 0.8, ['performance']),
        (3, "Cooper Kupp", "Kupp unlikely to play Sunday",
         "Ankle injury worse than expected", NewsImpact.VERY_NEGATIVE, 0.9, ['injury']),
        (4, "Jonathan Taylor", "Taylor placed on IR",
         "Back injury requires extended rest", NewsImpact.VERY_NEGATIVE, 1.0, ['injury']),
    ]
    
    for player_id, name, headline, content, impact, confidence, categories in sample_news:
        tracker.add_news_item(player_id, name, headline, content, impact, confidence, categories=categories)

if __name__ == "__main__":
    # Test the injury and news tracking system
    print("🏥 INJURY & NEWS TRACKING SYSTEM")
    print("=" * 40)
    
    tracker = InjuryNewsTracker()
    load_sample_injury_data(tracker)
    
    # Test player status summaries
    test_players = [(1, "Christian McCaffrey"), (3, "Cooper Kupp"), (4, "Jonathan Taylor")]
    
    for player_id, name in test_players:
        print(tracker.get_player_status_summary(player_id, name))
        print()