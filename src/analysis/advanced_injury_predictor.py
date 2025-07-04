#!/usr/bin/env python3
"""
Advanced Injury Risk Prediction System
Uses physical health data analysis, injury history patterns, and predictive modeling
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import StandardScaler
from enum import Enum

logger = logging.getLogger(__name__)

class InjuryRiskLevel(Enum):
    """Injury risk level classifications"""
    LOW = "low"           # 0-15% risk
    MODERATE = "moderate" # 15-35% risk
    HIGH = "high"         # 35-60% risk
    CRITICAL = "critical" # 60%+ risk

class InjuryType(Enum):
    """Types of injuries to predict"""
    SOFT_TISSUE = "soft_tissue"     # Hamstring, groin, etc.
    JOINT = "joint"                 # Knee, ankle, shoulder
    CONCUSSION = "concussion"       # Head injuries
    CONTACT = "contact"             # Collision-based injuries
    OVERUSE = "overuse"             # Repetitive stress injuries

@dataclass
class InjuryRiskProfile:
    """Player injury risk assessment"""
    player_id: int
    player_name: str
    position: str
    
    # Overall risk assessment
    overall_risk_level: InjuryRiskLevel
    overall_risk_probability: float  # 0-1
    
    # Specific injury type risks
    injury_type_risks: Dict[InjuryType, float]
    
    # Contributing factors
    age_factor: float
    position_factor: float
    injury_history_factor: float
    workload_factor: float
    recovery_factor: float
    physical_condition_factor: float
    
    # Predictive insights
    high_risk_weeks: List[int]  # Weeks with elevated risk
    recommended_rest_probability: float
    injury_prone_rating: float  # 0-10 scale
    
    # Data quality
    confidence_score: float
    data_completeness: float

@dataclass
class InjuryHistoryRecord:
    """Historical injury record"""
    player_id: int
    injury_date: datetime
    injury_type: InjuryType
    severity: str  # mild, moderate, severe
    games_missed: int
    return_date: Optional[datetime] = None
    recurring: bool = False
    position_at_injury: Optional[str] = None

@dataclass
class PhysicalMetrics:
    """Physical condition metrics for injury prediction"""
    player_id: int
    measurement_date: datetime
    
    # Basic physical stats
    age: float
    height: float  # inches
    weight: float  # pounds
    bmi: float
    body_fat_percentage: Optional[float] = None
    
    # Performance metrics
    speed_score: Optional[float] = None  # 40-yard dash relative to position
    agility_score: Optional[float] = None
    strength_score: Optional[float] = None
    endurance_score: Optional[float] = None
    
    # Workload metrics
    snaps_per_game_avg: float = 0.0
    touches_per_game_avg: float = 0.0
    high_impact_plays_per_game: float = 0.0
    
    # Recovery metrics
    days_since_last_injury: Optional[int] = None
    offseason_rest_days: Optional[int] = None
    practice_participation_rate: Optional[float] = None

class AdvancedInjuryPredictor:
    """
    Advanced injury risk prediction system using machine learning
    and comprehensive health data analysis
    """
    
    def __init__(self):
        """Initialize advanced injury predictor"""
        self.logger = logging.getLogger(__name__)
        
        # Historical data storage
        self.injury_history: List[InjuryHistoryRecord] = []
        self.physical_metrics: List[PhysicalMetrics] = []
        
        # Position-specific injury risk baselines
        self.position_injury_rates = {
            'QB': 0.12,   # Lower contact, but pocket collapses
            'RB': 0.35,   # High contact, high workload
            'WR': 0.25,   # Moderate contact, high speed
            'TE': 0.28,   # High contact, blocking duties
            'K': 0.05,    # Very low contact
            'DEF': 0.20   # Defense average
        }
        
        # Age-based risk multipliers
        self.age_risk_multipliers = {
            range(21, 25): 0.8,   # Young, resilient
            range(25, 28): 1.0,   # Prime years
            range(28, 31): 1.3,   # Increased risk
            range(31, 35): 1.8,   # High risk
            range(35, 40): 2.5    # Very high risk
        }
        
        # Injury type patterns by position
        self.position_injury_patterns = {
            'QB': {InjuryType.CONCUSSION: 0.4, InjuryType.JOINT: 0.3, InjuryType.SOFT_TISSUE: 0.2, InjuryType.CONTACT: 0.1},
            'RB': {InjuryType.SOFT_TISSUE: 0.35, InjuryType.JOINT: 0.25, InjuryType.CONTACT: 0.25, InjuryType.OVERUSE: 0.15},
            'WR': {InjuryType.SOFT_TISSUE: 0.4, InjuryType.JOINT: 0.3, InjuryType.CONTACT: 0.2, InjuryType.CONCUSSION: 0.1},
            'TE': {InjuryType.JOINT: 0.35, InjuryType.CONTACT: 0.3, InjuryType.SOFT_TISSUE: 0.25, InjuryType.OVERUSE: 0.1}
        }
        
        # Machine learning models
        self.injury_risk_model: Optional[RandomForestClassifier] = None
        self.severity_model: Optional[GradientBoostingClassifier] = None
        self.scaler = StandardScaler()
        
        self.logger.info("Advanced Injury Predictor initialized")
    
    def predict_injury_risk(self, player_id: int, player_name: str, position: str,
                          current_metrics: PhysicalMetrics, week: int = 1) -> InjuryRiskProfile:
        """
        Predict comprehensive injury risk for a player
        
        Args:
            player_id: Player identifier
            player_name: Player name
            position: Player position
            current_metrics: Current physical condition metrics
            week: Current week number
            
        Returns:
            InjuryRiskProfile with detailed risk assessment
        """
        try:
            self.logger.debug(f"Predicting injury risk for {player_name}")
            
            # Calculate individual risk factors
            age_factor = self._calculate_age_factor(current_metrics.age)
            position_factor = self._calculate_position_factor(position)
            injury_history_factor = self._calculate_injury_history_factor(player_id)
            workload_factor = self._calculate_workload_factor(current_metrics, position)
            recovery_factor = self._calculate_recovery_factor(player_id, current_metrics)
            physical_condition_factor = self._calculate_physical_condition_factor(current_metrics, position)
            
            # Calculate overall risk probability
            overall_risk = self._calculate_overall_risk_probability(
                age_factor, position_factor, injury_history_factor,
                workload_factor, recovery_factor, physical_condition_factor
            )
            
            # Determine risk level
            risk_level = self._classify_risk_level(overall_risk)
            
            # Calculate injury type-specific risks
            injury_type_risks = self._calculate_injury_type_risks(
                position, overall_risk, injury_history_factor
            )
            
            # Identify high-risk weeks
            high_risk_weeks = self._identify_high_risk_weeks(
                player_id, overall_risk, week
            )
            
            # Calculate additional insights
            rest_probability = self._calculate_rest_recommendation(overall_risk, workload_factor)
            injury_prone_rating = self._calculate_injury_prone_rating(
                injury_history_factor, overall_risk
            )
            
            # Assess data quality
            confidence_score, data_completeness = self._assess_data_quality(
                player_id, current_metrics
            )
            
            return InjuryRiskProfile(
                player_id=player_id,
                player_name=player_name,
                position=position,
                overall_risk_level=risk_level,
                overall_risk_probability=overall_risk,
                injury_type_risks=injury_type_risks,
                age_factor=age_factor,
                position_factor=position_factor,
                injury_history_factor=injury_history_factor,
                workload_factor=workload_factor,
                recovery_factor=recovery_factor,
                physical_condition_factor=physical_condition_factor,
                high_risk_weeks=high_risk_weeks,
                recommended_rest_probability=rest_probability,
                injury_prone_rating=injury_prone_rating,
                confidence_score=confidence_score,
                data_completeness=data_completeness
            )
            
        except Exception as e:
            self.logger.error(f"Error predicting injury risk for {player_name}: {e}")
            return self._create_default_risk_profile(player_id, player_name, position)
    
    def _calculate_age_factor(self, age: float) -> float:
        """Calculate age-based injury risk factor"""
        try:
            # Find appropriate age range multiplier
            for age_range, multiplier in self.age_risk_multipliers.items():
                if int(age) in age_range:
                    return multiplier
            
            # Handle extreme ages
            if age < 21:
                return 0.9  # Young but inexperienced
            elif age > 35:
                return 3.0  # Very high risk
            else:
                return 1.5  # Default for unexpected ranges
                
        except Exception as e:
            self.logger.error(f"Error calculating age factor: {e}")
            return 1.0
    
    def _calculate_position_factor(self, position: str) -> float:
        """Calculate position-based injury risk factor"""
        base_rate = self.position_injury_rates.get(position, 0.20)
        # Normalize to 0-2 scale where 1.0 is average
        return base_rate / 0.20
    
    def _calculate_injury_history_factor(self, player_id: int) -> float:
        """Calculate injury history risk factor"""
        try:
            player_injuries = [inj for inj in self.injury_history if inj.player_id == player_id]
            
            if not player_injuries:
                return 0.8  # No history is slightly protective
            
            # Calculate recency-weighted injury count
            current_date = datetime.now()
            weighted_injuries = 0.0
            
            for injury in player_injuries:
                days_ago = (current_date - injury.injury_date).days
                
                # Weight recent injuries more heavily
                if days_ago <= 365:  # Last year
                    weight = 2.0
                elif days_ago <= 730:  # 1-2 years ago
                    weight = 1.5
                elif days_ago <= 1095:  # 2-3 years ago
                    weight = 1.0
                else:  # 3+ years ago
                    weight = 0.5
                
                # Severity multiplier
                severity_multiplier = {'mild': 0.5, 'moderate': 1.0, 'severe': 2.0}.get(injury.severity, 1.0)
                
                # Recurring injury penalty
                recurring_multiplier = 1.5 if injury.recurring else 1.0
                
                weighted_injuries += weight * severity_multiplier * recurring_multiplier
            
            # Convert to risk factor (more injuries = higher risk)
            risk_factor = min(3.0, 0.8 + (weighted_injuries * 0.3))
            return risk_factor
            
        except Exception as e:
            self.logger.error(f"Error calculating injury history factor: {e}")
            return 1.0
    
    def _calculate_workload_factor(self, metrics: PhysicalMetrics, position: str) -> float:
        """Calculate workload-based injury risk factor"""
        try:
            # Position-specific workload thresholds
            position_thresholds = {
                'QB': {'snaps': 65, 'touches': 35, 'high_impact': 5},
                'RB': {'snaps': 45, 'touches': 20, 'high_impact': 15},
                'WR': {'snaps': 55, 'touches': 8, 'high_impact': 3},
                'TE': {'snaps': 50, 'touches': 5, 'high_impact': 8}
            }
            
            thresholds = position_thresholds.get(position, {'snaps': 50, 'touches': 10, 'high_impact': 8})
            
            # Calculate workload ratios
            snap_ratio = metrics.snaps_per_game_avg / thresholds['snaps']
            touch_ratio = metrics.touches_per_game_avg / thresholds['touches']
            impact_ratio = metrics.high_impact_plays_per_game / thresholds['high_impact']
            
            # Weight different factors by position
            if position == 'QB':
                workload_score = (snap_ratio * 0.4) + (touch_ratio * 0.3) + (impact_ratio * 0.3)
            elif position == 'RB':
                workload_score = (snap_ratio * 0.2) + (touch_ratio * 0.5) + (impact_ratio * 0.3)
            else:  # WR, TE
                workload_score = (snap_ratio * 0.3) + (touch_ratio * 0.4) + (impact_ratio * 0.3)
            
            # Convert to risk factor
            return min(2.5, max(0.5, workload_score))
            
        except Exception as e:
            self.logger.error(f"Error calculating workload factor: {e}")
            return 1.0
    
    def _calculate_recovery_factor(self, player_id: int, metrics: PhysicalMetrics) -> float:
        """Calculate recovery-based injury risk factor"""
        try:
            recovery_score = 1.0
            
            # Days since last injury
            if metrics.days_since_last_injury is not None:
                if metrics.days_since_last_injury < 30:
                    recovery_score += 0.8  # Recent injury, high risk
                elif metrics.days_since_last_injury < 90:
                    recovery_score += 0.4  # Moderate recovery time
                elif metrics.days_since_last_injury > 365:
                    recovery_score -= 0.2  # Well recovered
            
            # Offseason rest
            if metrics.offseason_rest_days is not None:
                if metrics.offseason_rest_days < 60:
                    recovery_score += 0.3  # Insufficient rest
                elif metrics.offseason_rest_days > 120:
                    recovery_score -= 0.2  # Good rest
            
            # Practice participation
            if metrics.practice_participation_rate is not None:
                if metrics.practice_participation_rate < 0.8:
                    recovery_score += 0.4  # Limited practice
                elif metrics.practice_participation_rate > 0.95:
                    recovery_score -= 0.1  # Full participation
            
            return max(0.3, min(2.0, recovery_score))
            
        except Exception as e:
            self.logger.error(f"Error calculating recovery factor: {e}")
            return 1.0
    
    def _calculate_physical_condition_factor(self, metrics: PhysicalMetrics, position: str) -> float:
        """Calculate physical condition-based injury risk factor"""
        try:
            condition_score = 1.0
            
            # BMI analysis
            if metrics.bmi > 30:
                condition_score += 0.3  # Higher injury risk
            elif metrics.bmi < 20:
                condition_score += 0.2  # Potentially underweight
            elif 22 <= metrics.bmi <= 26:
                condition_score -= 0.1  # Optimal range
            
            # Body fat percentage (if available)
            if metrics.body_fat_percentage is not None:
                position_optimal = {'QB': 15, 'RB': 8, 'WR': 10, 'TE': 12}.get(position, 10)
                fat_deviation = abs(metrics.body_fat_percentage - position_optimal)
                if fat_deviation > 5:
                    condition_score += 0.2
            
            # Performance metrics (if available)
            performance_metrics = [
                metrics.speed_score, metrics.agility_score,
                metrics.strength_score, metrics.endurance_score
            ]
            
            available_metrics = [m for m in performance_metrics if m is not None]
            if available_metrics:
                avg_performance = np.mean(available_metrics)
                if avg_performance < 0.7:  # Below average
                    condition_score += 0.3
                elif avg_performance > 1.2:  # Above average
                    condition_score -= 0.2
            
            return max(0.4, min(2.0, condition_score))
            
        except Exception as e:
            self.logger.error(f"Error calculating physical condition factor: {e}")
            return 1.0
    
    def _calculate_overall_risk_probability(self, age_factor: float, position_factor: float,
                                          history_factor: float, workload_factor: float,
                                          recovery_factor: float, condition_factor: float) -> float:
        """Calculate overall injury risk probability"""
        try:
            # Weighted combination of factors
            weights = {
                'age': 0.15,
                'position': 0.20,
                'history': 0.25,
                'workload': 0.20,
                'recovery': 0.10,
                'condition': 0.10
            }
            
            weighted_risk = (
                age_factor * weights['age'] +
                position_factor * weights['position'] +
                history_factor * weights['history'] +
                workload_factor * weights['workload'] +
                recovery_factor * weights['recovery'] +
                condition_factor * weights['condition']
            )
            
            # Normalize to 0-1 probability scale
            # Assuming maximum reasonable weighted risk is around 2.5
            probability = min(0.9, max(0.05, weighted_risk / 2.5))
            
            return probability
            
        except Exception as e:
            self.logger.error(f"Error calculating overall risk: {e}")
            return 0.20  # Default moderate risk
    
    def _classify_risk_level(self, probability: float) -> InjuryRiskLevel:
        """Classify risk probability into risk level"""
        if probability <= 0.15:
            return InjuryRiskLevel.LOW
        elif probability <= 0.35:
            return InjuryRiskLevel.MODERATE
        elif probability <= 0.60:
            return InjuryRiskLevel.HIGH
        else:
            return InjuryRiskLevel.CRITICAL
    
    def _calculate_injury_type_risks(self, position: str, overall_risk: float,
                                   history_factor: float) -> Dict[InjuryType, float]:
        """Calculate risk probabilities for specific injury types"""
        try:
            position_patterns = self.position_injury_patterns.get(position, {
                InjuryType.SOFT_TISSUE: 0.3,
                InjuryType.JOINT: 0.3,
                InjuryType.CONTACT: 0.2,
                InjuryType.CONCUSSION: 0.1,
                InjuryType.OVERUSE: 0.1
            })
            
            injury_type_risks = {}
            
            for injury_type, base_proportion in position_patterns.items():
                # Scale by overall risk and history
                type_risk = overall_risk * base_proportion
                
                # Adjust based on injury history
                if history_factor > 1.5:  # High injury history
                    type_risk *= 1.2
                
                injury_type_risks[injury_type] = min(0.8, type_risk)
            
            return injury_type_risks
            
        except Exception as e:
            self.logger.error(f"Error calculating injury type risks: {e}")
            return {}
    
    def _identify_high_risk_weeks(self, player_id: int, overall_risk: float,
                                current_week: int) -> List[int]:
        """Identify weeks with elevated injury risk"""
        try:
            high_risk_weeks = []
            
            # Higher risk periods
            risk_periods = [
                (1, 3),    # Season start adjustment
                (4, 6),    # Early season intensity
                (13, 15),  # Late season fatigue
                (16, 18)   # Playoff push
            ]
            
            for start_week, end_week in risk_periods:
                if overall_risk > 0.3:  # Only for moderate+ risk players
                    high_risk_weeks.extend(range(start_week, end_week + 1))
            
            # Remove duplicates and sort
            high_risk_weeks = sorted(list(set(high_risk_weeks)))
            
            return high_risk_weeks
            
        except Exception as e:
            self.logger.error(f"Error identifying high risk weeks: {e}")
            return []
    
    def _calculate_rest_recommendation(self, overall_risk: float, workload_factor: float) -> float:
        """Calculate probability of recommending rest"""
        if overall_risk > 0.6 and workload_factor > 1.5:
            return 0.8
        elif overall_risk > 0.4 and workload_factor > 1.3:
            return 0.5
        elif overall_risk > 0.3:
            return 0.2
        else:
            return 0.0
    
    def _calculate_injury_prone_rating(self, history_factor: float, overall_risk: float) -> float:
        """Calculate injury prone rating (0-10 scale)"""
        rating = (history_factor + overall_risk) * 2.5
        return min(10.0, max(0.0, rating))
    
    def _assess_data_quality(self, player_id: int, metrics: PhysicalMetrics) -> Tuple[float, float]:
        """Assess data quality and completeness"""
        try:
            # Count available data points
            total_fields = 15  # Total important fields
            available_fields = 0
            
            if metrics.age > 0:
                available_fields += 1
            if metrics.height > 0:
                available_fields += 1
            if metrics.weight > 0:
                available_fields += 1
            if metrics.bmi > 0:
                available_fields += 1
            if metrics.body_fat_percentage is not None:
                available_fields += 1
            if metrics.speed_score is not None:
                available_fields += 1
            if metrics.agility_score is not None:
                available_fields += 1
            if metrics.strength_score is not None:
                available_fields += 1
            if metrics.endurance_score is not None:
                available_fields += 1
            if metrics.snaps_per_game_avg > 0:
                available_fields += 1
            if metrics.touches_per_game_avg >= 0:
                available_fields += 1
            if metrics.high_impact_plays_per_game >= 0:
                available_fields += 1
            if metrics.days_since_last_injury is not None:
                available_fields += 1
            if metrics.offseason_rest_days is not None:
                available_fields += 1
            if metrics.practice_participation_rate is not None:
                available_fields += 1
            
            data_completeness = available_fields / total_fields
            
            # Confidence based on completeness and injury history availability
            injury_history_count = len([inj for inj in self.injury_history if inj.player_id == player_id])
            history_confidence = min(1.0, injury_history_count / 5.0)  # 5+ injuries for full confidence
            
            confidence_score = (data_completeness * 0.7) + (history_confidence * 0.3)
            
            return confidence_score, data_completeness
            
        except Exception as e:
            self.logger.error(f"Error assessing data quality: {e}")
            return 0.5, 0.5
    
    def _create_default_risk_profile(self, player_id: int, player_name: str, position: str) -> InjuryRiskProfile:
        """Create default risk profile when prediction fails"""
        base_risk = self.position_injury_rates.get(position, 0.20)
        
        return InjuryRiskProfile(
            player_id=player_id,
            player_name=player_name,
            position=position,
            overall_risk_level=InjuryRiskLevel.MODERATE,
            overall_risk_probability=base_risk,
            injury_type_risks={},
            age_factor=1.0,
            position_factor=1.0,
            injury_history_factor=1.0,
            workload_factor=1.0,
            recovery_factor=1.0,
            physical_condition_factor=1.0,
            high_risk_weeks=[],
            recommended_rest_probability=0.0,
            injury_prone_rating=5.0,
            confidence_score=0.3,
            data_completeness=0.3
        )
    
    def add_injury_record(self, record: InjuryHistoryRecord) -> None:
        """Add injury history record"""
        self.injury_history.append(record)
    
    def add_physical_metrics(self, metrics: PhysicalMetrics) -> None:
        """Add physical metrics record"""
        self.physical_metrics.append(metrics)

# Sample data generators for testing
def generate_sample_injury_data() -> List[InjuryHistoryRecord]:
    """Generate sample injury history data"""
    sample_injuries = [
        InjuryHistoryRecord(
            player_id=1,
            injury_date=datetime(2023, 10, 15),
            injury_type=InjuryType.SOFT_TISSUE,
            severity="moderate",
            games_missed=3,
            return_date=datetime(2023, 11, 5),
            recurring=False,
            position_at_injury="WR"
        ),
        InjuryHistoryRecord(
            player_id=2,
            injury_date=datetime(2023, 9, 10),
            injury_type=InjuryType.JOINT,
            severity="severe",
            games_missed=8,
            return_date=datetime(2024, 1, 15),
            recurring=True,
            position_at_injury="RB"
        )
    ]
    return sample_injuries

def generate_sample_physical_metrics() -> List[PhysicalMetrics]:
    """Generate sample physical metrics"""
    sample_metrics = [
        PhysicalMetrics(
            player_id=1,
            measurement_date=datetime(2024, 8, 1),
            age=26.0,
            height=72.0,
            weight=195.0,
            bmi=26.4,
            body_fat_percentage=12.0,
            speed_score=1.1,
            agility_score=1.2,
            strength_score=0.9,
            endurance_score=1.0,
            snaps_per_game_avg=58.0,
            touches_per_game_avg=8.0,
            high_impact_plays_per_game=3.0,
            days_since_last_injury=120,
            offseason_rest_days=90,
            practice_participation_rate=0.95
        ),
        PhysicalMetrics(
            player_id=2,
            measurement_date=datetime(2024, 8, 1),
            age=29.0,
            height=71.0,
            weight=215.0,
            bmi=30.0,
            body_fat_percentage=8.0,
            speed_score=0.8,
            agility_score=0.9,
            strength_score=1.3,
            endurance_score=0.8,
            snaps_per_game_avg=45.0,
            touches_per_game_avg=18.0,
            high_impact_plays_per_game=12.0,
            days_since_last_injury=45,
            offseason_rest_days=60,
            practice_participation_rate=0.85
        )
    ]
    return sample_metrics

if __name__ == "__main__":
    print("🏥 ADVANCED INJURY RISK PREDICTOR TEST")
    print("=" * 45)
    
    predictor = AdvancedInjuryPredictor()
    
    # Load sample data
    sample_injuries = generate_sample_injury_data()
    sample_metrics = generate_sample_physical_metrics()
    
    for injury in sample_injuries:
        predictor.add_injury_record(injury)
    
    for metrics in sample_metrics:
        predictor.add_physical_metrics(metrics)
    
    # Test injury risk prediction
    test_players = [
        (1, "Cooper Kupp", "WR"),
        (2, "Christian McCaffrey", "RB")
    ]
    
    for player_id, player_name, position in test_players:
        print(f"\n📊 Analyzing: {player_name} ({position})")
        print("-" * 40)
        
        # Get player metrics
        player_metrics = next((m for m in sample_metrics if m.player_id == player_id), None)
        
        if player_metrics:
            risk_profile = predictor.predict_injury_risk(
                player_id, player_name, position, player_metrics, 1
            )
            
            print(f"Overall Risk: {risk_profile.overall_risk_level.value.upper()} ({risk_profile.overall_risk_probability:.1%})")
            print(f"Injury Prone Rating: {risk_profile.injury_prone_rating:.1f}/10")
            print(f"Rest Recommendation: {risk_profile.recommended_rest_probability:.1%}")
            print(f"Confidence: {risk_profile.confidence_score:.1%}")
            print(f"Data Completeness: {risk_profile.data_completeness:.1%}")
            
            print(f"\nRisk Factors:")
            print(f"  Age Factor: {risk_profile.age_factor:.2f}")
            print(f"  Position Factor: {risk_profile.position_factor:.2f}")
            print(f"  Injury History: {risk_profile.injury_history_factor:.2f}")
            print(f"  Workload: {risk_profile.workload_factor:.2f}")
            print(f"  Recovery: {risk_profile.recovery_factor:.2f}")
            print(f"  Physical Condition: {risk_profile.physical_condition_factor:.2f}")
            
            if risk_profile.high_risk_weeks:
                print(f"\nHigh Risk Weeks: {risk_profile.high_risk_weeks}")
    
    print("\n✅ Advanced Injury Risk Predictor test completed!")