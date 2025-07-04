"""
Salary Cap Impact Analysis for Player Value
Analyzes how salary cap constraints and contracts affect player performance and value
"""
from typing import Dict, List, Optional, Tuple, Any, Union
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from src.utils.type_hint_utility import PlayerId, Season, Week, TeamCode, Position, FantasyPoints
from src.utils.unified_database_operations import DatabaseSessionManager, CommonQueries
from src.database.models import Player, PlayerStats, TransactionLog


class ContractType(Enum):
    """Types of player contracts"""
    ROOKIE = "rookie"
    VETERAN_MINIMUM = "veteran_minimum"
    PROVE_IT = "prove_it"
    MARKET_VALUE = "market_value"
    OVERPAID = "overpaid"
    SUPERSTAR = "superstar"
    EXTENSION = "extension"
    FRANCHISE_TAG = "franchise_tag"


class ValueTier(Enum):
    """Player value tiers relative to cost"""
    ELITE_VALUE = "elite_value"      # Top performance, low cost
    GOOD_VALUE = "good_value"        # Good performance, reasonable cost
    FAIR_VALUE = "fair_value"        # Performance matches cost
    POOR_VALUE = "poor_value"        # Underperformance relative to cost
    TERRIBLE_VALUE = "terrible_value" # Significant underperformance


@dataclass
class ContractInfo:
    """Player contract information"""
    player_id: PlayerId
    total_value: float
    annual_average: float
    cap_hit_current: float
    guaranteed_money: float
    years_remaining: int
    contract_type: ContractType
    signing_year: int
    incentives: float
    is_team_friendly: bool


@dataclass
class SalaryCapProfile:
    """Team salary cap profile"""
    team_code: TeamCode
    season: Season
    total_cap_space: float
    used_cap_space: float
    available_cap_space: float
    top_earners: List[Dict[str, Any]]
    position_allocation: Dict[Position, float]
    cap_efficiency_score: float
    value_contracts: List[PlayerId]
    overpaid_contracts: List[PlayerId]


@dataclass
class PlayerValueAnalysis:
    """Comprehensive player value analysis"""
    player_id: PlayerId
    player_name: str
    position: Position
    team: TeamCode
    contract_info: ContractInfo
    performance_value: float  # Expected fantasy points per game
    cost_per_point: float     # Cap hit per fantasy point
    value_tier: ValueTier
    value_score: float        # 0-100 scale
    market_comparison: float  # vs. position average
    contract_motivation_factor: float  # Impact on performance
    team_cap_impact: float    # Impact on team's ability to build around player
    value_trend: float        # Improving/declining value
    breakout_probability: float  # Chance of exceeding expectations
    bust_risk: float          # Risk of significant underperformance


