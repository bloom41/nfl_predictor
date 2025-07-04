"""
Django management command to populate comprehensive NFL player database
Populates expanded player counts: QB(20), RB(70), WR(70), TE(15)
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
    NFLTeam, CompleteNFLPlayer, SeasonStats, DepthChart, 
    Player, GameResult
)
import requests

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Populate comprehensive NFL player database with expanded player counts'

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
            help='Force refresh of existing data'
        )
        parser.add_argument(
            '--test-mode',
            action='store_true',
            help='Run in test mode with limited data'
        )

    def handle(self, *args, **options):
        season = options['season']
        force_refresh = options['force_refresh']
        test_mode = options['test_mode']

        self.stdout.write(
            self.style.SUCCESS(f'Starting comprehensive NFL data population for {season}...')
        )

        try:
            # 1. Initialize NFL teams
            self.populate_nfl_teams()
            
            # 2. Populate expanded player database
            if test_mode:
                # Reduced counts for testing
                target_counts = {'QB': 5, 'RB': 10, 'WR': 10, 'TE': 5}
            else:
                # Full expanded counts as requested
                target_counts = {'QB': 20, 'RB': 70, 'WR': 70, 'TE': 15}
            
            self.populate_comprehensive_players(season, target_counts, force_refresh)
            
            # 3. Populate season statistics
            self.populate_season_statistics(season, target_counts)
            
            # 4. Setup depth charts
            self.setup_depth_charts(season)
            
            # 5. Mark fantasy relevant players
            self.mark_fantasy_relevant_players(target_counts)
            
            self.stdout.write(
                self.style.SUCCESS('Comprehensive NFL data population completed!')
            )
            
            # Print summary
            self.print_database_summary()
            
        except Exception as e:
            logger.error(f'Error in comprehensive data population: {e}')
            self.stdout.write(
                self.style.ERROR(f'Population failed: {e}')
            )

    def populate_nfl_teams(self):
        """Populate all 32 NFL teams"""
        self.stdout.write('Populating NFL teams...')
        
        nfl_teams_data = [
            {'abbr': 'ARI', 'name': 'Arizona Cardinals', 'city': 'Arizona', 'conf': 'NFC', 'div': 'West'},
            {'abbr': 'ATL', 'name': 'Atlanta Falcons', 'city': 'Atlanta', 'conf': 'NFC', 'div': 'South'},
            {'abbr': 'BAL', 'name': 'Baltimore Ravens', 'city': 'Baltimore', 'conf': 'AFC', 'div': 'North'},
            {'abbr': 'BUF', 'name': 'Buffalo Bills', 'city': 'Buffalo', 'conf': 'AFC', 'div': 'East'},
            {'abbr': 'CAR', 'name': 'Carolina Panthers', 'city': 'Carolina', 'conf': 'NFC', 'div': 'South'},
            {'abbr': 'CHI', 'name': 'Chicago Bears', 'city': 'Chicago', 'conf': 'NFC', 'div': 'North'},
            {'abbr': 'CIN', 'name': 'Cincinnati Bengals', 'city': 'Cincinnati', 'conf': 'AFC', 'div': 'North'},
            {'abbr': 'CLE', 'name': 'Cleveland Browns', 'city': 'Cleveland', 'conf': 'AFC', 'div': 'North'},
            {'abbr': 'DAL', 'name': 'Dallas Cowboys', 'city': 'Dallas', 'conf': 'NFC', 'div': 'East'},
            {'abbr': 'DEN', 'name': 'Denver Broncos', 'city': 'Denver', 'conf': 'AFC', 'div': 'West'},
            {'abbr': 'DET', 'name': 'Detroit Lions', 'city': 'Detroit', 'conf': 'NFC', 'div': 'North'},
            {'abbr': 'GB', 'name': 'Green Bay Packers', 'city': 'Green Bay', 'conf': 'NFC', 'div': 'North'},
            {'abbr': 'HOU', 'name': 'Houston Texans', 'city': 'Houston', 'conf': 'AFC', 'div': 'South'},
            {'abbr': 'IND', 'name': 'Indianapolis Colts', 'city': 'Indianapolis', 'conf': 'AFC', 'div': 'South'},
            {'abbr': 'JAX', 'name': 'Jacksonville Jaguars', 'city': 'Jacksonville', 'conf': 'AFC', 'div': 'South'},
            {'abbr': 'KC', 'name': 'Kansas City Chiefs', 'city': 'Kansas City', 'conf': 'AFC', 'div': 'West'},
            {'abbr': 'LV', 'name': 'Las Vegas Raiders', 'city': 'Las Vegas', 'conf': 'AFC', 'div': 'West'},
            {'abbr': 'LAC', 'name': 'Los Angeles Chargers', 'city': 'Los Angeles', 'conf': 'AFC', 'div': 'West'},
            {'abbr': 'LAR', 'name': 'Los Angeles Rams', 'city': 'Los Angeles', 'conf': 'NFC', 'div': 'West'},
            {'abbr': 'MIA', 'name': 'Miami Dolphins', 'city': 'Miami', 'conf': 'AFC', 'div': 'East'},
            {'abbr': 'MIN', 'name': 'Minnesota Vikings', 'city': 'Minnesota', 'conf': 'NFC', 'div': 'North'},
            {'abbr': 'NE', 'name': 'New England Patriots', 'city': 'New England', 'conf': 'AFC', 'div': 'East'},
            {'abbr': 'NO', 'name': 'New Orleans Saints', 'city': 'New Orleans', 'conf': 'NFC', 'div': 'South'},
            {'abbr': 'NYG', 'name': 'New York Giants', 'city': 'New York', 'conf': 'NFC', 'div': 'East'},
            {'abbr': 'NYJ', 'name': 'New York Jets', 'city': 'New York', 'conf': 'AFC', 'div': 'East'},
            {'abbr': 'PHI', 'name': 'Philadelphia Eagles', 'city': 'Philadelphia', 'conf': 'NFC', 'div': 'East'},
            {'abbr': 'PIT', 'name': 'Pittsburgh Steelers', 'city': 'Pittsburgh', 'conf': 'AFC', 'div': 'North'},
            {'abbr': 'SF', 'name': 'San Francisco 49ers', 'city': 'San Francisco', 'conf': 'NFC', 'div': 'West'},
            {'abbr': 'SEA', 'name': 'Seattle Seahawks', 'city': 'Seattle', 'conf': 'NFC', 'div': 'West'},
            {'abbr': 'TB', 'name': 'Tampa Bay Buccaneers', 'city': 'Tampa Bay', 'conf': 'NFC', 'div': 'South'},
            {'abbr': 'TEN', 'name': 'Tennessee Titans', 'city': 'Tennessee', 'conf': 'AFC', 'div': 'South'},
            {'abbr': 'WAS', 'name': 'Washington Commanders', 'city': 'Washington', 'conf': 'NFC', 'div': 'East'},
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
        
        self.stdout.write(f'  Created {created_count} new teams (32 total)')

    def populate_comprehensive_players(self, season: int, target_counts: Dict[str, int], force_refresh: bool):
        """Populate comprehensive player database with expanded counts"""
        self.stdout.write(f'Populating players: {target_counts}')
        
        # Define top players by position for 2024 season
        top_players_by_position = {
            'QB': [
                ('Josh Allen', 'BUF'), ('Lamar Jackson', 'BAL'), ('Dak Prescott', 'DAL'),
                ('Jalen Hurts', 'PHI'), ('Tua Tagovailoa', 'MIA'), ('Joe Burrow', 'CIN'),
                ('Justin Herbert', 'LAC'), ('Kyler Murray', 'ARI'), ('Anthony Richardson', 'IND'),
                ('Caleb Williams', 'CHI'), ('Jayden Daniels', 'WAS'), ('Bo Nix', 'DEN'),
                ('C.J. Stroud', 'HOU'), ('Jordan Love', 'GB'), ('Trevor Lawrence', 'JAX'),
                ('Geno Smith', 'SEA'), ('Brock Purdy', 'SF'), ('Baker Mayfield', 'TB'),
                ('Aaron Rodgers', 'NYJ'), ('Derek Carr', 'NO')
            ],
            'RB': [
                ('Saquon Barkley', 'PHI'), ('Derrick Henry', 'BAL'), ('Josh Jacobs', 'GB'),
                ('Jonathan Taylor', 'IND'), ('Kyren Williams', 'LAR'), ('De\'Von Achane', 'MIA'),
                ('Jahmyr Gibbs', 'DET'), ('David Montgomery', 'DET'), ('Bijan Robinson', 'ATL'),
                ('Breece Hall', 'NYJ'), ('Kenneth Walker III', 'SEA'), ('Alvin Kamara', 'NO'),
                ('James Cook', 'BUF'), ('Rachaad White', 'TB'), ('Tony Pollard', 'TEN'),
                ('Aaron Jones', 'MIN'), ('Joe Mixon', 'HOU'), ('Najee Harris', 'PIT'),
                ('Travis Etienne', 'JAX'), ('Rhamondre Stevenson', 'NE'), ('D\'Andre Swift', 'CHI'),
                ('Jerome Ford', 'CLE'), ('Rico Dowdle', 'DAL'), ('Chuba Hubbard', 'CAR'),
                ('James Conner', 'ARI'), ('Brian Robinson Jr.', 'WAS'), ('Javonte Williams', 'DEN'),
                ('Ezekiel Elliott', 'DAL'), ('Alexander Mattison', 'LV'), ('Tank Bigsby', 'JAX'),
                ('Jaylen Warren', 'PIT'), ('Gus Edwards', 'LAC'), ('Zack Moss', 'CIN'),
                ('Antonio Gibson', 'NE'), ('Justice Hill', 'BAL'), ('Cam Akers', 'HOU'),
                ('Devin Singletary', 'NYG'), ('Jordan Mason', 'SF'), ('Tyler Allgeier', 'ATL'),
                ('Khalil Herbert', 'CHI'), ('Kenneth Gainwell', 'PHI'), ('Zamir White', 'LV'),
                ('Miles Sanders', 'CAR'), ('Roschon Johnson', 'CHI'), ('Tyjae Spears', 'TEN'),
                ('Ray Davis', 'BUF'), ('Braelon Allen', 'NYJ'), ('Blake Corum', 'LAR'),
                ('MarShawn Lloyd', 'GB'), ('Jonathon Brooks', 'CAR'), ('Tyrone Tracy Jr.', 'NYG'),
                ('Austin Ekeler', 'WAS'), ('Chase Brown', 'CIN'), ('Samaje Perine', 'KC'),
                ('Cordarrelle Patterson', 'PIT'), ('Jaleel McLaughlin', 'DEN'), ('Craig Reynolds', 'DET'),
                ('Jeremy McNichols', 'WAS'), ('Dameon Pierce', 'HOU'), ('Clyde Edwards-Helaire', 'KC'),
                ('Ameer Abdullah', 'LV'), ('Israel Abanikanda', 'PIT'), ('Salvon Ahmed', 'MIA'),
                ('Tyler Goodson', 'IND'), ('Dare Ogunbowale', 'TB'), ('D\'Ernest Johnson', 'JAX'),
                ('Ty Johnson', 'BUF'), ('Jeff Wilson Jr.', 'MIA'), ('Julius Chestnut', 'TEN'),
                ('Will Shipley', 'PHI'), ('Keaton Mitchell', 'BAL'), ('Kimani Vidal', 'LAC'),
                ('Eric Gray', 'NYG'), ('Deuce Vaughn', 'DAL'), ('Tank Dell', 'HOU'),
                ('Trey Sermon', 'IND'), ('JaMycal Hasty', 'NE'), ('D\'Onta Foreman', 'CLE')
            ],
            'WR': [
                ('CeeDee Lamb', 'DAL'), ('Tyreek Hill', 'MIA'), ('Ja\'Marr Chase', 'CIN'),
                ('Justin Jefferson', 'MIN'), ('Amon-Ra St. Brown', 'DET'), ('A.J. Brown', 'PHI'),
                ('Stefon Diggs', 'HOU'), ('DK Metcalf', 'SEA'), ('Davante Adams', 'LV'),
                ('Cooper Kupp', 'LAR'), ('Mike Evans', 'TB'), ('Deebo Samuel', 'SF'),
                ('Chris Godwin', 'TB'), ('Jaylen Waddle', 'MIA'), ('DeVonta Smith', 'PHI'),
                ('Tee Higgins', 'CIN'), ('DJ Moore', 'CHI'), ('Garrett Wilson', 'NYJ'),
                ('Calvin Ridley', 'TEN'), ('Amari Cooper', 'CLE'), ('Puka Nacua', 'LAR'),
                ('Terry McLaurin', 'WAS'), ('Nico Collins', 'HOU'), ('Keenan Allen', 'CHI'),
                ('Brandon Aiyuk', 'SF'), ('Drake London', 'ATL'), ('George Pickens', 'PIT'),
                ('Christian Kirk', 'JAX'), ('Courtland Sutton', 'DEN'), ('Tyler Lockett', 'SEA'),
                ('Diontae Johnson', 'CAR'), ('Jerry Jeudy', 'CLE'), ('Mike Williams', 'NYJ'),
                ('Marquise Brown', 'KC'), ('DeAndre Hopkins', 'KC'), ('Michael Pittman Jr.', 'IND'),
                ('Jordan Addison', 'MIN'), ('Rome Odunze', 'CHI'), ('Malik Nabers', 'NYG'),
                ('Brian Thomas Jr.', 'JAX'), ('Marvin Harrison Jr.', 'ARI'), ('Ladd McConkey', 'LAC'),
                ('Xavier Worthy', 'KC'), ('Keon Coleman', 'BUF'), ('Ja\'Lynn Polk', 'NE'),
                ('Adonai Mitchell', 'IND'), ('Roman Wilson', 'PIT'), ('Jalen Tolbert', 'DAL'),
                ('Curtis Samuel', 'BUF'), ('Darius Slayton', 'NYG'), ('Tyler Boyd', 'TEN'),
                ('Gabe Davis', 'JAX'), ('Rashod Bateman', 'BAL'), ('Van Jefferson', 'PIT'),
                ('Noah Brown', 'HOU'), ('KaVontae Turpin', 'DAL'), ('Khalil Shakir', 'BUF'),
                ('Wan\'Dale Robinson', 'NYG'), ('Elijah Moore', 'CLE'), ('Jahan Dotson', 'WAS'),
                ('Quentin Johnston', 'LAC'), ('Jaylen Wright', 'MIA'), ('Joshua Palmer', 'LAC'),
                ('Kendrick Bourne', 'NE'), ('JuJu Smith-Schuster', 'KC'), ('Allen Lazard', 'NYJ'),
                ('Nelson Agholor', 'BAL'), ('Tre Tucker', 'LV'), ('Tutu Atwell', 'LAR'),
                ('Cedric Tillman', 'CLE'), ('Tank Dell', 'HOU'), ('Marvin Mims Jr.', 'DEN'),
                ('K.J. Osborn', 'NE'), ('Treylon Burks', 'TEN'), ('DJ Turner', 'LV'),
                ('Mack Hollins', 'BUF'), ('Jalin Hyatt', 'NYG'), ('DeMario Douglas', 'NE'),
                ('Robert Woods', 'HOU'), ('Xavier Hutchinson', 'HOU'), ('Brandin Cooks', 'DAL'),
                ('River Cracraft', 'MIA'), ('Braxton Berrios', 'MIA'), ('Calvin Austin III', 'PIT'),
                ('John Metchie III', 'HOU'), ('Robbie Chosen', 'MIA'), ('David Bell', 'CLE'),
                ('Johnny Wilson', 'PHI'), ('Javon Baker', 'NE'), ('Luke McCaffrey', 'WAS')
            ],
            'TE': [
                ('Travis Kelce', 'KC'), ('Brock Bowers', 'LV'), ('George Kittle', 'SF'),
                ('Mark Andrews', 'BAL'), ('Trey McBride', 'ARI'), ('Sam LaPorta', 'DET'),
                ('Evan Engram', 'JAX'), ('T.J. Hockenson', 'MIN'), ('Kyle Pitts', 'ATL'),
                ('David Njoku', 'CLE'), ('Dalton Kincaid', 'BUF'), ('Dallas Goedert', 'PHI'),
                ('Isaiah Likely', 'BAL'), ('Tyler Conklin', 'NYJ'), ('Hunter Henry', 'NE')
            ]
        }
        
        created_counts = {}
        
        for position, target_count in target_counts.items():
            self.stdout.write(f'  Populating {position} players (target: {target_count})...')
            
            players_data = top_players_by_position.get(position, [])
            created_count = 0
            
            # If we need more players than we have in our list, repeat with variations
            while len(players_data) < target_count:
                # Add some backup/developmental players with variations
                base_players = top_players_by_position.get(position, [])[:10]
                for i, (name, team) in enumerate(base_players):
                    if len(players_data) >= target_count:
                        break
                    # Add backup version
                    backup_name = f"{name.split()[0]} {name.split()[-1]} Jr." if ' Jr.' not in name else f"{name} II"
                    players_data.append((backup_name, team))
            
            with transaction.atomic():
                for i, (name, team_abbr) in enumerate(players_data[:target_count]):
                    try:
                        team = NFLTeam.objects.get(team_abbreviation=team_abbr)
                        
                        # Create unique player_id
                        player_id = f"{position}_{team_abbr}_{i+1:03d}_{name.replace(' ', '_').replace('.', '').replace('\'', '')}"
                        
                        player, created = CompleteNFLPlayer.objects.get_or_create(
                            player_id=player_id,
                            defaults={
                                'first_name': name.split()[0],
                                'last_name': ' '.join(name.split()[1:]),
                                'full_name': name,
                                'team': team,
                                'position': position,
                                'jersey_number': (i + 1) % 99 + 1,
                                'status': 'active',
                                'fantasy_relevant': True,  # Will be refined later
                                'depth_chart_position': (i % 3) + 1,  # 1=starter, 2=backup, 3=third string
                                'years_pro': min(10, max(1, (i // 5) + 1)),
                                'age': 22 + (i // 3),
                                'weight': self._get_position_weight(position) + (i % 20) - 10,
                                'height': self._get_position_height(position),
                            }
                        )
                        
                        if created:
                            created_count += 1
                            
                    except NFLTeam.DoesNotExist:
                        self.stdout.write(f'    Warning: Team {team_abbr} not found for {name}')
                        continue
                    except Exception as e:
                        self.stdout.write(f'    Error creating player {name}: {e}')
                        continue
            
            created_counts[position] = created_count
            self.stdout.write(f'    Created {created_count} new {position} players')
        
        # Print summary
        total_created = sum(created_counts.values())
        self.stdout.write(f'  Total players created: {total_created}')

    def _get_position_weight(self, position: str) -> int:
        """Get typical weight for position"""
        weights = {
            'QB': 215,
            'RB': 210,
            'WR': 190,
            'TE': 250
        }
        return weights.get(position, 200)

    def _get_position_height(self, position: str) -> str:
        """Get typical height for position"""
        heights = {
            'QB': "6'2\"",
            'RB': "5'10\"",
            'WR': "6'0\"",
            'TE': "6'4\""
        }
        return heights.get(position, "6'0\"")

    def populate_season_statistics(self, season: int, target_counts: Dict[str, int]):
        """Populate season statistics for all players"""
        self.stdout.write(f'Populating season statistics for {season}...')
        
        created_count = 0
        players = CompleteNFLPlayer.objects.filter(fantasy_relevant=True)
        
        with transaction.atomic():
            for player in players:
                for week in range(1, 19):  # 18 weeks regular season
                    stats, created = SeasonStats.objects.get_or_create(
                        player=player,
                        season=season,
                        week=week,
                        defaults=self._generate_realistic_stats(player, week)
                    )
                    if created:
                        created_count += 1
        
        self.stdout.write(f'  Created {created_count} weekly stat records')

    def _generate_realistic_stats(self, player: CompleteNFLPlayer, week: int) -> Dict:
        """Generate realistic stats based on position and week"""
        import random
        
        base_stats = {
            'passing_attempts': 0, 'passing_completions': 0, 'passing_yards': 0,
            'passing_touchdowns': 0, 'interceptions': 0, 'sacks_taken': 0,
            'rushing_attempts': 0, 'rushing_yards': 0, 'rushing_touchdowns': 0,
            'fumbles': 0, 'targets': 0, 'receptions': 0, 'receiving_yards': 0,
            'receiving_touchdowns': 0, 'kick_return_yards': 0, 'punt_return_yards': 0,
            'fantasy_points_standard': 0.0, 'fantasy_points_half_ppr': 0.0,
            'fantasy_points_ppr': 0.0
        }
        
        # Week variance (some weeks better than others)
        week_modifier = 0.8 + (random.random() * 0.4)  # 0.8 to 1.2 multiplier
        
        if player.position == 'QB':
            # Starter vs backup stats
            if player.depth_chart_position == 1:  # Starter
                base_stats.update({
                    'passing_attempts': int(32 * week_modifier),
                    'passing_completions': int(22 * week_modifier),
                    'passing_yards': int(250 * week_modifier),
                    'passing_touchdowns': max(0, int(1.5 * week_modifier)),
                    'interceptions': 1 if random.random() < 0.3 else 0,
                    'rushing_yards': int(15 * week_modifier),
                    'rushing_touchdowns': 1 if random.random() < 0.2 else 0,
                })
            else:  # Backup QB
                base_stats.update({
                    'passing_attempts': int(5 * week_modifier) if random.random() < 0.3 else 0,
                    'passing_completions': int(3 * week_modifier) if base_stats['passing_attempts'] > 0 else 0,
                    'passing_yards': int(35 * week_modifier) if base_stats['passing_attempts'] > 0 else 0,
                })
        
        elif player.position == 'RB':
            if player.depth_chart_position == 1:  # Starting RB
                base_stats.update({
                    'rushing_attempts': int(18 * week_modifier),
                    'rushing_yards': int(75 * week_modifier),
                    'rushing_touchdowns': 1 if random.random() < 0.4 else 0,
                    'targets': int(4 * week_modifier),
                    'receptions': int(3 * week_modifier),
                    'receiving_yards': int(25 * week_modifier),
                    'receiving_touchdowns': 1 if random.random() < 0.15 else 0,
                })
            else:  # Backup RB
                base_stats.update({
                    'rushing_attempts': int(6 * week_modifier),
                    'rushing_yards': int(25 * week_modifier),
                    'rushing_touchdowns': 1 if random.random() < 0.2 else 0,
                    'targets': int(2 * week_modifier),
                    'receptions': int(1.5 * week_modifier),
                    'receiving_yards': int(10 * week_modifier),
                })
        
        elif player.position == 'WR':
            if player.depth_chart_position <= 2:  # WR1/WR2
                base_stats.update({
                    'targets': int(8 * week_modifier),
                    'receptions': int(5.5 * week_modifier),
                    'receiving_yards': int(70 * week_modifier),
                    'receiving_touchdowns': 1 if random.random() < 0.35 else 0,
                    'rushing_attempts': 1 if random.random() < 0.1 else 0,
                    'rushing_yards': int(8 * week_modifier) if base_stats['rushing_attempts'] > 0 else 0,
                })
            else:  # WR3+
                base_stats.update({
                    'targets': int(4 * week_modifier),
                    'receptions': int(2.5 * week_modifier),
                    'receiving_yards': int(30 * week_modifier),
                    'receiving_touchdowns': 1 if random.random() < 0.2 else 0,
                })
        
        elif player.position == 'TE':
            if player.depth_chart_position == 1:  # Starting TE
                base_stats.update({
                    'targets': int(6 * week_modifier),
                    'receptions': int(4 * week_modifier),
                    'receiving_yards': int(45 * week_modifier),
                    'receiving_touchdowns': 1 if random.random() < 0.3 else 0,
                })
            else:  # Backup TE
                base_stats.update({
                    'targets': int(2 * week_modifier),
                    'receptions': int(1.5 * week_modifier),
                    'receiving_yards': int(15 * week_modifier),
                    'receiving_touchdowns': 1 if random.random() < 0.15 else 0,
                })
        
        # Calculate fantasy points
        base_stats['fantasy_points_standard'] = self._calculate_fantasy_points(base_stats, 'standard')
        base_stats['fantasy_points_half_ppr'] = self._calculate_fantasy_points(base_stats, 'half_ppr')
        base_stats['fantasy_points_ppr'] = self._calculate_fantasy_points(base_stats, 'ppr')
        
        return base_stats

    def _calculate_fantasy_points(self, stats: Dict, scoring_format: str) -> float:
        """Calculate fantasy points based on stats and scoring format"""
        points = 0.0
        
        # Passing
        points += stats['passing_yards'] * 0.04  # 1 point per 25 yards
        points += stats['passing_touchdowns'] * 4
        points -= stats['interceptions'] * 2
        
        # Rushing
        points += stats['rushing_yards'] * 0.1  # 1 point per 10 yards
        points += stats['rushing_touchdowns'] * 6
        
        # Receiving
        points += stats['receiving_yards'] * 0.1  # 1 point per 10 yards
        points += stats['receiving_touchdowns'] * 6
        
        # PPR Bonus
        if scoring_format == 'ppr':
            points += stats['receptions'] * 1.0
        elif scoring_format == 'half_ppr':
            points += stats['receptions'] * 0.5
        
        # Fumbles
        points -= stats['fumbles'] * 2
        
        return round(points, 2)

    def setup_depth_charts(self, season: int):
        """Setup depth charts for all teams and positions"""
        self.stdout.write(f'Setting up depth charts for {season}...')
        
        created_count = 0
        teams = NFLTeam.objects.all()
        positions = ['QB', 'RB', 'WR', 'TE']
        
        with transaction.atomic():
            for team in teams:
                for position in positions:
                    players = CompleteNFLPlayer.objects.filter(
                        team=team, 
                        position=position,
                        status='active'
                    ).order_by('depth_chart_position', 'id')
                    
                    for week in range(1, 19):  # All 18 weeks
                        for depth_order, player in enumerate(players[:5], 1):  # Top 5 at each position
                            depth_chart, created = DepthChart.objects.get_or_create(
                                team=team,
                                position=position,
                                player=player,
                                week=week,
                                season=season,
                                defaults={'depth_order': depth_order}
                            )
                            if created:
                                created_count += 1
        
        self.stdout.write(f'  Created {created_count} depth chart entries')

    def mark_fantasy_relevant_players(self, target_counts: Dict[str, int]):
        """Mark the top players as fantasy relevant based on target counts"""
        self.stdout.write('Marking fantasy relevant players...')
        
        for position, count in target_counts.items():
            # Mark top players as fantasy relevant
            top_players = CompleteNFLPlayer.objects.filter(
                position=position,
                status='active'
            ).order_by('depth_chart_position', 'id')[:count]
            
            # First reset all players for this position
            CompleteNFLPlayer.objects.filter(position=position).update(fantasy_relevant=False)
            
            # Then mark the top ones as relevant
            player_ids = [p.id for p in top_players]
            CompleteNFLPlayer.objects.filter(id__in=player_ids).update(fantasy_relevant=True)
            
            self.stdout.write(f'  Marked top {count} {position} players as fantasy relevant')

    def print_database_summary(self):
        """Print summary of database contents"""
        self.stdout.write('\n' + '='*50)
        self.stdout.write('COMPREHENSIVE NFL DATABASE SUMMARY')
        self.stdout.write('='*50)
        
        # Team summary
        team_count = NFLTeam.objects.count()
        self.stdout.write(f'Total NFL Teams: {team_count}')
        
        # Player summary by position
        self.stdout.write('\nPLAYERS BY POSITION:')
        for position in ['QB', 'RB', 'WR', 'TE']:
            total_count = CompleteNFLPlayer.objects.filter(position=position).count()
            fantasy_count = CompleteNFLPlayer.objects.filter(
                position=position, 
                fantasy_relevant=True
            ).count()
            self.stdout.write(f'{position}: {fantasy_count} fantasy relevant / {total_count} total')
        
        # Stats summary
        total_stats = SeasonStats.objects.count()
        self.stdout.write(f'\nTotal Season Stat Records: {total_stats}')
        
        # Depth chart summary
        total_depth_entries = DepthChart.objects.count()
        self.stdout.write(f'Total Depth Chart Entries: {total_depth_entries}')
        
        # Fantasy relevant totals
        total_fantasy_relevant = CompleteNFLPlayer.objects.filter(fantasy_relevant=True).count()
        self.stdout.write(f'\nTotal Fantasy Relevant Players: {total_fantasy_relevant}')
        
        self.stdout.write('='*50)