from django.db import models
from django.utils import timezone


class Player(models.Model):
    """Django Player model converted from Flask SQLAlchemy"""
    name = models.CharField(max_length=100)
    team = models.CharField(max_length=10)
    position = models.CharField(max_length=10)
    season = models.IntegerField()
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'players'
        indexes = [
            models.Index(fields=['position', 'season']),
            models.Index(fields=['team', 'season']),
        ]

    def __str__(self):
        return f"{self.name} ({self.team} - {self.position})"


class Prediction(models.Model):
    """Django Prediction model converted from Flask SQLAlchemy"""
    player_id = models.IntegerField()
    player_name = models.CharField(max_length=100)
    team = models.CharField(max_length=10)
    position = models.CharField(max_length=10)
    week = models.IntegerField()
    season = models.IntegerField()
    predicted_points = models.FloatField()
    confidence = models.FloatField()
    scoring_format = models.CharField(max_length=20, default='half_ppr')
    model_version = models.CharField(max_length=50, default='v1.0')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'predictions'
        indexes = [
            models.Index(fields=['position', 'week', 'season']),
            models.Index(fields=['player_name', 'week', 'season']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.player_name} Week {self.week}: {self.predicted_points}pts"


class GameResult(models.Model):
    """Django Game Results model converted from Flask SQLAlchemy"""
    player_id = models.IntegerField()
    player_name = models.CharField(max_length=100)
    team = models.CharField(max_length=10)
    position = models.CharField(max_length=10)
    week = models.IntegerField()
    season = models.IntegerField()
    actual_points = models.FloatField()
    fantasy_points_ppr = models.FloatField(null=True, blank=True)
    fantasy_points_half_ppr = models.FloatField(null=True, blank=True)
    fantasy_points_standard = models.FloatField(null=True, blank=True)
    
    # Individual stats
    passing_yards = models.IntegerField(default=0)
    passing_tds = models.IntegerField(default=0)
    passing_attempts = models.IntegerField(default=0)
    passing_completions = models.IntegerField(default=0)
    interceptions = models.IntegerField(default=0)
    
    rushing_yards = models.IntegerField(default=0)
    rushing_tds = models.IntegerField(default=0)
    rushing_attempts = models.IntegerField(default=0)
    
    receiving_yards = models.IntegerField(default=0)
    receiving_tds = models.IntegerField(default=0)
    receptions = models.IntegerField(default=0)
    targets = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'game_results'
        indexes = [
            models.Index(fields=['player_name', 'week', 'season']),
            models.Index(fields=['position', 'week', 'season']),
        ]

    def __str__(self):
        return f"{self.player_name} Week {self.week}: {self.actual_points}pts"


class InjuryReport(models.Model):
    """Django Injury Report model converted from Flask SQLAlchemy"""
    
    INJURY_STATUS_CHOICES = [
        ('healthy', 'Healthy'),
        ('questionable', 'Questionable'),
        ('doubtful', 'Doubtful'),
        ('out', 'Out'),
        ('ir', 'Injured Reserve'),
    ]
    
    player_id = models.IntegerField()
    player_name = models.CharField(max_length=100)
    team = models.CharField(max_length=10)
    position = models.CharField(max_length=10)
    week = models.IntegerField()
    season = models.IntegerField()
    injury_status = models.CharField(max_length=20, choices=INJURY_STATUS_CHOICES, null=True, blank=True)
    injury_description = models.TextField(null=True, blank=True)
    date_reported = models.DateTimeField(default=timezone.now)
    source = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = 'injury_reports'
        indexes = [
            models.Index(fields=['player_name', 'week', 'season']),
            models.Index(fields=['injury_status', 'week', 'season']),
            models.Index(fields=['date_reported']),
        ]

    def __str__(self):
        return f"{self.player_name} - {self.injury_status} (Week {self.week})"


# Separate NFL Team Roster Database Models
class NFLTeam(models.Model):
    """Complete NFL team information"""
    team_abbreviation = models.CharField(max_length=3, primary_key=True)
    full_name = models.CharField(max_length=100)
    city = models.CharField(max_length=50)
    conference = models.CharField(max_length=3, choices=[('AFC', 'AFC'), ('NFC', 'NFC')])
    division = models.CharField(max_length=10)
    stadium = models.CharField(max_length=100, null=True, blank=True)
    head_coach = models.CharField(max_length=100, null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'nfl_teams'

    def __str__(self):
        return f"{self.full_name} ({self.team_abbreviation})"


class CompleteNFLPlayer(models.Model):
    """Comprehensive NFL player database - all players on all teams"""
    player_id = models.CharField(max_length=20, unique=True)  # External API player ID
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    full_name = models.CharField(max_length=100)
    team = models.ForeignKey(NFLTeam, on_delete=models.CASCADE, related_name='players')
    position = models.CharField(max_length=10)
    jersey_number = models.IntegerField(null=True, blank=True)
    
    # Physical attributes
    height = models.CharField(max_length=10, null=True, blank=True)  # e.g., "6'2"
    weight = models.IntegerField(null=True, blank=True)
    age = models.IntegerField(null=True, blank=True)
    years_pro = models.IntegerField(null=True, blank=True)
    
    # Status information
    status = models.CharField(max_length=20, choices=[
        ('active', 'Active'),
        ('injured', 'Injured'),
        ('suspended', 'Suspended'),
        ('practice_squad', 'Practice Squad'),
        ('ir', 'Injured Reserve'),
        ('retired', 'Retired'),
        ('free_agent', 'Free Agent'),
    ], default='active')
    
    fantasy_relevant = models.BooleanField(default=False)  # Flag for fantasy relevance
    depth_chart_position = models.IntegerField(null=True, blank=True)  # 1 = starter, 2 = backup, etc.
    
    # College and draft info
    college = models.CharField(max_length=100, null=True, blank=True)
    draft_year = models.IntegerField(null=True, blank=True)
    draft_round = models.IntegerField(null=True, blank=True)
    draft_pick = models.IntegerField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    last_roster_update = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'complete_nfl_players'
        indexes = [
            models.Index(fields=['team', 'position']),
            models.Index(fields=['position', 'fantasy_relevant']),
            models.Index(fields=['status']),
            models.Index(fields=['depth_chart_position']),
            models.Index(fields=['last_roster_update']),
        ]

    def __str__(self):
        return f"{self.full_name} - {self.team.team_abbreviation} {self.position}"


class PlayerTransaction(models.Model):
    """Track all player transactions (trades, signings, cuts, etc.)"""
    TRANSACTION_TYPES = [
        ('trade', 'Trade'),
        ('signing', 'Free Agent Signing'),
        ('waiver_claim', 'Waiver Claim'),
        ('release', 'Release/Cut'),
        ('ir_placement', 'Injured Reserve Placement'),
        ('ir_return', 'Return from IR'),
        ('suspension', 'Suspension'),
        ('activation', 'Activation'),
        ('practice_squad', 'Practice Squad'),
        ('futures_contract', 'Futures Contract'),
        ('retirement', 'Retirement'),
    ]
    
    player = models.ForeignKey(CompleteNFLPlayer, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    from_team = models.ForeignKey(NFLTeam, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions_from')
    to_team = models.ForeignKey(NFLTeam, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions_to')
    
    transaction_date = models.DateTimeField()
    details = models.TextField(null=True, blank=True)  # Additional transaction details
    source = models.CharField(max_length=100, null=True, blank=True)  # News source
    
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'player_transactions'
        indexes = [
            models.Index(fields=['transaction_date']),
            models.Index(fields=['transaction_type']),
            models.Index(fields=['player', 'transaction_date']),
        ]

    def __str__(self):
        return f"{self.player.full_name} - {self.get_transaction_type_display()} ({self.transaction_date.date()})"


class DepthChart(models.Model):
    """Track team depth charts by position"""
    team = models.ForeignKey(NFLTeam, on_delete=models.CASCADE, related_name='depth_charts')
    position = models.CharField(max_length=10)
    player = models.ForeignKey(CompleteNFLPlayer, on_delete=models.CASCADE)
    depth_order = models.IntegerField()  # 1 = starter, 2 = backup, etc.
    week = models.IntegerField()
    season = models.IntegerField()
    
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'depth_charts'
        unique_together = ['team', 'position', 'player', 'week', 'season']
        indexes = [
            models.Index(fields=['team', 'position', 'week', 'season']),
            models.Index(fields=['depth_order']),
        ]

    def __str__(self):
        return f"{self.team.team_abbreviation} {self.position} #{self.depth_order}: {self.player.full_name}"


class SeasonStats(models.Model):
    """Comprehensive season statistics for all players"""
    player = models.ForeignKey(CompleteNFLPlayer, on_delete=models.CASCADE, related_name='season_stats')
    season = models.IntegerField()
    week = models.IntegerField()
    
    # Passing stats
    passing_attempts = models.IntegerField(default=0)
    passing_completions = models.IntegerField(default=0)
    passing_yards = models.IntegerField(default=0)
    passing_touchdowns = models.IntegerField(default=0)
    interceptions = models.IntegerField(default=0)
    sacks_taken = models.IntegerField(default=0)
    
    # Rushing stats
    rushing_attempts = models.IntegerField(default=0)
    rushing_yards = models.IntegerField(default=0)
    rushing_touchdowns = models.IntegerField(default=0)
    fumbles = models.IntegerField(default=0)
    
    # Receiving stats
    targets = models.IntegerField(default=0)
    receptions = models.IntegerField(default=0)
    receiving_yards = models.IntegerField(default=0)
    receiving_touchdowns = models.IntegerField(default=0)
    
    # Special teams
    kick_return_yards = models.IntegerField(default=0)
    punt_return_yards = models.IntegerField(default=0)
    
    # Fantasy points (calculated)
    fantasy_points_standard = models.FloatField(default=0.0)
    fantasy_points_half_ppr = models.FloatField(default=0.0)
    fantasy_points_ppr = models.FloatField(default=0.0)
    
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'season_stats'
        unique_together = ['player', 'season', 'week']
        indexes = [
            models.Index(fields=['player', 'season']),
            models.Index(fields=['season', 'week']),
        ]

    def __str__(self):
        return f"{self.player.full_name} - Week {self.week}, {self.season}"