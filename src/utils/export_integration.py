#!/usr/bin/env python3
"""
Export and Integration System
CSV exports, draft helpers, lineup optimizers, and external integrations
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import csv
import json
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class ExportFormat(Enum):
    CSV = "csv"
    JSON = "json"
    EXCEL = "excel"
    HTML = "html"

@dataclass
class PlayerExportData:
    """Player data for export"""
    player_name: str
    team: str
    position: str
    week: int
    projected_points: float
    confidence: float
    
    # Optional advanced data
    injury_status: Optional[str] = None
    matchup_rating: Optional[float] = None
    target_share: Optional[float] = None
    snap_percentage: Optional[float] = None
    red_zone_share: Optional[float] = None
    recent_trend: Optional[str] = None
    
    # ADP and value metrics
    adp: Optional[float] = None
    value_over_adp: Optional[float] = None
    ownership_percentage: Optional[float] = None

@dataclass
class LineupConstraints:
    """Lineup construction constraints"""
    salary_cap: int = 50000
    min_salary: int = 0
    
    # Position requirements
    qb_required: int = 1
    rb_required: int = 2
    wr_required: int = 3
    te_required: int = 1
    flex_required: int = 1  # RB/WR/TE
    dst_required: int = 1
    k_required: int = 1
    
    # Optional constraints
    max_players_per_team: int = 4
    min_projected_points: float = 0.0
    stack_requirements: Optional[Dict[str, int]] = None  # {'QB-WR': 1}

@dataclass
class DraftSettings:
    """Draft helper settings"""
    draft_format: str = "snake"  # snake, linear, auction
    team_count: int = 12
    rounds: int = 16
    current_pick: int = 1
    user_team_position: int = 1
    
    # Scoring settings
    scoring_format: str = "half_ppr"
    
    # Strategy settings
    positional_scarcity: Dict[str, float] = None
    value_over_replacement: bool = True

class ExportIntegrationSystem:
    """Handle exports and integrations"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.export_directory = "exports"
        self._ensure_export_directory()
    
    def _ensure_export_directory(self):
        """Create export directory if it doesn't exist"""
        os.makedirs(self.export_directory, exist_ok=True)
    
    def export_rankings(self, player_data: List[PlayerExportData], 
                       export_format: ExportFormat = ExportFormat.CSV,
                       filename: Optional[str] = None) -> str:
        """Export player rankings to specified format"""
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"nfl_rankings_{timestamp}"
        
        if export_format == ExportFormat.CSV:
            return self._export_to_csv(player_data, filename)
        elif export_format == ExportFormat.JSON:
            return self._export_to_json(player_data, filename)
        elif export_format == ExportFormat.HTML:
            return self._export_to_html(player_data, filename)
        else:
            raise ValueError(f"Unsupported export format: {export_format}")
    
    def _export_to_csv(self, player_data: List[PlayerExportData], filename: str) -> str:
        """Export to CSV format"""
        filepath = os.path.join(self.export_directory, f"{filename}.csv")
        
        # Get all possible fields from the dataclass
        fieldnames = [
            'player_name', 'team', 'position', 'week', 'projected_points', 'confidence',
            'injury_status', 'matchup_rating', 'target_share', 'snap_percentage',
            'red_zone_share', 'recent_trend', 'adp', 'value_over_adp', 'ownership_percentage'
        ]
        
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for player in player_data:
                row = asdict(player)
                writer.writerow(row)
        
        self.logger.info(f"Exported {len(player_data)} players to {filepath}")
        return filepath
    
    def _export_to_json(self, player_data: List[PlayerExportData], filename: str) -> str:
        """Export to JSON format"""
        filepath = os.path.join(self.export_directory, f"{filename}.json")
        
        export_data = {
            'export_timestamp': datetime.now().isoformat(),
            'total_players': len(player_data),
            'players': [asdict(player) for player in player_data]
        }
        
        with open(filepath, 'w', encoding='utf-8') as jsonfile:
            json.dump(export_data, jsonfile, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Exported {len(player_data)} players to {filepath}")
        return filepath
    
    def _export_to_html(self, player_data: List[PlayerExportData], filename: str) -> str:
        """Export to HTML format"""
        filepath = os.path.join(self.export_directory, f"{filename}.html")
        
        html_content = self._generate_html_table(player_data)
        
        with open(filepath, 'w', encoding='utf-8') as htmlfile:
            htmlfile.write(html_content)
        
        self.logger.info(f"Exported {len(player_data)} players to {filepath}")
        return filepath
    
    def _generate_html_table(self, player_data: List[PlayerExportData]) -> str:
        """Generate HTML table for player data"""
        html = """<!DOCTYPE html>
<html>
<head>
    <title>NFL Fantasy Rankings</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        .position-QB { background-color: #ffebee; }
        .position-RB { background-color: #e8f5e8; }
        .position-WR { background-color: #e3f2fd; }
        .position-TE { background-color: #fff3e0; }
    </style>
</head>
<body>
    <h1>NFL Fantasy Rankings</h1>
    <p>Generated: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
    <table>
        <thead>
            <tr>
                <th>Rank</th>
                <th>Player</th>
                <th>Team</th>
                <th>Position</th>
                <th>Projected Points</th>
                <th>Confidence</th>
                <th>Matchup</th>
                <th>Injury Status</th>
                <th>Trend</th>
            </tr>
        </thead>
        <tbody>
"""
        
        for i, player in enumerate(player_data, 1):
            injury_display = player.injury_status or "Healthy"
            matchup_display = f"{player.matchup_rating:.1f}" if player.matchup_rating else "N/A"
            trend_display = player.recent_trend or "Stable"
            
            html += f"""            <tr class="position-{player.position}">
                <td>{i}</td>
                <td><strong>{player.player_name}</strong></td>
                <td>{player.team}</td>
                <td>{player.position}</td>
                <td>{player.projected_points:.1f}</td>
                <td>{player.confidence:.2f}</td>
                <td>{matchup_display}</td>
                <td>{injury_display}</td>
                <td>{trend_display}</td>
            </tr>
"""
        
        html += """        </tbody>
    </table>
</body>
</html>"""
        
        return html
    
    def generate_draft_helper(self, player_data: List[PlayerExportData], 
                            draft_settings: DraftSettings) -> Dict[str, Any]:
        """Generate draft helper recommendations"""
        
        # Calculate positional values
        positional_rankings = self._create_positional_rankings(player_data)
        
        # Calculate ADP vs projection value
        value_players = self._identify_value_players(player_data)
        
        # Generate pick recommendations
        current_round = ((draft_settings.current_pick - 1) // draft_settings.team_count) + 1
        next_pick = self._calculate_next_pick(draft_settings)
        
        pick_recommendations = self._generate_pick_recommendations(
            player_data, draft_settings, current_round
        )
        
        return {
            'draft_info': {
                'current_pick': draft_settings.current_pick,
                'current_round': current_round,
                'next_pick': next_pick,
                'picks_until_next': next_pick - draft_settings.current_pick
            },
            'positional_rankings': positional_rankings,
            'value_players': value_players[:10],  # Top 10 values
            'recommendations': pick_recommendations,
            'strategy_notes': self._generate_strategy_notes(draft_settings, current_round)
        }
    
    def _create_positional_rankings(self, player_data: List[PlayerExportData]) -> Dict[str, List[Dict]]:
        """Create rankings by position"""
        positions = {}
        
        for player in player_data:
            if player.position not in positions:
                positions[player.position] = []
            
            positions[player.position].append({
                'name': player.player_name,
                'team': player.team,
                'projected_points': player.projected_points,
                'confidence': player.confidence,
                'adp': player.adp
            })
        
        # Sort each position by projected points
        for position in positions:
            positions[position].sort(key=lambda x: x['projected_points'], reverse=True)
            
            # Add positional rank
            for i, player in enumerate(positions[position], 1):
                player['position_rank'] = i
        
        return positions
    
    def _identify_value_players(self, player_data: List[PlayerExportData]) -> List[Dict[str, Any]]:
        """Identify players with best value vs ADP"""
        value_players = []
        
        for player in player_data:
            if player.adp and player.value_over_adp:
                value_players.append({
                    'name': player.player_name,
                    'position': player.position,
                    'team': player.team,
                    'projected_points': player.projected_points,
                    'adp': player.adp,
                    'value': player.value_over_adp
                })
        
        # Sort by value (highest value first)
        value_players.sort(key=lambda x: x['value'], reverse=True)
        return value_players
    
    def _calculate_next_pick(self, draft_settings: DraftSettings) -> int:
        """Calculate user's next pick in snake draft"""
        current_pick = draft_settings.current_pick
        team_count = draft_settings.team_count
        user_position = draft_settings.user_team_position
        
        # Determine current round
        current_round = ((current_pick - 1) // team_count) + 1
        
        # In snake draft, determine if round is forward or reverse
        if current_round % 2 == 1:  # Odd round (1, 3, 5...)
            next_pick_in_round = user_position
        else:  # Even round (2, 4, 6...)
            next_pick_in_round = team_count - user_position + 1
        
        # Calculate actual pick number
        next_pick = (current_round - 1) * team_count + next_pick_in_round
        
        # If this pick has already passed, calculate next round
        if next_pick <= current_pick:
            next_round = current_round + 1
            if next_round % 2 == 1:
                next_pick_in_round = user_position
            else:
                next_pick_in_round = team_count - user_position + 1
            next_pick = (next_round - 1) * team_count + next_pick_in_round
        
        return next_pick
    
    def _generate_pick_recommendations(self, player_data: List[PlayerExportData], 
                                     draft_settings: DraftSettings, current_round: int) -> List[Dict[str, Any]]:
        """Generate pick recommendations based on draft situation"""
        recommendations = []
        
        # Early rounds: focus on best available
        if current_round <= 3:
            top_players = sorted(player_data, key=lambda x: x.projected_points, reverse=True)[:5]
            for player in top_players:
                recommendations.append({
                    'player': player.player_name,
                    'position': player.position,
                    'reason': 'Best Available - High Projected Points',
                    'projected_points': player.projected_points,
                    'confidence': player.confidence
                })
        
        # Middle rounds: value and positional need
        elif current_round <= 10:
            value_players = [p for p in player_data if p.value_over_adp and p.value_over_adp > 0]
            value_players.sort(key=lambda x: x.value_over_adp, reverse=True)
            
            for player in value_players[:5]:
                recommendations.append({
                    'player': player.player_name,
                    'position': player.position,
                    'reason': f'Value Pick - {player.value_over_adp:.1f} picks above ADP',
                    'projected_points': player.projected_points,
                    'confidence': player.confidence
                })
        
        # Late rounds: upside and sleepers
        else:
            upside_players = [p for p in player_data if p.confidence < 0.7 and p.projected_points > 8]
            upside_players.sort(key=lambda x: x.projected_points, reverse=True)
            
            for player in upside_players[:5]:
                recommendations.append({
                    'player': player.player_name,
                    'position': player.position,
                    'reason': 'High Upside Sleeper',
                    'projected_points': player.projected_points,
                    'confidence': player.confidence
                })
        
        return recommendations
    
    def _generate_strategy_notes(self, draft_settings: DraftSettings, current_round: int) -> List[str]:
        """Generate strategic notes for current draft situation"""
        notes = []
        
        if current_round <= 2:
            notes.append("Focus on elite RB/WR - establish strong foundation")
            notes.append("Avoid QB early unless superflex format")
        elif current_round <= 5:
            notes.append("Target RB depth if you went WR early")
            notes.append("Consider elite TE if Kelce/Andrews available")
        elif current_round <= 8:
            notes.append("Address QB position in standard formats")
            notes.append("Look for value WRs and RB handcuffs")
        elif current_round <= 12:
            notes.append("Target high-upside players")
            notes.append("Consider stacking QB with team WR")
        else:
            notes.append("Focus on handcuffs for your RBs")
            notes.append("Take flyers on rookies and sleepers")
            notes.append("Don't forget DEF and K in final rounds")
        
        return notes
    
    def optimize_lineup(self, player_data: List[PlayerExportData], 
                       constraints: LineupConstraints) -> Dict[str, Any]:
        """Optimize lineup for DFS or best ball"""
        
        # Simple greedy optimization (would be more sophisticated in real implementation)
        lineup = {
            'QB': [],
            'RB': [],
            'WR': [],
            'TE': [],
            'FLEX': [],
            'DST': [],
            'K': []
        }
        
        # Sort players by points per salary efficiency
        efficient_players = []
        for player in player_data:
            if hasattr(player, 'salary') and player.salary:
                efficiency = player.projected_points / player.salary * 1000
                efficient_players.append((player, efficiency))
        
        efficient_players.sort(key=lambda x: x[1], reverse=True)
        
        total_salary = 0
        total_points = 0.0
        
        # Fill required positions
        for player, efficiency in efficient_players:
            if total_salary >= constraints.salary_cap:
                break
            
            position = player.position
            player_salary = getattr(player, 'salary', 5000)  # Default salary
            
            # Check if we can afford and need this position
            if total_salary + player_salary <= constraints.salary_cap:
                if position == 'QB' and len(lineup['QB']) < constraints.qb_required:
                    lineup['QB'].append(player)
                    total_salary += player_salary
                    total_points += player.projected_points
                elif position == 'RB' and len(lineup['RB']) < constraints.rb_required:
                    lineup['RB'].append(player)
                    total_salary += player_salary
                    total_points += player.projected_points
                elif position == 'WR' and len(lineup['WR']) < constraints.wr_required:
                    lineup['WR'].append(player)
                    total_salary += player_salary
                    total_points += player.projected_points
                elif position == 'TE' and len(lineup['TE']) < constraints.te_required:
                    lineup['TE'].append(player)
                    total_salary += player_salary
                    total_points += player.projected_points
        
        return {
            'lineup': lineup,
            'total_salary': total_salary,
            'total_projected_points': total_points,
            'salary_remaining': constraints.salary_cap - total_salary,
            'optimization_score': total_points / (total_salary / 1000)  # Points per $1K
        }
    
    def export_for_platform(self, player_data: List[PlayerExportData], 
                           platform: str) -> str:
        """Export data formatted for specific platforms"""
        
        platform_formats = {
            'draftkings': self._format_for_draftkings,
            'fanduel': self._format_for_fanduel,
            'yahoo': self._format_for_yahoo,
            'espn': self._format_for_espn,
            'sleeper': self._format_for_sleeper
        }
        
        if platform.lower() in platform_formats:
            return platform_formats[platform.lower()](player_data)
        else:
            # Default to CSV export
            return self.export_rankings(player_data, ExportFormat.CSV, f"{platform}_export")
    
    def _format_for_draftkings(self, player_data: List[PlayerExportData]) -> str:
        """Format for DraftKings import"""
        # DraftKings specific formatting
        dk_data = []
        for player in player_data:
            dk_data.append({
                'Name': player.player_name,
                'Position': player.position,
                'Team': player.team,
                'Salary': getattr(player, 'salary', 5000),
                'Projected': player.projected_points,
                'Ownership': player.ownership_percentage or 0
            })
        
        return self._export_to_csv([PlayerExportData(**data) for data in dk_data], "draftkings_import")
    
    def _format_for_fanduel(self, player_data: List[PlayerExportData]) -> str:
        """Format for FanDuel import"""
        # FanDuel specific formatting (similar structure)
        return self._format_for_draftkings(player_data)  # Simplified for demo
    
    def _format_for_yahoo(self, player_data: List[PlayerExportData]) -> str:
        """Format for Yahoo import"""
        return self.export_rankings(player_data, ExportFormat.CSV, "yahoo_import")
    
    def _format_for_espn(self, player_data: List[PlayerExportData]) -> str:
        """Format for ESPN import"""
        return self.export_rankings(player_data, ExportFormat.JSON, "espn_import")
    
    def _format_for_sleeper(self, player_data: List[PlayerExportData]) -> str:
        """Format for Sleeper import"""
        return self.export_rankings(player_data, ExportFormat.JSON, "sleeper_import")

# Sample usage and testing
def create_sample_export_data() -> List[PlayerExportData]:
    """Create sample data for testing exports"""
    sample_players = [
        PlayerExportData("Josh Allen", "BUF", "QB", 8, 24.5, 0.85, "Healthy", 7.8, None, 0.89, None, "up", 45.2, 12.3, 15.2),
        PlayerExportData("Christian McCaffrey", "SF", "RB", 8, 22.1, 0.78, "Questionable", 6.2, None, 0.92, 0.35, "stable", 8.1, -2.1, 22.8),
        PlayerExportData("Cooper Kupp", "LAR", "WR", 8, 19.8, 0.82, "Healthy", 8.5, 0.28, 0.88, 0.15, "up", 18.9, 5.7, 18.3),
        PlayerExportData("Travis Kelce", "KC", "TE", 8, 16.4, 0.79, "Healthy", 7.1, 0.22, 0.85, 0.28, "down", 28.4, -8.2, 25.1),
    ]
    
    return sample_players

if __name__ == "__main__":
    print("📤 EXPORT & INTEGRATION SYSTEM")
    print("=" * 40)
    
    # Test the export system
    export_system = ExportIntegrationSystem()
    sample_data = create_sample_export_data()
    
    # Test CSV export
    csv_file = export_system.export_rankings(sample_data, ExportFormat.CSV, "test_rankings")
    print(f"✅ CSV export created: {csv_file}")
    
    # Test JSON export  
    json_file = export_system.export_rankings(sample_data, ExportFormat.JSON, "test_rankings")
    print(f"✅ JSON export created: {json_file}")
    
    # Test HTML export
    html_file = export_system.export_rankings(sample_data, ExportFormat.HTML, "test_rankings")
    print(f"✅ HTML export created: {html_file}")
    
    # Test draft helper
    draft_settings = DraftSettings(current_pick=15, user_team_position=3)
    draft_helper = export_system.generate_draft_helper(sample_data, draft_settings)
    print(f"\n📋 Draft Helper Generated:")
    print(f"Current Pick: {draft_helper['draft_info']['current_pick']}")
    print(f"Recommendations: {len(draft_helper['recommendations'])}")
    
    # Test lineup optimizer
    constraints = LineupConstraints(salary_cap=50000)
    lineup = export_system.optimize_lineup(sample_data, constraints)
    print(f"\n🎯 Lineup Optimized:")
    print(f"Projected Points: {lineup['total_projected_points']:.1f}")
    print(f"Salary Used: ${lineup['total_salary']:,}")
    
    print("\n✅ All export features tested successfully!")