class SalaryCapAnalyzer:
    """Analyzes salary cap impact on player value and performance"""
    
    def __init__(self) -> None:
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.db_manager: DatabaseSessionManager = DatabaseSessionManager()
        self.queries: CommonQueries = CommonQueries()
        
        # Position value baselines (average AAV by position in millions)
        self.position_market_values: Dict[Position, float] = {
            'QB': 35.0,   # Top QBs command highest salaries
            'RB': 8.0,    # RB market has been depressed
            'WR': 20.0,   # Premium receivers well-paid
            'TE': 12.0,   # Elite TEs increasingly valuable
            'LT': 15.0,   # Premier pass protection
            'C': 12.0,    # Quality centers important
            'K': 4.0,     # Kickers standardized pricing
            'DEF': 10.0   # Defense varies widely
        }
        
        # Contract motivation factors
        self.contract_motivation: Dict[ContractType, float] = {
            ContractType.ROOKIE: 1.05,          # Hungry to prove themselves
            ContractType.VETERAN_MINIMUM: 1.10, # Playing for next contract
            ContractType.PROVE_IT: 1.15,        # High motivation to prove worth
            ContractType.MARKET_VALUE: 1.0,     # Standard motivation
            ContractType.OVERPAID: 0.95,        # Less pressure, potential complacency
            ContractType.SUPERSTAR: 0.98,       # Slight motivation decrease
            ContractType.EXTENSION: 1.02,       # Motivated by long-term security
            ContractType.FRANCHISE_TAG: 0.92    # Often unhappy with tag
        }
        
        # Salary cap per team (approximate for 2025)
        self.salary_cap_limit: float = 255_000_000  # $255M estimated for 2025
    
    def analyze_player_value(self, player_id: PlayerId, season: Season, week: Week) -> Optional[PlayerValueAnalysis]:
        """Comprehensive player value analysis"""
        try:
            # Get player info
            player = self._get_player_info(player_id)
            if not player:
                return None
            
            # Get contract information (would need contract database in production)
            contract_info = self._estimate_contract_info(player, season)
            
            # Calculate performance value
            performance_value = self._calculate_performance_value(player_id, season, week)
            
            # Calculate cost efficiency
            cost_per_point = self._calculate_cost_per_point(contract_info, performance_value)
            
            # Determine value tier
            value_tier = self._determine_value_tier(cost_per_point, player.position)
            
            # Calculate comprehensive value score
            value_score = self._calculate_value_score(
                performance_value, cost_per_point, player.position, contract_info
            )
            
            # Market comparison
            market_comparison = self._compare_to_market(contract_info, player.position)
            
            # Contract motivation factor
            motivation_factor = self.contract_motivation.get(contract_info.contract_type, 1.0)
            
            # Team cap impact
            team_cap_impact = self._calculate_team_cap_impact(player.team, contract_info, season)
            
            # Value trend analysis
            value_trend = self._calculate_value_trend(player_id, season)
            
            # Breakout and bust probabilities
            breakout_prob, bust_risk = self._calculate_outcome_probabilities(
                player, contract_info, performance_value
            )
            
            return PlayerValueAnalysis(
                player_id=player_id,
                player_name=player.name,
                position=player.position,
                team=player.team,
                contract_info=contract_info,
                performance_value=performance_value,
                cost_per_point=cost_per_point,
                value_tier=value_tier,
                value_score=value_score,
                market_comparison=market_comparison,
                contract_motivation_factor=motivation_factor,
                team_cap_impact=team_cap_impact,
                value_trend=value_trend,
                breakout_probability=breakout_prob,
                bust_risk=bust_risk
            )
            
        except Exception as e:
            self.logger.error(f"Error analyzing player value for {player_id}: {e}")
            return None
    
    def analyze_team_cap_efficiency(self, team_code: TeamCode, season: Season) -> SalaryCapProfile:
        """Analyze team's salary cap allocation efficiency"""
        try:
            # Get team players
            team_players = self.db_manager.safe_find_team_players(team_code)
            
            # Calculate team cap usage (estimated)
            total_cap_used = 0.0
            top_earners: List[Dict[str, Any]] = []
            position_allocation: Dict[Position, float] = {}
            value_contracts: List[PlayerId] = []
            overpaid_contracts: List[PlayerId] = []
            
            for player in team_players:
                contract_info = self._estimate_contract_info(player, season)
                performance_value = self._calculate_performance_value(player.id, season, 1)
                
                total_cap_used += contract_info.cap_hit_current
                
                # Track top earners
                top_earners.append({
                    'player_id': player.id,
                    'player_name': player.name,
                    'position': player.position,
                    'cap_hit': contract_info.cap_hit_current,
                    'performance_value': performance_value
                })
                
                # Position allocation
                if player.position not in position_allocation:
                    position_allocation[player.position] = 0
                position_allocation[player.position] += contract_info.cap_hit_current
                
                # Value classification
                cost_per_point = self._calculate_cost_per_point(contract_info, performance_value)
                value_tier = self._determine_value_tier(cost_per_point, player.position)
                
                if value_tier in [ValueTier.ELITE_VALUE, ValueTier.GOOD_VALUE]:
                    value_contracts.append(player.id)
                elif value_tier in [ValueTier.POOR_VALUE, ValueTier.TERRIBLE_VALUE]:
                    overpaid_contracts.append(player.id)
            
            # Sort top earners
            top_earners.sort(key=lambda x: x['cap_hit'], reverse=True)
            
            # Calculate cap efficiency
            cap_efficiency = self._calculate_cap_efficiency(top_earners, total_cap_used)
            
            available_cap = self.salary_cap_limit - total_cap_used
            
            return SalaryCapProfile(
                team_code=team_code,
                season=season,
                total_cap_space=self.salary_cap_limit,
                used_cap_space=total_cap_used,
                available_cap_space=available_cap,
                top_earners=top_earners[:10],  # Top 10 earners
                position_allocation=position_allocation,
                cap_efficiency_score=cap_efficiency,
                value_contracts=value_contracts,
                overpaid_contracts=overpaid_contracts
            )
            
        except Exception as e:
            self.logger.error(f"Error analyzing team cap efficiency for {team_code}: {e}")
            return self._create_default_cap_profile(team_code, season)
    
    def identify_value_opportunities(self, season: Season, position: Optional[Position] = None) -> List[Dict[str, Any]]:
        """Identify players offering exceptional value"""
        try:
            opportunities: List[Dict[str, Any]] = []
            
            # Get all players for analysis
            if position:
                players = self.queries.get_position_players(position)
            else:
                # For demo, limit to specific teams to avoid overwhelming results
                demo_teams = ['KC', 'BUF', 'LAR', 'TB', 'SF']
                players = []
                for team in demo_teams:
                    team_players = self.db_manager.safe_find_team_players(team)
                    players.extend(team_players)
            
            for player in players[:50]:  # Limit for performance
                value_analysis = self.analyze_player_value(player.id, season, 1)
                if not value_analysis:
                    continue
                
                # Identify high-value opportunities
                if (value_analysis.value_tier in [ValueTier.ELITE_VALUE, ValueTier.GOOD_VALUE] and
                    value_analysis.value_score > 70):
                    
                    opportunities.append({
                        'player_id': player.id,
                        'player_name': player.name,
                        'position': player.position,
                        'team': player.team,
                        'value_score': value_analysis.value_score,
                        'value_tier': value_analysis.value_tier.value,
                        'cost_per_point': value_analysis.cost_per_point,
                        'breakout_probability': value_analysis.breakout_probability,
                        'contract_type': value_analysis.contract_info.contract_type.value,
                        'motivation_factor': value_analysis.contract_motivation_factor
                    })
            
            # Sort by value score
            opportunities.sort(key=lambda x: x['value_score'], reverse=True)
            
            return opportunities[:20]  # Top 20 opportunities
            
        except Exception as e:
            self.logger.error(f"Error identifying value opportunities: {e}")
            return []
    
    def calculate_contract_performance_impact(self, player_id: PlayerId, season: Season) -> Dict[str, float]:
        """Calculate how contract situation impacts performance predictions"""
        try:
            player = self._get_player_info(player_id)
            if not player:
                return self._get_default_contract_impact()
            
            contract_info = self._estimate_contract_info(player, season)
            
            # Contract motivation impact
            motivation_multiplier = self.contract_motivation.get(contract_info.contract_type, 1.0)
            
            # Pressure factor (high-paid players face more pressure)
            pressure_factor = self._calculate_pressure_factor(contract_info, player.position)
            
            # Security factor (guaranteed money provides security)
            security_factor = self._calculate_security_factor(contract_info)
            
            # Team expectation factor
            expectation_factor = self._calculate_expectation_factor(contract_info, player.team)
            
            # Overall contract impact
            performance_impact = (
                motivation_multiplier * 0.3 +
                pressure_factor * 0.25 +
                security_factor * 0.25 +
                expectation_factor * 0.2
            )
            
            # Confidence adjustment based on contract clarity
            confidence_adjustment = self._calculate_confidence_adjustment(contract_info)
            
            return {
                'performance_multiplier': performance_impact,
                'motivation_factor': motivation_multiplier,
                'pressure_factor': pressure_factor,
                'security_factor': security_factor,
                'expectation_factor': expectation_factor,
                'confidence_adjustment': confidence_adjustment,
                'overall_impact': (performance_impact - 1.0) * 100  # Percentage impact
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating contract impact for {player_id}: {e}")
            return self._get_default_contract_impact()
    
    # Helper methods
    def _get_player_info(self, player_id: PlayerId) -> Optional[Player]:
        """Get player information"""
        try:
            def get_player(session):
                return session.query(Player).filter(Player.id == player_id).first()
            
            return self.db_manager.execute_readonly(get_player)
        except Exception:
            return None
    
    def _estimate_contract_info(self, player: Player, season: Season) -> ContractInfo:
        """Estimate contract information (would use real contract database in production)"""
        # This would typically pull from a contracts database
        # For demo purposes, we'll estimate based on position and experience
        
        experience = player.experience_years or 1
        position_value = self.position_market_values.get(player.position, 5.0)
        
        # Estimate contract based on experience and position
        if experience <= 4:  # Rookie contract
            annual_value = min(position_value * 0.2, 10.0)  # Rookie scale
            contract_type = ContractType.ROOKIE
            guaranteed = annual_value * 0.8
        elif experience <= 6:  # Second contract
            annual_value = position_value * 0.6
            contract_type = ContractType.MARKET_VALUE
            guaranteed = annual_value * 0.5
        else:  # Veteran
            # Estimate based on performance tier
            recent_stats = self.queries.get_recent_player_stats(player.id, limit=3)
            if recent_stats:
                avg_fp = np.mean([getattr(stat, 'fantasy_points', 0) for stat in recent_stats])
                if avg_fp > 15:  # High performer
                    annual_value = position_value * 1.2
                    contract_type = ContractType.SUPERSTAR
                elif avg_fp > 10:
                    annual_value = position_value
                    contract_type = ContractType.MARKET_VALUE
                else:
                    annual_value = position_value * 0.5
                    contract_type = ContractType.PROVE_IT
            else:
                annual_value = position_value * 0.7
                contract_type = ContractType.MARKET_VALUE
            
            guaranteed = annual_value * 0.4
        
        # Add some randomness for realism
        annual_value *= (0.8 + np.random.random() * 0.4)
        
        return ContractInfo(
            player_id=player.id,
            total_value=annual_value * 4,  # 4-year deal
            annual_average=annual_value,
            cap_hit_current=annual_value * 1.1,  # Slightly higher cap hit
            guaranteed_money=guaranteed,
            years_remaining=max(1, 4 - (season - 2022)),
            contract_type=contract_type,
            signing_year=max(2020, season - 2),
            incentives=annual_value * 0.1,
            is_team_friendly=annual_value < position_value * 0.8
        )
    
    def _calculate_performance_value(self, player_id: PlayerId, season: Season, week: Week) -> float:
        """Calculate expected performance value (fantasy points per game)"""
        try:
            recent_stats = self.queries.get_recent_player_stats(player_id, limit=8)
            if not recent_stats:
                return 8.0  # Default moderate value
            
            fantasy_points = [getattr(stat, 'fantasy_points', 0) for stat in recent_stats]
            avg_fantasy_points = np.mean(fantasy_points)
            
            return max(avg_fantasy_points, 0.0)
            
        except Exception:
            return 8.0
    
    def _calculate_cost_per_point(self, contract_info: ContractInfo, performance_value: float) -> float:
        """Calculate cost per fantasy point"""
        if performance_value <= 0:
            return float('inf')
        
        # Convert to per-game basis (17 games)
        annual_cost = contract_info.cap_hit_current
        cost_per_game = annual_cost / 17
        cost_per_point = cost_per_game / performance_value if performance_value > 0 else float('inf')
        
        return cost_per_point
    
    def _determine_value_tier(self, cost_per_point: float, position: Position) -> ValueTier:
        """Determine player's value tier"""
        # Position-specific value thresholds (cost per fantasy point in thousands)
        thresholds = {
            'QB': {'elite': 50, 'good': 100, 'fair': 200, 'poor': 300},
            'RB': {'elite': 30, 'good': 60, 'fair': 120, 'poor': 180},
            'WR': {'elite': 40, 'good': 80, 'fair': 160, 'poor': 240},
            'TE': {'elite': 35, 'good': 70, 'fair': 140, 'poor': 210}
        }
        
        pos_thresholds = thresholds.get(position, thresholds['RB'])  # Default to RB
        
        cost_k = cost_per_point / 1000  # Convert to thousands
        
        if cost_k <= pos_thresholds['elite']:
            return ValueTier.ELITE_VALUE
        elif cost_k <= pos_thresholds['good']:
            return ValueTier.GOOD_VALUE
        elif cost_k <= pos_thresholds['fair']:
            return ValueTier.FAIR_VALUE
        elif cost_k <= pos_thresholds['poor']:
            return ValueTier.POOR_VALUE
        else:
            return ValueTier.TERRIBLE_VALUE
    
    def _calculate_value_score(self, performance_value: float, cost_per_point: float, 
                             position: Position, contract_info: ContractInfo) -> float:
        """Calculate comprehensive value score (0-100)"""
        # Base score from cost efficiency
        if cost_per_point == float('inf'):
            efficiency_score = 0
        else:
            # Lower cost per point = higher score
            position_avg_cost = self.position_market_values.get(position, 10.0) * 1000 / 17 / 10  # Rough estimate
            efficiency_ratio = position_avg_cost / max(cost_per_point, 1)
            efficiency_score = min(efficiency_ratio * 50, 70)  # Cap at 70
        
        # Performance bonus
        performance_bonus = min(performance_value * 2, 20)  # Up to 20 points
        
        # Contract situation bonus/penalty
        if contract_info.contract_type in [ContractType.ROOKIE, ContractType.PROVE_IT]:
            contract_bonus = 10  # High motivation
        elif contract_info.contract_type == ContractType.OVERPAID:
            contract_bonus = -10  # Overpaid penalty
        else:
            contract_bonus = 0
        
        total_score = efficiency_score + performance_bonus + contract_bonus
        return min(max(total_score, 0), 100)
    
    def _compare_to_market(self, contract_info: ContractInfo, position: Position) -> float:
        """Compare contract to market value"""
        market_value = self.position_market_values.get(position, 10.0)
        return contract_info.annual_average / market_value
    
    def _calculate_team_cap_impact(self, team_code: TeamCode, contract_info: ContractInfo, season: Season) -> float:
        """Calculate impact on team's cap flexibility"""
        # Percentage of team cap used by this player
        cap_percentage = contract_info.cap_hit_current / self.salary_cap_limit
        
        # High cap hit reduces team flexibility
        if cap_percentage > 0.15:  # 15%+ of cap
            return -0.2  # Negative impact
        elif cap_percentage > 0.10:  # 10-15% of cap
            return -0.1
        else:
            return 0.0  # Minimal impact
    
    def _calculate_value_trend(self, player_id: PlayerId, season: Season) -> float:
        """Calculate value trend (improving/declining)"""
        try:
            recent_stats = self.queries.get_recent_player_stats(player_id, limit=6)
            if len(recent_stats) < 4:
                return 0.0
            
            fantasy_points = [getattr(stat, 'fantasy_points', 0) for stat in recent_stats]
            
            # Calculate trend
            weeks = list(range(len(fantasy_points)))
            correlation = np.corrcoef(weeks, fantasy_points)[0, 1]
            
            return correlation if not np.isnan(correlation) else 0.0
            
        except Exception:
            return 0.0
    
    def _calculate_outcome_probabilities(self, player: Player, contract_info: ContractInfo, 
                                       performance_value: float) -> Tuple[float, float]:
        """Calculate breakout and bust probabilities"""
        # Base probabilities
        breakout_prob = 0.15  # 15% base breakout chance
        bust_risk = 0.20      # 20% base bust risk
        
        # Contract motivation adjustments
        if contract_info.contract_type in [ContractType.PROVE_IT, ContractType.ROOKIE]:
            breakout_prob += 0.10  # Higher breakout chance
            bust_risk -= 0.05      # Lower bust risk
        elif contract_info.contract_type == ContractType.OVERPAID:
            breakout_prob -= 0.05  # Lower breakout chance
            bust_risk += 0.10      # Higher bust risk
        
        # Age adjustments
        if player.age:
            if player.age < 25:
                breakout_prob += 0.05  # Young players more likely to break out
            elif player.age > 30:
                breakout_prob -= 0.05  # Older players less likely
                bust_risk += 0.05      # Higher injury/decline risk
        
        # Performance level adjustments
        if performance_value > 15:  # Already high performer
            breakout_prob -= 0.05  # Less room to break out
        elif performance_value < 8:
            bust_risk += 0.10      # Already struggling
        
        return min(max(breakout_prob, 0.05), 0.40), min(max(bust_risk, 0.05), 0.50)
    
    def _calculate_cap_efficiency(self, top_earners: List[Dict[str, Any]], total_cap_used: float) -> float:
        """Calculate team's cap efficiency score"""
        if not top_earners:
            return 0.5
        
        # Calculate value received for cap dollars spent
        total_performance = sum(earner.get('performance_value', 0) for earner in top_earners)
        total_cost = sum(earner.get('cap_hit', 0) for earner in top_earners)
        
        if total_cost == 0:
            return 0.5
        
        # Efficiency metric (performance per million spent)
        efficiency = total_performance / (total_cost / 1_000_000)
        
        # Normalize to 0-1 scale (10+ is excellent efficiency)
        normalized_efficiency = min(efficiency / 10, 1.0)
        
        return normalized_efficiency
    
    def _calculate_pressure_factor(self, contract_info: ContractInfo, position: Position) -> float:
        """Calculate pressure factor from contract size"""
        market_value = self.position_market_values.get(position, 10.0)
        
        if contract_info.annual_average > market_value * 1.5:
            return 0.95  # High pressure, slight performance decrease
        elif contract_info.annual_average > market_value:
            return 0.98  # Moderate pressure
        else:
            return 1.02  # Low pressure, slight boost
    
    def _calculate_security_factor(self, contract_info: ContractInfo) -> float:
        """Calculate security factor from guaranteed money"""
        guarantee_ratio = contract_info.guaranteed_money / contract_info.total_value
        
        if guarantee_ratio > 0.6:
            return 1.01  # High security, slight boost
        elif guarantee_ratio > 0.3:
            return 1.0   # Moderate security
        else:
            return 0.99  # Low security, slight decrease
    
    def _calculate_expectation_factor(self, contract_info: ContractInfo, team_code: TeamCode) -> float:
        """Calculate expectation factor based on team and contract"""
        # High-paid players on good teams face higher expectations
        # This would typically consider team success, market size, etc.
        return 1.0  # Simplified for demo
    
    def _calculate_confidence_adjustment(self, contract_info: ContractInfo) -> float:
        """Calculate confidence adjustment based on contract certainty"""
        if contract_info.years_remaining >= 3:
            return 0.05  # More predictable with long-term deal
        elif contract_info.years_remaining == 1:
            return -0.05  # Less predictable in contract year
        else:
            return 0.0
    
    def _get_default_contract_impact(self) -> Dict[str, float]:
        """Default contract impact values"""
        return {
            'performance_multiplier': 1.0,
            'motivation_factor': 1.0,
            'pressure_factor': 1.0,
            'security_factor': 1.0,
            'expectation_factor': 1.0,
            'confidence_adjustment': 0.0,
            'overall_impact': 0.0
        }
    
    def _create_default_cap_profile(self, team_code: TeamCode, season: Season) -> SalaryCapProfile:
        """Create default cap profile when analysis fails"""
        return SalaryCapProfile(
            team_code=team_code,
            season=season,
            total_cap_space=self.salary_cap_limit,
            used_cap_space=self.salary_cap_limit * 0.9,  # Assume 90% used
            available_cap_space=self.salary_cap_limit * 0.1,
            top_earners=[],
            position_allocation={},
            cap_efficiency_score=0.5,
            value_contracts=[],
            overpaid_contracts=[]
        )


# Convenience functions
def analyze_player_contract_value(player_id: PlayerId, season: Season, week: Week) -> Optional[PlayerValueAnalysis]:
    """Analyze player's contract value"""
    analyzer = SalaryCapAnalyzer()
    return analyzer.analyze_player_value(player_id, season, week)


def get_team_cap_efficiency(team_code: TeamCode, season: Season) -> SalaryCapProfile:
    """Get team's cap efficiency analysis"""
    analyzer = SalaryCapAnalyzer()
    return analyzer.analyze_team_cap_efficiency(team_code, season)


def find_value_opportunities(season: Season, position: Optional[Position] = None) -> List[Dict[str, Any]]:
    """Find players offering exceptional value"""
    analyzer = SalaryCapAnalyzer()
    return analyzer.identify_value_opportunities(season, position)


__all__ = [
    'SalaryCapAnalyzer', 'PlayerValueAnalysis', 'SalaryCapProfile', 
    'ContractInfo', 'ContractType', 'ValueTier',
    'analyze_player_contract_value', 'get_team_cap_efficiency', 'find_value_opportunities'
]