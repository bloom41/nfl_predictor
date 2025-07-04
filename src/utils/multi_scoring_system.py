#!/usr/bin/env python3
"""
Multi-Scoring System
Supports Standard, Half PPR, Full PPR, and custom scoring formats
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dataclasses import dataclass
from typing import Dict, Any, Optional
from enum import Enum

class ScoringType(Enum):
    STANDARD = "standard"
    HALF_PPR = "half_ppr"
    FULL_PPR = "full_ppr"
    CUSTOM = "custom"

@dataclass
class ScoringSettings:
    """Fantasy scoring settings"""
    # Passing
    passing_yards_per_point: float = 25.0  # 1 pt per 25 yards
    passing_td_points: float = 4.0
    interception_points: float = -2.0
    
    # Rushing
    rushing_yards_per_point: float = 10.0  # 1 pt per 10 yards
    rushing_td_points: float = 6.0
    
    # Receiving
    receiving_yards_per_point: float = 10.0  # 1 pt per 10 yards
    receiving_td_points: float = 6.0
    reception_points: float = 0.5  # Half PPR default
    
    # Other
    fumble_lost_points: float = -2.0
    two_point_conversion_points: float = 2.0
    
    # Bonus scoring (optional)
    long_td_bonus: Dict[int, float] = None  # {40: 2.0, 50: 4.0} yards: bonus
    high_yardage_bonus: Dict[int, float] = None  # {100: 3.0, 200: 6.0}

class ScoringCalculator:
    """Calculate fantasy points with different scoring systems"""
    
    PRESET_SCORING = {
        ScoringType.STANDARD: ScoringSettings(reception_points=0.0),
        ScoringType.HALF_PPR: ScoringSettings(reception_points=0.5),
        ScoringType.FULL_PPR: ScoringSettings(reception_points=1.0),
    }
    
    def __init__(self, scoring_type: ScoringType = ScoringType.HALF_PPR, 
                 custom_settings: Optional[ScoringSettings] = None):
        self.scoring_type = scoring_type
        
        if scoring_type == ScoringType.CUSTOM and custom_settings:
            self.settings = custom_settings
        else:
            self.settings = self.PRESET_SCORING.get(scoring_type, 
                                                  self.PRESET_SCORING[ScoringType.HALF_PPR])
    
    def calculate_fantasy_points(self, stats: Dict[str, Any]) -> float:
        """Calculate fantasy points for given stats"""
        points = 0.0
        
        # Passing points
        points += (stats.get('passing_yards', 0) / self.settings.passing_yards_per_point)
        points += (stats.get('passing_tds', 0) * self.settings.passing_td_points)
        points += (stats.get('interceptions', 0) * self.settings.interception_points)
        
        # Rushing points
        points += (stats.get('rushing_yards', 0) / self.settings.rushing_yards_per_point)
        points += (stats.get('rushing_tds', 0) * self.settings.rushing_td_points)
        
        # Receiving points
        points += (stats.get('receiving_yards', 0) / self.settings.receiving_yards_per_point)
        points += (stats.get('receiving_tds', 0) * self.settings.receiving_td_points)
        points += (stats.get('receptions', 0) * self.settings.reception_points)
        
        # Other scoring
        points += (stats.get('fumbles_lost', 0) * self.settings.fumble_lost_points)
        points += (stats.get('two_point_conversions', 0) * self.settings.two_point_conversion_points)
        
        # Bonus scoring
        if self.settings.long_td_bonus:
            points += self._calculate_long_td_bonus(stats)
        
        if self.settings.high_yardage_bonus:
            points += self._calculate_yardage_bonus(stats)
        
        return max(points, 0.0)
    
    def _calculate_long_td_bonus(self, stats: Dict[str, Any]) -> float:
        """Calculate bonus points for long TDs"""
        bonus = 0.0
        for min_yards, bonus_points in sorted(self.settings.long_td_bonus.items(), reverse=True):
            long_tds = stats.get(f'tds_{min_yards}_plus', 0)
            bonus += long_tds * bonus_points
        return bonus
    
    def _calculate_yardage_bonus(self, stats: Dict[str, Any]) -> float:
        """Calculate bonus points for high yardage games"""
        bonus = 0.0
        total_yards = (stats.get('passing_yards', 0) + 
                      stats.get('rushing_yards', 0) + 
                      stats.get('receiving_yards', 0))
        
        for min_yards, bonus_points in sorted(self.settings.high_yardage_bonus.items(), reverse=True):
            if total_yards >= min_yards:
                bonus += bonus_points
                break
        
        return bonus
    
    def get_scoring_display(self) -> str:
        """Get display string for current scoring settings"""
        if self.scoring_type == ScoringType.STANDARD:
            return "Standard (No PPR)"
        elif self.scoring_type == ScoringType.HALF_PPR:
            return "Half PPR (0.5 pts/rec)"
        elif self.scoring_type == ScoringType.FULL_PPR:
            return "Full PPR (1.0 pts/rec)"
        else:
            return f"Custom ({self.settings.reception_points} pts/rec)"

# Common league scoring presets
COMMON_LEAGUE_SETTINGS = {
    "espn_standard": ScoringSettings(
        reception_points=0.0,
        passing_td_points=4.0,
        rushing_td_points=6.0,
        receiving_td_points=6.0
    ),
    "yahoo_half_ppr": ScoringSettings(
        reception_points=0.5,
        passing_td_points=4.0,
        rushing_td_points=6.0,
        receiving_td_points=6.0
    ),
    "sleeper_full_ppr": ScoringSettings(
        reception_points=1.0,
        passing_td_points=4.0,
        rushing_td_points=6.0,
        receiving_td_points=6.0,
        high_yardage_bonus={100: 3.0, 200: 6.0}
    ),
    "superflex": ScoringSettings(
        reception_points=0.5,
        passing_td_points=6.0,  # Higher QB scoring
        rushing_td_points=6.0,
        receiving_td_points=6.0
    )
}

def get_scoring_calculator(scoring_format: str) -> ScoringCalculator:
    """Get scoring calculator for popular formats"""
    if scoring_format in COMMON_LEAGUE_SETTINGS:
        return ScoringCalculator(ScoringType.CUSTOM, COMMON_LEAGUE_SETTINGS[scoring_format])
    elif scoring_format.lower() == "standard":
        return ScoringCalculator(ScoringType.STANDARD)
    elif scoring_format.lower() == "half_ppr":
        return ScoringCalculator(ScoringType.HALF_PPR)
    elif scoring_format.lower() == "full_ppr":
        return ScoringCalculator(ScoringType.FULL_PPR)
    else:
        # Default to half PPR
        return ScoringCalculator(ScoringType.HALF_PPR)

if __name__ == "__main__":
    # Test different scoring systems
    test_stats = {
        'passing_yards': 300,
        'passing_tds': 2,
        'interceptions': 1,
        'rushing_yards': 50,
        'rushing_tds': 1,
        'receiving_yards': 80,
        'receiving_tds': 1,
        'receptions': 6
    }
    
    print("🏈 MULTI-SCORING SYSTEM TEST")
    print("=" * 40)
    print(f"Test stats: {test_stats}")
    print()
    
    for scoring_type in [ScoringType.STANDARD, ScoringType.HALF_PPR, ScoringType.FULL_PPR]:
        calc = ScoringCalculator(scoring_type)
        points = calc.calculate_fantasy_points(test_stats)
        print(f"{calc.get_scoring_display()}: {points:.1f} points")
    
    print()
    print("Common League Formats:")
    for format_name in COMMON_LEAGUE_SETTINGS.keys():
        calc = get_scoring_calculator(format_name)
        points = calc.calculate_fantasy_points(test_stats)
        print(f"{format_name}: {points:.1f} points")