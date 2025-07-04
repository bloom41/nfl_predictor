#!/usr/bin/env python3
"""
Position-Based Rankings System
Organizes player predictions by position (QB, RB, WR, TE) for easy comparison
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from src.models.comprehensive_prediction_system import ComprehensivePredictionSystem
from src.utils.unified_database_operations import DatabaseSessionManager
from src.database.models import Player
from src.utils.type_hint_utility import PlayerId, Season, Week, Position

logger = logging.getLogger(__name__)

class RankingType(Enum):
    """Types of rankings available"""
    FANTASY_POINTS = "fantasy_points"
    CONFIDENCE = "confidence"
    UPSIDE = "upside"
    CONSISTENCY = "consistency"

@dataclass
class PlayerRanking:
    """Player ranking with all relevant stats"""
    rank: int
    player_id: PlayerId
    player_name: str
    team: str
    position: Position
    fantasy_points: float
    confidence: float
    passing_yards: Optional[int] = None
    passing_tds: Optional[float] = None
    rushing_yards: Optional[int] = None
    rushing_tds: Optional[float] = None
    receiving_yards: Optional[int] = None
    receiving_tds: Optional[float] = None
    targets: Optional[int] = None

@dataclass
class PositionRankings:
    """Rankings for a specific position"""
    position: Position
    week: Week
    rankings: List[PlayerRanking]
    total_players: int
    avg_fantasy_points: float

class PositionRankingSystem:
    """Generate position-based player rankings"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.db_manager = DatabaseSessionManager()
        
        # Initialize prediction systems for each position
        self.prediction_systems = {
            'QB': ComprehensivePredictionSystem('QB'),
            'RB': ComprehensivePredictionSystem('RB'), 
            'WR': ComprehensivePredictionSystem('WR'),
            'TE': ComprehensivePredictionSystem('TE')
        }
    
    def get_all_position_rankings(self, season: Season, week: Week, 
                                top_n: int = 10) -> Dict[Position, PositionRankings]:
        """Get rankings for all positions"""
        self.logger.info(f"Generating position rankings for {season} Week {week}")
        
        position_rankings = {}
        
        for position in ['QB', 'RB', 'WR', 'TE']:
            try:
                rankings = self.get_position_rankings(position, season, week, top_n)
                position_rankings[position] = rankings
                self.logger.info(f"Generated {position} rankings: {len(rankings.rankings)} players")
            except Exception as e:
                self.logger.error(f"Error generating {position} rankings: {e}")
                # Create empty rankings for failed positions
                position_rankings[position] = PositionRankings(
                    position=position,
                    week=week,
                    rankings=[],
                    total_players=0,
                    avg_fantasy_points=0.0
                )
        
        return position_rankings
    
    def get_position_rankings(self, position: Position, season: Season, 
                            week: Week, top_n: int = 10) -> PositionRankings:
        """Get rankings for a specific position"""
        try:
            # Get all players for this position
            def get_position_players(session):
                players = session.query(Player).filter(
                    Player.position == position
                ).limit(50).all()
                # Extract data and detach from session
                player_data = []
                for player in players:
                    player_data.append({
                        'id': player.id,
                        'name': player.name,
                        'team': player.team,
                        'position': player.position
                    })
                    session.expunge(player)
                return player_data
            
            player_data = self.db_manager.execute_readonly(get_position_players)
            
            if not player_data:
                self.logger.warning(f"No {position} players found in database")
                return PositionRankings(position, week, [], 0, 0.0)
            
            # Generate predictions for each player
            player_predictions = []
            prediction_system = self.prediction_systems[position]
            
            for player_info in player_data:
                try:
                    # Extract player data
                    player_id = player_info['id']
                    player_name = player_info['name']
                    team = player_info['team']
                    
                    # Generate comprehensive prediction
                    prediction = prediction_system.predict_comprehensive(player_id, season, week)
                    
                    if prediction and prediction.final_prediction:
                        fantasy_points = prediction.final_prediction.get('target_fantasy_points', 0)
                        
                        # Create player ranking
                        player_ranking = PlayerRanking(
                            rank=0,  # Will be set later
                            player_id=player_id,
                            player_name=player_name,
                            team=team,
                            position=position,
                            fantasy_points=fantasy_points,
                            confidence=prediction.overall_confidence,
                            passing_yards=prediction.final_prediction.get('target_passing_yards'),
                            passing_tds=prediction.final_prediction.get('target_passing_tds'),
                            rushing_yards=prediction.final_prediction.get('target_rushing_yards'),
                            rushing_tds=prediction.final_prediction.get('target_rushing_tds'),
                            receiving_yards=prediction.final_prediction.get('target_receiving_yards'),
                            receiving_tds=prediction.final_prediction.get('target_receiving_tds'),
                            targets=prediction.final_prediction.get('target_targets')
                        )
                        
                        player_predictions.append(player_ranking)
                        
                except Exception as e:
                    self.logger.warning(f"Could not generate prediction for {player_name}: {e}")
                    continue
            
            # Sort by fantasy points (descending)
            player_predictions.sort(key=lambda x: x.fantasy_points, reverse=True)
            
            # Assign ranks and limit to top N
            top_predictions = player_predictions[:top_n]
            for i, prediction in enumerate(top_predictions, 1):
                prediction.rank = i
            
            # Calculate average
            avg_fantasy_points = (
                sum(p.fantasy_points for p in player_predictions) / len(player_predictions)
                if player_predictions else 0.0
            )
            
            return PositionRankings(
                position=position,
                week=week,
                rankings=top_predictions,
                total_players=len(player_predictions),
                avg_fantasy_points=avg_fantasy_points
            )
            
        except Exception as e:
            self.logger.error(f"Error generating {position} rankings: {e}")
            return PositionRankings(position, week, [], 0, 0.0)
    
    def format_position_rankings(self, rankings: PositionRankings, 
                               detailed: bool = True) -> str:
        """Format position rankings as readable text"""
        if not rankings.rankings:
            return f"❌ No {rankings.position} rankings available for Week {rankings.week}"
        
        lines = []
        lines.append(f"🏈 TOP {rankings.position} RANKINGS - WEEK {rankings.week}")
        lines.append("=" * (len(lines[0]) - 2))
        lines.append("")
        
        for player in rankings.rankings:
            # Basic info
            line = f"{player.rank:2}. {player.player_name} ({player.team}): {player.fantasy_points:.1f} pts"
            
            if detailed:
                # Add position-specific stats
                if rankings.position == 'QB':
                    if player.passing_yards and player.passing_tds:
                        line += f" ({player.passing_yards} pass yds, {player.passing_tds:.1f} pass TDs"
                        if player.rushing_yards:
                            line += f", {player.rushing_yards} rush yds"
                        line += ")"
                elif rankings.position == 'RB':
                    if player.rushing_yards and player.rushing_tds:
                        line += f" ({player.rushing_yards} rush yds, {player.rushing_tds:.1f} rush TDs"
                        if player.receiving_yards:
                            line += f", {player.receiving_yards} rec yds"
                        line += ")"
                elif rankings.position in ['WR', 'TE']:
                    if player.receiving_yards and player.receiving_tds:
                        line += f" ({player.receiving_yards} rec yds, {player.receiving_tds:.1f} rec TDs"
                        if player.targets:
                            line += f", {player.targets} targets"
                        line += ")"
            
            # Add confidence
            line += f" [Confidence: {player.confidence:.2f}]"
            lines.append(line)
        
        lines.append("")
        lines.append(f"📊 Position Average: {rankings.avg_fantasy_points:.1f} pts")
        lines.append(f"📈 Total {rankings.position} Players Analyzed: {rankings.total_players}")
        
        return "\n".join(lines)
    
    def format_all_positions(self, all_rankings: Dict[Position, PositionRankings],
                           top_n: int = 5) -> str:
        """Format rankings for all positions in one display"""
        lines = []
        lines.append("🏆 NFL FANTASY RANKINGS BY POSITION")
        lines.append("=" * 50)
        lines.append("")
        
        position_order = ['QB', 'RB', 'WR', 'TE']
        
        for position in position_order:
            if position in all_rankings:
                rankings = all_rankings[position]
                
                lines.append(f"🏈 {position} TOP {min(top_n, len(rankings.rankings))}")
                lines.append("-" * 20)
                
                for i, player in enumerate(rankings.rankings[:top_n], 1):
                    lines.append(f"{i}. {player.player_name} ({player.team}) - {player.fantasy_points:.1f} pts")
                
                lines.append("")
        
        return "\n".join(lines)

# Convenience functions
def get_week_rankings(season: Season = 2024, week: Week = 1, top_n: int = 10) -> str:
    """Get formatted rankings for all positions for a specific week"""
    ranking_system = PositionRankingSystem()
    all_rankings = ranking_system.get_all_position_rankings(season, week, top_n)
    return ranking_system.format_all_positions(all_rankings, top_n)

def get_position_ranking(position: Position, season: Season = 2024, 
                        week: Week = 1, top_n: int = 10) -> str:
    """Get detailed rankings for a specific position"""
    ranking_system = PositionRankingSystem()
    rankings = ranking_system.get_position_rankings(position, season, week, top_n)
    return ranking_system.format_position_rankings(rankings, detailed=True)

if __name__ == "__main__":
    # Test the ranking system
    print("🏈 Testing Position Ranking System...")
    print()
    
    # Test all positions
    try:
        all_rankings = get_week_rankings(2024, 1, 5)
        print(all_rankings)
    except Exception as e:
        print(f"❌ Error testing rankings: {e}")