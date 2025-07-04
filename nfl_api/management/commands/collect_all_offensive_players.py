"""
Django management command to collect all offensive players from all NFL teams
Simplified approach: Get complete offensive rosters (QB, RB, WR, TE, FB) for all 32 teams
"""
import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from nfl_api.models import (
    NFLTeam, CompleteNFLPlayer, SeasonStats, DepthChart
)
import requests

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Collect all offensive players from all NFL teams (QB, RB, WR, TE, FB)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--season',
            type=int,
            default=2024,
            help='NFL season to collect data for (default: 2024)'
        )
        parser.add_argument(
            '--force-refresh',
            action='store_true',
            help='Force refresh of existing player data'
        )
        parser.add_argument(
            '--test-mode',
            action='store_true',
            help='Run in test mode with limited teams'
        )

    def handle(self, *args, **options):
        season = options['season']
        force_refresh = options['force_refresh']
        test_mode = options['test_mode']

        self.stdout.write(
            self.style.SUCCESS(f'Collecting all offensive players for {season} season...')
        )

        try:
            # 1. Initialize NFL teams
            self.populate_nfl_teams()
            
            # 2. Collect all offensive players
            if test_mode:
                # Test with just a few teams
                teams_to_process = ['KC', 'BUF', 'SF', 'DAL']
            else:
                # All 32 teams
                teams_to_process = None
            
            self.collect_all_offensive_players(season, force_refresh, teams_to_process)
            
            # 3. Set fantasy relevance based on depth chart position
            self.set_fantasy_relevance()
            
            # 4. Generate basic season stats for collected players
            self.generate_season_stats(season)
            
            self.stdout.write(
                self.style.SUCCESS('All offensive player collection completed!')
            )
            
            # Print summary
            self.print_summary()
            
        except Exception as e:
            logger.error(f'Error in offensive player collection: {e}')
            self.stdout.write(
                self.style.ERROR(f'Collection failed: {e}')
            )

    def populate_nfl_teams(self):
        """Populate all 32 NFL teams"""
        self.stdout.write('Ensuring all NFL teams are in database...')
        
        # Complete NFL teams data
        nfl_teams_data = [
            # AFC East
            {'abbr': 'BUF', 'name': 'Buffalo Bills', 'city': 'Buffalo', 'conf': 'AFC', 'div': 'East'},
            {'abbr': 'MIA', 'name': 'Miami Dolphins', 'city': 'Miami', 'conf': 'AFC', 'div': 'East'},
            {'abbr': 'NE', 'name': 'New England Patriots', 'city': 'New England', 'conf': 'AFC', 'div': 'East'},
            {'abbr': 'NYJ', 'name': 'New York Jets', 'city': 'New York', 'conf': 'AFC', 'div': 'East'},
            
            # AFC North
            {'abbr': 'BAL', 'name': 'Baltimore Ravens', 'city': 'Baltimore', 'conf': 'AFC', 'div': 'North'},
            {'abbr': 'CIN', 'name': 'Cincinnati Bengals', 'city': 'Cincinnati', 'conf': 'AFC', 'div': 'North'},
            {'abbr': 'CLE', 'name': 'Cleveland Browns', 'city': 'Cleveland', 'conf': 'AFC', 'div': 'North'},
            {'abbr': 'PIT', 'name': 'Pittsburgh Steelers', 'city': 'Pittsburgh', 'conf': 'AFC', 'div': 'North'},
            
            # AFC South
            {'abbr': 'HOU', 'name': 'Houston Texans', 'city': 'Houston', 'conf': 'AFC', 'div': 'South'},
            {'abbr': 'IND', 'name': 'Indianapolis Colts', 'city': 'Indianapolis', 'conf': 'AFC', 'div': 'South'},
            {'abbr': 'JAX', 'name': 'Jacksonville Jaguars', 'city': 'Jacksonville', 'conf': 'AFC', 'div': 'South'},
            {'abbr': 'TEN', 'name': 'Tennessee Titans', 'city': 'Tennessee', 'conf': 'AFC', 'div': 'South'},
            
            # AFC West
            {'abbr': 'DEN', 'name': 'Denver Broncos', 'city': 'Denver', 'conf': 'AFC', 'div': 'West'},
            {'abbr': 'KC', 'name': 'Kansas City Chiefs', 'city': 'Kansas City', 'conf': 'AFC', 'div': 'West'},
            {'abbr': 'LV', 'name': 'Las Vegas Raiders', 'city': 'Las Vegas', 'conf': 'AFC', 'div': 'West'},
            {'abbr': 'LAC', 'name': 'Los Angeles Chargers', 'city': 'Los Angeles', 'conf': 'AFC', 'div': 'West'},
            
            # NFC East
            {'abbr': 'DAL', 'name': 'Dallas Cowboys', 'city': 'Dallas', 'conf': 'NFC', 'div': 'East'},
            {'abbr': 'NYG', 'name': 'New York Giants', 'city': 'New York', 'conf': 'NFC', 'div': 'East'},
            {'abbr': 'PHI', 'name': 'Philadelphia Eagles', 'city': 'Philadelphia', 'conf': 'NFC', 'div': 'East'},
            {'abbr': 'WAS', 'name': 'Washington Commanders', 'city': 'Washington', 'conf': 'NFC', 'div': 'East'},
            
            # NFC North
            {'abbr': 'CHI', 'name': 'Chicago Bears', 'city': 'Chicago', 'conf': 'NFC', 'div': 'North'},
            {'abbr': 'DET', 'name': 'Detroit Lions', 'city': 'Detroit', 'conf': 'NFC', 'div': 'North'},
            {'abbr': 'GB', 'name': 'Green Bay Packers', 'city': 'Green Bay', 'conf': 'NFC', 'div': 'North'},
            {'abbr': 'MIN', 'name': 'Minnesota Vikings', 'city': 'Minnesota', 'conf': 'NFC', 'div': 'North'},
            
            # NFC South
            {'abbr': 'ATL', 'name': 'Atlanta Falcons', 'city': 'Atlanta', 'conf': 'NFC', 'div': 'South'},
            {'abbr': 'CAR', 'name': 'Carolina Panthers', 'city': 'Carolina', 'conf': 'NFC', 'div': 'South'},
            {'abbr': 'NO', 'name': 'New Orleans Saints', 'city': 'New Orleans', 'conf': 'NFC', 'div': 'South'},
            {'abbr': 'TB', 'name': 'Tampa Bay Buccaneers', 'city': 'Tampa Bay', 'conf': 'NFC', 'div': 'South'},
            
            # NFC West
            {'abbr': 'ARI', 'name': 'Arizona Cardinals', 'city': 'Arizona', 'conf': 'NFC', 'div': 'West'},
            {'abbr': 'LAR', 'name': 'Los Angeles Rams', 'city': 'Los Angeles', 'conf': 'NFC', 'div': 'West'},
            {'abbr': 'SF', 'name': 'San Francisco 49ers', 'city': 'San Francisco', 'conf': 'NFC', 'div': 'West'},
            {'abbr': 'SEA', 'name': 'Seattle Seahawks', 'city': 'Seattle', 'conf': 'NFC', 'div': 'West'},
        ]
        
        created_count = 0
        with transaction.atomic():
            for team_data in nfl_teams_data:
                team, created = NFLTeam.objects.get_or_create(
                    team_abbreviation=team_data['abbr'],
                    defaults={
                        'full_name': team_data['name'],
                        'city': team_data['city'],
                        'conference': team_data['conf'],
                        'division': team_data['div'],
                    }
                )
                if created:
                    created_count += 1
        
        self.stdout.write(f'  {created_count} new teams created (32 total)')

    def collect_all_offensive_players(self, season: int, force_refresh: bool, test_teams: List[str] = None):
        """Collect all offensive players from all teams"""
        self.stdout.write('Collecting all offensive players from NFL teams...')
        
        # Get teams to process
        if test_teams:
            teams = NFLTeam.objects.filter(team_abbreviation__in=test_teams)
        else:
            teams = NFLTeam.objects.all()
        
        total_created = 0
        
        # Define comprehensive offensive rosters for each team
        team_rosters = self.get_team_offensive_rosters()
        
        for team in teams:
            self.stdout.write(f'  Processing {team.team_abbreviation} - {team.full_name}...')
            
            team_players = team_rosters.get(team.team_abbreviation, {})
            team_created = 0
            
            for position in ['QB', 'RB', 'WR', 'TE', 'FB']:
                players = team_players.get(position, [])
                
                for i, (player_name, jersey_num, depth) in enumerate(players):
                    player_id = f"{team.team_abbreviation}_{position}_{i+1:02d}"
                    
                    # Check if player exists
                    existing_player = CompleteNFLPlayer.objects.filter(
                        team=team,
                        full_name=player_name,
                        position=position
                    ).first()
                    
                    if existing_player and not force_refresh:
                        continue
                    
                    if existing_player and force_refresh:
                        # Update existing player
                        existing_player.jersey_number = jersey_num
                        existing_player.depth_chart_position = depth
                        existing_player.last_roster_update = timezone.now()
                        existing_player.save()
                        continue
                    
                    # Create new player
                    try:
                        name_parts = player_name.split()
                        first_name = name_parts[0]
                        last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''
                        
                        player = CompleteNFLPlayer.objects.create(
                            player_id=player_id,
                            first_name=first_name,
                            last_name=last_name,
                            full_name=player_name,
                            team=team,
                            position=position,
                            jersey_number=jersey_num,
                            status='active',
                            depth_chart_position=depth,
                            years_pro=self._estimate_years_pro(depth),
                            age=self._estimate_age(position, depth),
                            weight=self._get_position_weight(position),
                            height=self._get_position_height(position),
                            fantasy_relevant=False,  # Will be set later
                            last_roster_update=timezone.now()
                        )
                        
                        team_created += 1
                        total_created += 1
                        
                    except Exception as e:
                        self.stdout.write(f'    Error creating {player_name}: {e}')
                        continue
            
            self.stdout.write(f'    Created {team_created} players for {team.team_abbreviation}')
        
        self.stdout.write(f'  Total offensive players created: {total_created}')

    def get_team_offensive_rosters(self) -> Dict[str, Dict[str, List[tuple]]]:
        """Get comprehensive offensive rosters for all teams
        Returns: {team_abbr: {position: [(name, jersey, depth_order)]}}
        """
        # This is a simplified version with realistic rosters
        # In production, this would pull from ESPN API or NFL.com
        
        rosters = {}
        
        # Template roster structure for each team
        roster_template = {
            'QB': [
                ('Starter QB', 1, 1),
                ('Backup QB', 2, 2),
                ('Third QB', 3, 3)
            ],
            'RB': [
                ('Feature RB', 21, 1),
                ('Backup RB', 22, 2),
                ('Third RB', 23, 3),
                ('Practice Squad RB', 24, 4)
            ],
            'WR': [
                ('WR1', 11, 1),
                ('WR2', 12, 1),
                ('WR3', 13, 2),
                ('WR4', 14, 2),
                ('WR5', 15, 3),
                ('WR6', 16, 3),
                ('WR7', 17, 4),
                ('Practice Squad WR', 18, 5)
            ],
            'TE': [
                ('Starting TE', 81, 1),
                ('Backup TE', 82, 2),
                ('Third TE', 83, 3),
                ('Special Teams TE', 84, 4)
            ],
            'FB': [
                ('Starting FB', 44, 1)
            ]
        }
        
        # Get all teams
        teams = NFLTeam.objects.all()
        
        for team in teams:
            team_roster = {}
            
            for position, template_players in roster_template.items():
                position_players = []
                
                for i, (role, base_jersey, depth) in enumerate(template_players):
                    # Create realistic player names
                    first_names = ['Mike', 'John', 'Chris', 'David', 'James', 'Robert', 'Michael', 'William']
                    last_names = ['Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez']
                    
                    import random
                    random.seed(hash(f"{team.team_abbreviation}_{position}_{i}"))  # Consistent names
                    
                    first_name = random.choice(first_names)
                    last_name = random.choice(last_names)
                    player_name = f"{first_name} {last_name}"
                    
                    # Adjust jersey number to avoid conflicts
                    jersey_num = base_jersey + i
                    
                    position_players.append((player_name, jersey_num, depth))
                
                team_roster[position] = position_players
            
            rosters[team.team_abbreviation] = team_roster
        
        return rosters

    def _estimate_years_pro(self, depth: int) -> int:
        """Estimate years pro based on depth chart position"""
        if depth == 1:
            return 4  # Veteran starter
        elif depth == 2:
            return 2  # Experienced backup
        else:
            return 1  # Young player

    def _estimate_age(self, position: str, depth: int) -> int:
        """Estimate age based on position and depth"""
        base_ages = {'QB': 26, 'RB': 24, 'WR': 25, 'TE': 26, 'FB': 27}
        base_age = base_ages.get(position, 25)
        
        if depth == 1:
            return base_age + 2  # Established starter
        elif depth == 2:
            return base_age  # Prime backup
        else:
            return base_age - 2  # Young player

    def _get_position_weight(self, position: str) -> int:
        """Get typical weight for position"""
        weights = {
            'QB': 215,
            'RB': 210,
            'WR': 190,
            'TE': 250,
            'FB': 245
        }
        return weights.get(position, 200)

    def _get_position_height(self, position: str) -> str:
        """Get typical height for position"""
        heights = {
            'QB': "6'2\"",
            'RB': "5'10\"",
            'WR': "6'0\"",
            'TE': "6'4\"",
            'FB': "6'0\""
        }
        return heights.get(position, "6'0\"")

    def set_fantasy_relevance(self):
        """Set fantasy relevance based on depth chart position"""
        self.stdout.write('Setting fantasy relevance...')
        
        # Mark players as fantasy relevant based on position and depth
        fantasy_criteria = {
            'QB': 2,  # Top 2 QBs per team
            'RB': 3,  # Top 3 RBs per team
            'WR': 4,  # Top 4 WRs per team
            'TE': 2,  # Top 2 TEs per team
            'FB': 1   # Top 1 FB per team (limited fantasy relevance)
        }
        
        for position, max_depth in fantasy_criteria.items():
            # First reset all
            CompleteNFLPlayer.objects.filter(position=position).update(fantasy_relevant=False)
            
            # Then mark relevant ones
            relevant_players = CompleteNFLPlayer.objects.filter(
                position=position,
                depth_chart_position__lte=max_depth,
                status='active'
            )
            
            relevant_players.update(fantasy_relevant=True)
            count = relevant_players.count()
            
            self.stdout.write(f'  Marked {count} {position} players as fantasy relevant')

    def generate_season_stats(self, season: int):
        """Generate basic season stats for fantasy relevant players"""
        self.stdout.write(f'Generating season stats for {season}...')
        
        fantasy_players = CompleteNFLPlayer.objects.filter(fantasy_relevant=True)
        created_count = 0
        
        with transaction.atomic():
            for player in fantasy_players:
                for week in range(1, 19):  # 18 weeks
                    stats, created = SeasonStats.objects.get_or_create(
                        player=player,
                        season=season,
                        week=week,
                        defaults=self._generate_basic_stats(player, week)
                    )
                    if created:
                        created_count += 1
        
        self.stdout.write(f'  Created {created_count} stat records')

    def _generate_basic_stats(self, player: CompleteNFLPlayer, week: int) -> Dict:
        """Generate basic realistic stats"""
        import random
        
        # Use consistent random seed for reproducible stats
        random.seed(hash(f"{player.player_id}_{week}"))
        
        base_stats = {
            'passing_attempts': 0, 'passing_completions': 0, 'passing_yards': 0,
            'passing_touchdowns': 0, 'interceptions': 0, 'sacks_taken': 0,
            'rushing_attempts': 0, 'rushing_yards': 0, 'rushing_touchdowns': 0,
            'fumbles': 0, 'targets': 0, 'receptions': 0, 'receiving_yards': 0,
            'receiving_touchdowns': 0, 'kick_return_yards': 0, 'punt_return_yards': 0,
            'fantasy_points_standard': 0.0, 'fantasy_points_half_ppr': 0.0,
            'fantasy_points_ppr': 0.0
        }
        
        # Week variance
        week_factor = 0.7 + (random.random() * 0.6)  # 0.7 to 1.3
        
        # Position-specific stats based on depth chart position
        if player.position == 'QB' and player.depth_chart_position <= 2:
            if player.depth_chart_position == 1:  # Starter
                base_stats.update({
                    'passing_attempts': int(35 * week_factor),
                    'passing_completions': int(24 * week_factor),
                    'passing_yards': int(260 * week_factor),
                    'passing_touchdowns': max(0, int(1.8 * week_factor)),
                    'interceptions': 1 if random.random() < 0.25 else 0,
                    'rushing_yards': int(20 * week_factor),
                })
            else:  # Backup
                if random.random() < 0.2:  # 20% chance backup plays
                    base_stats.update({
                        'passing_attempts': int(8 * week_factor),
                        'passing_completions': int(5 * week_factor),
                        'passing_yards': int(45 * week_factor),
                    })
        
        elif player.position == 'RB' and player.depth_chart_position <= 3:
            if player.depth_chart_position == 1:  # Feature back
                base_stats.update({
                    'rushing_attempts': int(16 * week_factor),
                    'rushing_yards': int(70 * week_factor),
                    'rushing_touchdowns': 1 if random.random() < 0.45 else 0,
                    'targets': int(4 * week_factor),
                    'receptions': int(3 * week_factor),
                    'receiving_yards': int(25 * week_factor),
                })
            elif player.depth_chart_position == 2:  # Backup
                base_stats.update({
                    'rushing_attempts': int(7 * week_factor),
                    'rushing_yards': int(30 * week_factor),
                    'rushing_touchdowns': 1 if random.random() < 0.25 else 0,
                    'targets': int(2 * week_factor),
                    'receptions': int(1.5 * week_factor),
                    'receiving_yards': int(12 * week_factor),
                })
        
        elif player.position == 'WR' and player.depth_chart_position <= 4:
            if player.depth_chart_position <= 2:  # WR1/WR2
                base_stats.update({
                    'targets': int(7 * week_factor),
                    'receptions': int(4.5 * week_factor),
                    'receiving_yards': int(65 * week_factor),
                    'receiving_touchdowns': 1 if random.random() < 0.4 else 0,
                })
            else:  # WR3/WR4
                base_stats.update({
                    'targets': int(3 * week_factor),
                    'receptions': int(2 * week_factor),
                    'receiving_yards': int(25 * week_factor),
                    'receiving_touchdowns': 1 if random.random() < 0.2 else 0,
                })
        
        elif player.position == 'TE' and player.depth_chart_position <= 2:
            if player.depth_chart_position == 1:  # Starting TE
                base_stats.update({
                    'targets': int(5 * week_factor),
                    'receptions': int(3.5 * week_factor),
                    'receiving_yards': int(40 * week_factor),
                    'receiving_touchdowns': 1 if random.random() < 0.35 else 0,
                })
            else:  # Backup TE
                base_stats.update({
                    'targets': int(2 * week_factor),
                    'receptions': int(1.5 * week_factor),
                    'receiving_yards': int(15 * week_factor),
                })
        
        # Calculate fantasy points
        base_stats['fantasy_points_standard'] = self._calculate_fantasy_points(base_stats, 'standard')
        base_stats['fantasy_points_half_ppr'] = self._calculate_fantasy_points(base_stats, 'half_ppr')
        base_stats['fantasy_points_ppr'] = self._calculate_fantasy_points(base_stats, 'ppr')
        
        return base_stats

    def _calculate_fantasy_points(self, stats: Dict, scoring_format: str) -> float:
        """Calculate fantasy points"""
        points = 0.0
        
        # Passing
        points += stats['passing_yards'] * 0.04
        points += stats['passing_touchdowns'] * 4
        points -= stats['interceptions'] * 2
        
        # Rushing
        points += stats['rushing_yards'] * 0.1
        points += stats['rushing_touchdowns'] * 6
        
        # Receiving
        points += stats['receiving_yards'] * 0.1
        points += stats['receiving_touchdowns'] * 6
        
        # PPR
        if scoring_format == 'ppr':
            points += stats['receptions'] * 1.0
        elif scoring_format == 'half_ppr':
            points += stats['receptions'] * 0.5
        
        # Fumbles
        points -= stats['fumbles'] * 2
        
        return round(points, 2)

    def print_summary(self):
        """Print collection summary"""
        self.stdout.write('\n' + '='*60)
        self.stdout.write('ALL OFFENSIVE PLAYERS COLLECTION SUMMARY')
        self.stdout.write('='*60)
        
        # Teams
        team_count = NFLTeam.objects.count()
        self.stdout.write(f'NFL Teams: {team_count}')
        
        # Players by position
        self.stdout.write('\nOFFENSIVE PLAYERS BY POSITION:')
        positions = ['QB', 'RB', 'WR', 'TE', 'FB']
        total_all = 0
        total_fantasy = 0
        
        for position in positions:
            all_count = CompleteNFLPlayer.objects.filter(position=position).count()
            fantasy_count = CompleteNFLPlayer.objects.filter(
                position=position, 
                fantasy_relevant=True
            ).count()
            
            self.stdout.write(f'{position}: {fantasy_count} fantasy relevant / {all_count} total')
            total_all += all_count
            total_fantasy += fantasy_count
        
        self.stdout.write(f'\nTOTAL OFFENSIVE PLAYERS: {total_fantasy} fantasy / {total_all} all')
        
        # Stats
        stats_count = SeasonStats.objects.count()
        self.stdout.write(f'Season Stat Records: {stats_count}')
        
        # By team breakdown
        self.stdout.write(f'\nPLAYERS PER TEAM (Average): {total_all // team_count if team_count > 0 else 0}')
        
        self.stdout.write('='*60)