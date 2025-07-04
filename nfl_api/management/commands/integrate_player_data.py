"""
Django management command to integrate existing high-quality player data
with the comprehensive NFL roster system
"""
import os
import sys
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from nfl_api.models import (
    Player, CompleteNFLPlayer, NFLTeam, GameResult, SeasonStats, 
    InjuryReport
)

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Integrate existing high-quality player data with comprehensive NFL roster'

    def add_arguments(self, parser):
        parser.add_argument(
            '--season',
            type=int,
            default=2024,
            help='NFL season to integrate (default: 2024)'
        )
        parser.add_argument(
            '--preserve-existing',
            action='store_true',
            help='Preserve existing CompleteNFLPlayer data where possible'
        )

    def handle(self, *args, **options):
        season = options['season']
        preserve_existing = options['preserve_existing']

        self.stdout.write(
            self.style.SUCCESS(f'Integrating player data for {season} season...')
        )

        try:
            # 1. Analyze current data state
            self.analyze_current_data()
            
            # 2. Map original players to comprehensive roster
            self.map_original_to_comprehensive(season, preserve_existing)
            
            # 3. Transfer high-quality game results to SeasonStats
            self.transfer_game_results_to_season_stats(season)
            
            # 4. Mark top players as fantasy relevant based on actual performance
            self.update_fantasy_relevance_from_performance()
            
            # 5. Optimize the combined dataset
            self.optimize_combined_dataset()
            
            self.stdout.write(
                self.style.SUCCESS('Player data integration completed!')
            )
            
            # Print final summary
            self.print_integration_summary()
            
        except Exception as e:
            logger.error(f'Error in player data integration: {e}')
            self.stdout.write(
                self.style.ERROR(f'Integration failed: {e}')
            )

    def analyze_current_data(self):
        """Analyze the current state of player data"""
        self.stdout.write('Analyzing current data state...')
        
        original_players = Player.objects.count()
        comprehensive_players = CompleteNFLPlayer.objects.count()
        game_results = GameResult.objects.count()
        season_stats = SeasonStats.objects.count()
        
        self.stdout.write(f'  Original Players: {original_players}')
        self.stdout.write(f'  Comprehensive Players: {comprehensive_players}')
        self.stdout.write(f'  Game Results: {game_results}')
        self.stdout.write(f'  Season Stats: {season_stats}')
        
        # Check for overlapping players
        overlap_count = 0
        for orig_player in Player.objects.all():
            matching_comprehensive = CompleteNFLPlayer.objects.filter(
                full_name__icontains=orig_player.name,
                team__team_abbreviation=orig_player.team,
                position=orig_player.position
            ).first()
            if matching_comprehensive:
                overlap_count += 1
        
        self.stdout.write(f'  Potential overlaps: {overlap_count}')

    def map_original_to_comprehensive(self, season: int, preserve_existing: bool):
        """Map original high-quality players to comprehensive roster"""
        self.stdout.write('Mapping original players to comprehensive roster...')
        
        mapped_count = 0
        created_count = 0
        
        for orig_player in Player.objects.filter(season=season):
            try:
                # Try to find matching comprehensive player
                team = NFLTeam.objects.get(team_abbreviation=orig_player.team)
                
                # Look for exact or close matches
                matching_player = CompleteNFLPlayer.objects.filter(
                    team=team,
                    position=orig_player.position,
                    full_name__icontains=orig_player.name.split()[0]  # Match by first name
                ).first()
                
                if matching_player:
                    # Update comprehensive player with original data quality
                    if not preserve_existing or not matching_player.fantasy_relevant:
                        matching_player.full_name = orig_player.name
                        matching_player.fantasy_relevant = True
                        matching_player.depth_chart_position = 1  # High-quality players are likely starters
                        matching_player.status = 'active' if orig_player.active else 'injured'
                        matching_player.last_roster_update = timezone.now()
                        matching_player.save()
                        mapped_count += 1
                else:
                    # Create new comprehensive player based on original
                    name_parts = orig_player.name.split()
                    first_name = name_parts[0]
                    last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''
                    
                    player_id = f"ORIG_{orig_player.team}_{orig_player.position}_{orig_player.id}"
                    
                    new_player = CompleteNFLPlayer.objects.create(
                        player_id=player_id,
                        first_name=first_name,
                        last_name=last_name,
                        full_name=orig_player.name,
                        team=team,
                        position=orig_player.position,
                        status='active' if orig_player.active else 'injured',
                        fantasy_relevant=True,
                        depth_chart_position=1,  # Original players are high-quality
                        years_pro=self._estimate_years_pro_from_performance(orig_player),
                        age=self._estimate_age_from_position(orig_player.position),
                        weight=self._get_position_weight(orig_player.position),
                        height=self._get_position_height(orig_player.position),
                        last_roster_update=timezone.now()
                    )
                    created_count += 1
                    
            except NFLTeam.DoesNotExist:
                self.stdout.write(f'  Warning: Team {orig_player.team} not found for {orig_player.name}')
                continue
            except Exception as e:
                self.stdout.write(f'  Error processing {orig_player.name}: {e}')
                continue
        
        self.stdout.write(f'  Mapped {mapped_count} existing players')
        self.stdout.write(f'  Created {created_count} new comprehensive players')

    def transfer_game_results_to_season_stats(self, season: int):
        """Transfer high-quality GameResult data to SeasonStats"""
        self.stdout.write('Transferring game results to season stats...')
        
        transferred_count = 0
        
        for game_result in GameResult.objects.filter(season=season):
            try:
                # Find corresponding comprehensive player
                team = NFLTeam.objects.get(team_abbreviation=game_result.team)
                comprehensive_player = CompleteNFLPlayer.objects.filter(
                    team=team,
                    position=game_result.position,
                    full_name__icontains=game_result.player_name.split()[0]
                ).first()
                
                if not comprehensive_player:
                    # Try different matching approaches
                    comprehensive_player = CompleteNFLPlayer.objects.filter(
                        team=team,
                        position=game_result.position,
                        fantasy_relevant=True
                    ).first()
                
                if comprehensive_player:
                    # Create or update SeasonStats with GameResult data
                    season_stats, created = SeasonStats.objects.update_or_create(
                        player=comprehensive_player,
                        season=game_result.season,
                        week=game_result.week,
                        defaults={
                            'passing_attempts': game_result.passing_attempts,
                            'passing_completions': game_result.passing_completions,
                            'passing_yards': game_result.passing_yards,
                            'passing_touchdowns': game_result.passing_tds,
                            'interceptions': game_result.interceptions,
                            'rushing_attempts': game_result.rushing_attempts,
                            'rushing_yards': game_result.rushing_yards,
                            'rushing_touchdowns': game_result.rushing_tds,
                            'targets': game_result.targets,
                            'receptions': game_result.receptions,
                            'receiving_yards': game_result.receiving_yards,
                            'receiving_touchdowns': game_result.receiving_tds,
                            'fantasy_points_standard': game_result.fantasy_points_standard or 0.0,
                            'fantasy_points_half_ppr': game_result.fantasy_points_half_ppr or 0.0,
                            'fantasy_points_ppr': game_result.fantasy_points_ppr or 0.0,
                        }
                    )
                    
                    if created or True:  # Always update for better data quality
                        transferred_count += 1
                        
            except NFLTeam.DoesNotExist:
                continue
            except Exception as e:
                self.stdout.write(f'  Error transferring {game_result.player_name}: {e}')
                continue
        
        self.stdout.write(f'  Transferred {transferred_count} game results')

    def update_fantasy_relevance_from_performance(self):
        """Update fantasy relevance based on actual performance data"""
        self.stdout.write('Updating fantasy relevance from performance...')
        
        updated_count = 0
        
        # Find players with high-quality performance data
        for player in CompleteNFLPlayer.objects.all():
            has_performance_data = SeasonStats.objects.filter(
                player=player,
                fantasy_points_ppr__gt=5.0  # Has meaningful fantasy production
            ).exists()
            
            if has_performance_data and not player.fantasy_relevant:
                player.fantasy_relevant = True
                player.depth_chart_position = min(player.depth_chart_position, 2)  # Promote to at least 2nd string
                player.save()
                updated_count += 1
        
        self.stdout.write(f'  Updated fantasy relevance for {updated_count} players')

    def optimize_combined_dataset(self):
        """Optimize the combined dataset for better performance"""
        self.stdout.write('Optimizing combined dataset...')
        
        # Remove duplicate or low-quality entries
        duplicates_removed = 0
        
        # Group by team and position to find duplicates
        teams = NFLTeam.objects.all()
        for team in teams:
            for position in ['QB', 'RB', 'WR', 'TE']:
                players = CompleteNFLPlayer.objects.filter(
                    team=team,
                    position=position,
                    fantasy_relevant=True
                ).order_by('depth_chart_position', '-id')
                
                # Keep reasonable numbers per position
                max_players = {'QB': 3, 'RB': 4, 'WR': 6, 'TE': 3}.get(position, 3)
                
                excess_players = players[max_players:]
                for player in excess_players:
                    # Only remove if they don't have performance data
                    if not SeasonStats.objects.filter(
                        player=player,
                        fantasy_points_ppr__gt=1.0
                    ).exists():
                        player.fantasy_relevant = False
                        player.save()
                        duplicates_removed += 1
        
        self.stdout.write(f'  Optimized {duplicates_removed} player entries')

    def _estimate_years_pro_from_performance(self, player: Player) -> int:
        """Estimate years pro based on performance consistency"""
        # Players with consistent data likely have more experience
        game_count = GameResult.objects.filter(
            player_name=player.name,
            season=player.season
        ).count()
        
        if game_count >= 15:
            return 4  # Veteran with full season
        elif game_count >= 10:
            return 2  # Experienced player
        else:
            return 1  # Rookie or limited experience

    def _estimate_age_from_position(self, position: str) -> int:
        """Estimate age based on position"""
        base_ages = {'QB': 27, 'RB': 25, 'WR': 26, 'TE': 27}
        return base_ages.get(position, 26)

    def _get_position_weight(self, position: str) -> int:
        """Get typical weight for position"""
        weights = {'QB': 215, 'RB': 210, 'WR': 190, 'TE': 250}
        return weights.get(position, 200)

    def _get_position_height(self, position: str) -> str:
        """Get typical height for position"""
        heights = {'QB': "6'2\"", 'RB': "5'10\"", 'WR': "6'0\"", 'TE': "6'4\""}
        return heights.get(position, "6'0\"")

    def print_integration_summary(self):
        """Print final integration summary"""
        self.stdout.write('\n' + '='*60)
        self.stdout.write('PLAYER DATA INTEGRATION SUMMARY')
        self.stdout.write('='*60)
        
        # Final counts
        original_players = Player.objects.count()
        comprehensive_players = CompleteNFLPlayer.objects.count()
        fantasy_relevant = CompleteNFLPlayer.objects.filter(fantasy_relevant=True).count()
        season_stats = SeasonStats.objects.count()
        game_results = GameResult.objects.count()
        
        self.stdout.write(f'Original Players (high-quality): {original_players}')
        self.stdout.write(f'Comprehensive Players (all rosters): {comprehensive_players}')
        self.stdout.write(f'Fantasy Relevant Players: {fantasy_relevant}')
        self.stdout.write(f'Season Statistics: {season_stats}')
        self.stdout.write(f'Game Results (original): {game_results}')
        
        # Quality breakdown
        self.stdout.write('\nQUALITY BREAKDOWN:')
        for position in ['QB', 'RB', 'WR', 'TE']:
            orig_count = Player.objects.filter(position=position).count()
            comp_count = CompleteNFLPlayer.objects.filter(
                position=position, 
                fantasy_relevant=True
            ).count()
            with_stats = CompleteNFLPlayer.objects.filter(
                position=position,
                fantasy_relevant=True,
                season_stats__fantasy_points_ppr__gt=1.0
            ).distinct().count()
            
            self.stdout.write(f'{position}: {orig_count} original, {comp_count} fantasy, {with_stats} with stats')
        
        self.stdout.write('\nSUCCESS: Integrated high-quality player data with comprehensive rosters!')
        self.stdout.write('='*60)