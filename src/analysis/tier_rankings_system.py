#!/usr/bin/env python3
"""
Tier Rankings System
Boris Chen-style tier-based player rankings with statistical clustering
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Tuple
from sklearn.cluster import KMeans, AgglomerativeClustering
from sklearn.preprocessing import StandardScaler
from scipy import stats
from scipy.cluster.hierarchy import dendrogram, linkage, fcluster
from enum import Enum
import matplotlib.pyplot as plt
import seaborn as sns

logger = logging.getLogger(__name__)

class TierMethod(Enum):
    """Methods for tier calculation"""
    STATISTICAL_GAPS = "statistical_gaps"
    KMEANS_CLUSTERING = "kmeans_clustering"
    HIERARCHICAL_CLUSTERING = "hierarchical_clustering"
    EXPERT_CONSENSUS = "expert_consensus"
    HYBRID_APPROACH = "hybrid_approach"

class TierQuality(Enum):
    """Quality levels for tier separations"""
    EXCELLENT = "excellent"   # Very clear separation
    GOOD = "good"            # Clear separation
    FAIR = "fair"            # Moderate separation
    POOR = "poor"            # Weak separation

@dataclass
class PlayerTierData:
    """Individual player tier data"""
    player_id: int
    player_name: str
    position: str
    tier: int
    tier_rank: int  # Rank within tier
    overall_rank: int
    
    # Scoring data
    projected_points: float
    floor_points: float
    ceiling_points: float
    confidence: float
    
    # Tier analysis
    tier_gap_above: Optional[float] = None  # Gap to player above
    tier_gap_below: Optional[float] = None  # Gap to player below
    tier_strength: float = 0.0  # How well player fits in tier
    
    # Visual properties
    tier_color: str = "#000000"
    display_priority: int = 0

@dataclass
class TierDefinition:
    """Definition of a player tier"""
    tier_number: int
    position: str
    tier_name: str  # e.g., "Elite", "High-End RB1", etc.
    
    # Players in tier
    players: List[PlayerTierData]
    player_count: int
    
    # Statistical properties
    tier_mean: float
    tier_std: float
    tier_min: float
    tier_max: float
    
    # Separation analysis
    gap_to_next_tier: Optional[float] = None
    gap_significance: float = 0.0  # Statistical significance of gap
    tier_quality: TierQuality = TierQuality.FAIR
    
    # Visual properties
    tier_color: str = "#808080"
    recommended_draft_rounds: List[int] = None

@dataclass
class TierAnalysisResult:
    """Complete tier analysis result"""
    position: str
    analysis_method: TierMethod
    total_players: int
    total_tiers: int
    
    # Tier definitions
    tiers: List[TierDefinition]
    
    # Analysis quality
    overall_tier_quality: float  # 0-1 score
    separation_clarity: float   # How clear tier separations are
    
    # Statistics
    largest_gap: float
    smallest_gap: float
    average_tier_size: float
    
    # Recommendations
    draft_strategy_notes: List[str]
    tier_break_points: List[float]

class TierRankingsSystem:
    """
    Boris Chen-style tier rankings system with advanced statistical clustering
    """
    
    def __init__(self):
        """Initialize tier rankings system"""
        self.logger = logging.getLogger(__name__)
        
        # Position-specific tier configurations
        self.position_tier_configs = {
            'QB': {
                'expected_tiers': 5,
                'tier_names': ['Elite QB1', 'High-End QB1', 'Mid-Tier QB1', 'QB2/Streamer', 'Backup QB'],
                'typical_tier_sizes': [3, 4, 5, 8, 12],
                'draft_rounds': [[1, 2], [3, 4], [5, 7], [8, 12], [13, 18]]
            },
            'RB': {
                'expected_tiers': 6,
                'tier_names': ['Elite RB1', 'High-End RB1', 'Mid-Tier RB1', 'Low-End RB1/High RB2', 'Mid-Tier RB2', 'Flex/Handcuff'],
                'typical_tier_sizes': [4, 6, 8, 10, 12, 20],
                'draft_rounds': [[1, 2], [2, 3], [3, 5], [5, 7], [7, 10], [10, 18]]
            },
            'WR': {
                'expected_tiers': 6,
                'tier_names': ['Elite WR1', 'High-End WR1', 'Mid-Tier WR1', 'Low-End WR1/High WR2', 'Mid-Tier WR2', 'Flex/WR3'],
                'typical_tier_sizes': [5, 8, 10, 12, 15, 25],
                'draft_rounds': [[1, 2], [2, 3], [3, 5], [5, 7], [7, 10], [10, 18]]
            },
            'TE': {
                'expected_tiers': 4,
                'tier_names': ['Elite TE1', 'High-End TE1', 'Mid-Tier TE1/TE2', 'Streamer/Backup'],
                'typical_tier_sizes': [3, 5, 8, 16],
                'draft_rounds': [[2, 4], [5, 7], [8, 12], [13, 18]]
            }
        }
        
        # Color schemes for tier visualization
        self.tier_colors = [
            '#8B0000',  # Dark Red (Elite)
            '#DC143C',  # Crimson (High-End)
            '#FF6347',  # Tomato (Mid-Tier)
            '#FFA500',  # Orange (Low-End)
            '#FFD700',  # Gold (Decent)
            '#90EE90',  # Light Green (Streamers)
            '#D3D3D3'   # Light Gray (Deep options)
        ]
        
        self.logger.info("Tier Rankings System initialized")
    
    def create_tier_rankings(self, player_data: List[Dict[str, Any]], position: str,
                           method: TierMethod = TierMethod.HYBRID_APPROACH) -> TierAnalysisResult:
        """
        Create tier-based rankings for a position
        
        Args:
            player_data: List of player dictionaries with scoring data
            position: Position to analyze
            method: Tier calculation method
            
        Returns:
            TierAnalysisResult with complete tier analysis
        """
        try:
            self.logger.info(f"Creating tier rankings for {position} using {method.value}")
            
            if not player_data:
                raise ValueError(f"No player data provided for {position}")
            
            # Convert to DataFrame for easier manipulation
            df = pd.DataFrame(player_data)
            
            # Ensure required columns exist
            required_cols = ['player_name', 'projected_points']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                raise ValueError(f"Missing required columns: {missing_cols}")
            
            # Sort by projected points (descending)
            df = df.sort_values('projected_points', ascending=False).reset_index(drop=True)
            
            # Calculate tiers based on method
            if method == TierMethod.STATISTICAL_GAPS:
                tier_assignments = self._calculate_statistical_gap_tiers(df, position)
            elif method == TierMethod.KMEANS_CLUSTERING:
                tier_assignments = self._calculate_kmeans_tiers(df, position)
            elif method == TierMethod.HIERARCHICAL_CLUSTERING:
                tier_assignments = self._calculate_hierarchical_tiers(df, position)
            elif method == TierMethod.HYBRID_APPROACH:
                tier_assignments = self._calculate_hybrid_tiers(df, position)
            else:
                tier_assignments = self._calculate_statistical_gap_tiers(df, position)
            
            # Create tier definitions
            tiers = self._create_tier_definitions(df, tier_assignments, position)
            
            # Calculate tier quality metrics
            overall_quality, separation_clarity = self._calculate_tier_quality(tiers)
            
            # Generate tier statistics
            tier_stats = self._calculate_tier_statistics(tiers)
            
            # Generate draft strategy notes
            draft_notes = self._generate_draft_strategy_notes(tiers, position)
            
            # Calculate tier break points
            break_points = self._calculate_tier_break_points(tiers)
            
            return TierAnalysisResult(
                position=position,
                analysis_method=method,
                total_players=len(player_data),
                total_tiers=len(tiers),
                tiers=tiers,
                overall_tier_quality=overall_quality,
                separation_clarity=separation_clarity,
                largest_gap=tier_stats['largest_gap'],
                smallest_gap=tier_stats['smallest_gap'],
                average_tier_size=tier_stats['average_tier_size'],
                draft_strategy_notes=draft_notes,
                tier_break_points=break_points
            )
            
        except Exception as e:
            self.logger.error(f"Error creating tier rankings for {position}: {e}")
            raise
    
    def _calculate_statistical_gap_tiers(self, df: pd.DataFrame, position: str) -> List[int]:
        """Calculate tiers based on statistical gaps in projections"""
        try:
            projections = df['projected_points'].values
            tier_assignments = [1] * len(projections)
            
            if len(projections) < 3:
                return tier_assignments
            
            # Calculate gaps between consecutive players
            gaps = []
            for i in range(len(projections) - 1):
                gap = projections[i] - projections[i + 1]
                gaps.append(gap)
            
            gaps = np.array(gaps)
            
            # Find statistically significant gaps
            if len(gaps) > 0:
                gap_mean = np.mean(gaps)
                gap_std = np.std(gaps)
                
                # Threshold for significant gap (1.5 standard deviations above mean)
                threshold = gap_mean + (1.5 * gap_std)
                
                current_tier = 1
                for i, gap in enumerate(gaps):
                    if gap > threshold:
                        current_tier += 1
                    
                    # Assign tier to next player
                    if i + 1 < len(tier_assignments):
                        tier_assignments[i + 1] = current_tier
            
            # Limit tiers to reasonable number for position
            max_tiers = self.position_tier_configs.get(position, {}).get('expected_tiers', 5)
            if max(tier_assignments) > max_tiers:
                # Consolidate lower tiers
                for i in range(len(tier_assignments)):
                    if tier_assignments[i] > max_tiers:
                        tier_assignments[i] = max_tiers
            
            return tier_assignments
            
        except Exception as e:
            self.logger.error(f"Error calculating statistical gap tiers: {e}")
            return [1] * len(df)
    
    def _calculate_kmeans_tiers(self, df: pd.DataFrame, position: str) -> List[int]:
        """Calculate tiers using K-means clustering"""
        try:
            projections = df['projected_points'].values.reshape(-1, 1)
            
            # Get expected number of tiers for position
            n_tiers = self.position_tier_configs.get(position, {}).get('expected_tiers', 5)
            n_tiers = min(n_tiers, len(projections))
            
            if n_tiers < 2:
                return [1] * len(projections)
            
            # Apply K-means clustering
            kmeans = KMeans(n_clusters=n_tiers, random_state=42, n_init=10)
            cluster_labels = kmeans.fit_predict(projections)
            
            # Map cluster labels to tier numbers (highest projection = tier 1)
            cluster_means = []
            for i in range(n_tiers):
                cluster_indices = np.where(cluster_labels == i)[0]
                if len(cluster_indices) > 0:
                    cluster_mean = np.mean(projections[cluster_indices])
                    cluster_means.append((i, cluster_mean))
            
            # Sort clusters by mean projection (descending)
            cluster_means.sort(key=lambda x: x[1], reverse=True)
            
            # Create mapping from cluster label to tier number
            cluster_to_tier = {}
            for tier_num, (cluster_label, _) in enumerate(cluster_means, 1):
                cluster_to_tier[cluster_label] = tier_num
            
            # Convert cluster labels to tier assignments
            tier_assignments = [cluster_to_tier[label] for label in cluster_labels]
            
            return tier_assignments
            
        except Exception as e:
            self.logger.error(f"Error calculating K-means tiers: {e}")
            return [1] * len(df)
    
    def _calculate_hierarchical_tiers(self, df: pd.DataFrame, position: str) -> List[int]:
        """Calculate tiers using hierarchical clustering"""
        try:
            projections = df['projected_points'].values.reshape(-1, 1)
            
            if len(projections) < 2:
                return [1] * len(projections)
            
            # Perform hierarchical clustering
            linkage_matrix = linkage(projections, method='ward')
            
            # Get expected number of tiers
            n_tiers = self.position_tier_configs.get(position, {}).get('expected_tiers', 5)
            n_tiers = min(n_tiers, len(projections))
            
            # Get cluster assignments
            cluster_labels = fcluster(linkage_matrix, n_tiers, criterion='maxclust')
            
            # Map to tier numbers (same logic as K-means)
            cluster_means = []
            for i in range(1, n_tiers + 1):
                cluster_indices = np.where(cluster_labels == i)[0]
                if len(cluster_indices) > 0:
                    cluster_mean = np.mean(projections[cluster_indices])
                    cluster_means.append((i, cluster_mean))
            
            cluster_means.sort(key=lambda x: x[1], reverse=True)
            
            cluster_to_tier = {}
            for tier_num, (cluster_label, _) in enumerate(cluster_means, 1):
                cluster_to_tier[cluster_label] = tier_num
            
            tier_assignments = [cluster_to_tier[label] for label in cluster_labels]
            
            return tier_assignments
            
        except Exception as e:
            self.logger.error(f"Error calculating hierarchical tiers: {e}")
            return [1] * len(df)
    
    def _calculate_hybrid_tiers(self, df: pd.DataFrame, position: str) -> List[int]:
        """Calculate tiers using hybrid approach (statistical gaps + clustering validation)"""
        try:
            # Start with statistical gaps
            gap_tiers = self._calculate_statistical_gap_tiers(df, position)
            
            # Validate with K-means clustering
            kmeans_tiers = self._calculate_kmeans_tiers(df, position)
            
            # Combine approaches - use gap tiers but validate against clustering
            final_tiers = gap_tiers.copy()
            
            # Check for agreement between methods
            agreement_score = np.mean([1 if gap_tiers[i] == kmeans_tiers[i] else 0 
                                     for i in range(len(gap_tiers))])
            
            # If low agreement, blend the approaches
            if agreement_score < 0.7:
                self.logger.debug(f"Low agreement ({agreement_score:.2f}) between methods, blending")
                
                # Use clustering to refine gap-based tiers
                for i in range(len(final_tiers)):
                    gap_tier = gap_tiers[i]
                    kmeans_tier = kmeans_tiers[i]
                    
                    # If methods disagree significantly, use average
                    if abs(gap_tier - kmeans_tier) > 1:
                        final_tiers[i] = int((gap_tier + kmeans_tier) / 2)
            
            return final_tiers
            
        except Exception as e:
            self.logger.error(f"Error calculating hybrid tiers: {e}")
            return self._calculate_statistical_gap_tiers(df, position)
    
    def _create_tier_definitions(self, df: pd.DataFrame, tier_assignments: List[int], 
                               position: str) -> List[TierDefinition]:
        """Create tier definition objects"""
        try:
            tiers = []
            unique_tiers = sorted(set(tier_assignments))
            position_config = self.position_tier_configs.get(position, {})
            tier_names = position_config.get('tier_names', [])
            draft_rounds = position_config.get('draft_rounds', [])
            
            for tier_num in unique_tiers:
                # Get players in this tier
                tier_indices = [i for i, t in enumerate(tier_assignments) if t == tier_num]
                tier_players = []
                
                projections_in_tier = []
                
                for idx, row_idx in enumerate(tier_indices):
                    row = df.iloc[row_idx]
                    
                    player_data = PlayerTierData(
                        player_id=getattr(row, 'player_id', row_idx),
                        player_name=row['player_name'],
                        position=position,
                        tier=tier_num,
                        tier_rank=idx + 1,
                        overall_rank=row_idx + 1,
                        projected_points=row['projected_points'],
                        floor_points=getattr(row, 'floor_points', row['projected_points'] * 0.7),
                        ceiling_points=getattr(row, 'ceiling_points', row['projected_points'] * 1.3),
                        confidence=getattr(row, 'confidence', 0.75),
                        tier_color=self.tier_colors[min(tier_num - 1, len(self.tier_colors) - 1)]
                    )
                    
                    tier_players.append(player_data)
                    projections_in_tier.append(row['projected_points'])
                
                # Calculate tier statistics
                tier_mean = np.mean(projections_in_tier)
                tier_std = np.std(projections_in_tier) if len(projections_in_tier) > 1 else 0
                tier_min = min(projections_in_tier)
                tier_max = max(projections_in_tier)
                
                # Get tier name
                tier_name = tier_names[tier_num - 1] if tier_num - 1 < len(tier_names) else f"Tier {tier_num}"
                
                # Get draft rounds
                tier_draft_rounds = draft_rounds[tier_num - 1] if tier_num - 1 < len(draft_rounds) else []
                
                tier_def = TierDefinition(
                    tier_number=tier_num,
                    position=position,
                    tier_name=tier_name,
                    players=tier_players,
                    player_count=len(tier_players),
                    tier_mean=tier_mean,
                    tier_std=tier_std,
                    tier_min=tier_min,
                    tier_max=tier_max,
                    tier_color=self.tier_colors[min(tier_num - 1, len(self.tier_colors) - 1)],
                    recommended_draft_rounds=tier_draft_rounds
                )
                
                tiers.append(tier_def)
            
            # Calculate gaps between tiers
            for i in range(len(tiers) - 1):
                current_tier = tiers[i]
                next_tier = tiers[i + 1]
                gap = current_tier.tier_min - next_tier.tier_max
                current_tier.gap_to_next_tier = gap
                
                # Calculate gap significance
                combined_std = np.sqrt((current_tier.tier_std ** 2 + next_tier.tier_std ** 2) / 2)
                if combined_std > 0:
                    gap_significance = gap / combined_std
                else:
                    gap_significance = 0
                current_tier.gap_significance = gap_significance
                
                # Determine tier quality
                if gap_significance > 2.0:
                    current_tier.tier_quality = TierQuality.EXCELLENT
                elif gap_significance > 1.5:
                    current_tier.tier_quality = TierQuality.GOOD
                elif gap_significance > 1.0:
                    current_tier.tier_quality = TierQuality.FAIR
                else:
                    current_tier.tier_quality = TierQuality.POOR
            
            return tiers
            
        except Exception as e:
            self.logger.error(f"Error creating tier definitions: {e}")
            return []
    
    def _calculate_tier_quality(self, tiers: List[TierDefinition]) -> Tuple[float, float]:
        """Calculate overall tier quality metrics"""
        try:
            if not tiers:
                return 0.0, 0.0
            
            # Overall quality based on gap significance
            gap_significances = [tier.gap_significance for tier in tiers if tier.gap_to_next_tier is not None]
            
            if gap_significances:
                overall_quality = min(1.0, np.mean(gap_significances) / 2.0)
                separation_clarity = min(1.0, min(gap_significances) / 1.5)
            else:
                overall_quality = 0.5
                separation_clarity = 0.5
            
            return overall_quality, separation_clarity
            
        except Exception as e:
            self.logger.error(f"Error calculating tier quality: {e}")
            return 0.5, 0.5
    
    def _calculate_tier_statistics(self, tiers: List[TierDefinition]) -> Dict[str, float]:
        """Calculate tier statistics"""
        try:
            if not tiers:
                return {'largest_gap': 0, 'smallest_gap': 0, 'average_tier_size': 0}
            
            gaps = [tier.gap_to_next_tier for tier in tiers if tier.gap_to_next_tier is not None]
            tier_sizes = [tier.player_count for tier in tiers]
            
            return {
                'largest_gap': max(gaps) if gaps else 0,
                'smallest_gap': min(gaps) if gaps else 0,
                'average_tier_size': np.mean(tier_sizes)
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating tier statistics: {e}")
            return {'largest_gap': 0, 'smallest_gap': 0, 'average_tier_size': 0}
    
    def _generate_draft_strategy_notes(self, tiers: List[TierDefinition], position: str) -> List[str]:
        """Generate draft strategy notes based on tier analysis"""
        try:
            notes = []
            
            if not tiers:
                return notes
            
            # Analyze tier structure
            elite_tier = tiers[0] if tiers else None
            if elite_tier and elite_tier.player_count <= 4:
                notes.append(f"Elite {position} tier is very small ({elite_tier.player_count} players) - prioritize early")
            
            # Find tiers with good value
            for tier in tiers:
                if tier.tier_quality in [TierQuality.EXCELLENT, TierQuality.GOOD] and tier.player_count >= 6:
                    draft_text = f"rounds {tier.recommended_draft_rounds[0]}-{tier.recommended_draft_rounds[-1]}" if tier.recommended_draft_rounds else "mid-rounds"
                    notes.append(f"{tier.tier_name} offers good depth - consider waiting until {draft_text}")
            
            # Identify tier breaks
            large_gaps = [tier for tier in tiers if tier.gap_to_next_tier and tier.gap_to_next_tier > 2.0]
            for tier in large_gaps:
                notes.append(f"Significant drop-off after {tier.tier_name} - avoid reaching into next tier")
            
            # Position-specific advice
            if position == 'QB' and len(tiers) >= 3:
                notes.append("QB position has depth - wait on QB unless elite tier available")
            elif position in ['RB', 'WR'] and len(tiers) >= 4:
                notes.append(f"{position} scarcity in later tiers - secure starter early")
            
            return notes
            
        except Exception as e:
            self.logger.error(f"Error generating draft strategy notes: {e}")
            return []
    
    def _calculate_tier_break_points(self, tiers: List[TierDefinition]) -> List[float]:
        """Calculate tier break points for visualization"""
        try:
            break_points = []
            
            for tier in tiers:
                if tier.gap_to_next_tier is not None:
                    # Break point is midway between tiers
                    break_point = tier.tier_min - (tier.gap_to_next_tier / 2)
                    break_points.append(break_point)
            
            return break_points
            
        except Exception as e:
            self.logger.error(f"Error calculating tier break points: {e}")
            return []
    
    def get_tier_summary(self, analysis: TierAnalysisResult) -> str:
        """Get formatted tier summary"""
        try:
            lines = []
            lines.append(f"📊 TIER ANALYSIS - {analysis.position}")
            lines.append("=" * 50)
            lines.append(f"Method: {analysis.analysis_method.value}")
            lines.append(f"Players: {analysis.total_players} | Tiers: {analysis.total_tiers}")
            lines.append(f"Quality Score: {analysis.overall_tier_quality:.1%}")
            lines.append("")
            
            for tier in analysis.tiers:
                tier_emoji = "🔥" if tier.tier_quality == TierQuality.EXCELLENT else "✅" if tier.tier_quality == TierQuality.GOOD else "⚠️"
                lines.append(f"{tier_emoji} {tier.tier_name} ({tier.player_count} players)")
                lines.append(f"   Range: {tier.tier_min:.1f} - {tier.tier_max:.1f} pts")
                
                if tier.gap_to_next_tier:
                    lines.append(f"   Gap to next: {tier.gap_to_next_tier:.1f} pts")
                
                # Show top 3 players in tier
                top_players = tier.players[:3]
                player_names = [p.player_name for p in top_players]
                lines.append(f"   Top: {', '.join(player_names)}")
                lines.append("")
            
            if analysis.draft_strategy_notes:
                lines.append("🎯 DRAFT STRATEGY:")
                for note in analysis.draft_strategy_notes:
                    lines.append(f"• {note}")
            
            return "\n".join(lines)
            
        except Exception as e:
            self.logger.error(f"Error creating tier summary: {e}")
            return "Error creating tier summary"

# Sample data generator
def generate_sample_player_data(position: str, count: int = 30) -> List[Dict[str, Any]]:
    """Generate sample player data for testing"""
    np.random.seed(42)
    
    # Position-specific projection ranges
    projection_ranges = {
        'QB': (15, 25),
        'RB': (8, 18),
        'WR': (6, 16),
        'TE': (4, 14)
    }
    
    min_proj, max_proj = projection_ranges.get(position, (5, 15))
    
    players = []
    for i in range(count):
        # Create realistic projection distribution (not uniform)
        if i < 5:  # Elite tier
            base_proj = np.random.uniform(max_proj * 0.85, max_proj)
        elif i < 12:  # High tier
            base_proj = np.random.uniform(max_proj * 0.65, max_proj * 0.85)
        elif i < 20:  # Mid tier
            base_proj = np.random.uniform(max_proj * 0.45, max_proj * 0.65)
        else:  # Lower tiers
            base_proj = np.random.uniform(min_proj, max_proj * 0.45)
        
        player = {
            'player_id': i + 1,
            'player_name': f"{position} Player {i + 1}",
            'position': position,
            'projected_points': base_proj,
            'floor_points': base_proj * 0.7,
            'ceiling_points': base_proj * 1.3,
            'confidence': np.random.uniform(0.6, 0.9)
        }
        players.append(player)
    
    return players

if __name__ == "__main__":
    print("📊 TIER RANKINGS SYSTEM TEST")
    print("=" * 40)
    
    tier_system = TierRankingsSystem()
    
    # Test different positions
    positions = ['QB', 'RB', 'WR', 'TE']
    
    for position in positions:
        print(f"\n🏈 Testing {position} tier analysis")
        print("-" * 30)
        
        # Generate sample data
        sample_data = generate_sample_player_data(position, 25)
        
        # Analyze tiers
        analysis = tier_system.create_tier_rankings(
            sample_data, position, TierMethod.HYBRID_APPROACH
        )
        
        print(f"Created {analysis.total_tiers} tiers for {analysis.total_players} players")
        print(f"Quality Score: {analysis.overall_tier_quality:.1%}")
        print(f"Separation Clarity: {analysis.separation_clarity:.1%}")
        
        # Show tier breakdown
        for tier in analysis.tiers[:3]:  # Show first 3 tiers
            print(f"  {tier.tier_name}: {tier.player_count} players ({tier.tier_min:.1f}-{tier.tier_max:.1f} pts)")
    
    print("\n✅ Tier Rankings System test completed!")