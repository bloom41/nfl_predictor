#!/usr/bin/env python3
"""
Enhanced Rankings System
Provides additional features for better user experience
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.simple_predictor import get_position_rankings_simple
from typing import List, Dict, Any

def get_comprehensive_week_rankings(season: int = 2024, week: int = 1, top_n: int = 10) -> str:
    """Get comprehensive rankings for all positions in one display"""
    
    lines = []
    lines.append(f"🏆 NFL WEEK {week} FANTASY RANKINGS - ALL POSITIONS")
    lines.append("=" * 60)
    lines.append("")
    
    # Get rankings for each position
    positions = ['QB', 'RB', 'WR', 'TE']
    all_rankings = {}
    
    for position in positions:
        rankings_text = get_position_rankings_simple(position, season, week, top_n)
        all_rankings[position] = rankings_text
    
    # Display side by side format for better viewing
    lines.append("📊 TOP PERFORMERS BY POSITION:")
    lines.append("")
    
    for position in positions:
        lines.append(all_rankings[position])
        lines.append("")
    
    # Add summary section
    lines.append("🎯 QUICK PICKS SUMMARY:")
    lines.append("-" * 40)
    
    # Extract top performer from each position for quick reference
    for position in positions:
        ranking_lines = all_rankings[position].split('\n')
        for line in ranking_lines:
            if line.strip().startswith('1.'):
                # Extract just the player name and points
                player_info = line.strip().split(':')[0].replace('1.', '').strip()
                points = line.split(':')[1].split('pts')[0].strip() + ' pts'
                lines.append(f"{position} #1: {player_info} - {points}")
                break
    
    lines.append("")
    lines.append("💡 Using machine learning models trained on real NFL data")
    lines.append("⚡ Historical data from all available seasons for accuracy")
    
    return "\n".join(lines)

def get_sleeper_picks(season: int = 2024, week: int = 1) -> str:
    """Identify potential sleeper picks (players ranked 6-15)"""
    
    lines = []
    lines.append(f"😴 WEEK {week} SLEEPER PICKS (RANKS 6-15)")
    lines.append("=" * 50)
    lines.append("")
    
    positions = ['QB', 'RB', 'WR', 'TE']
    
    for position in positions:
        # Get extended rankings
        rankings_text = get_position_rankings_simple(position, season, week, 15)
        ranking_lines = rankings_text.split('\n')
        
        lines.append(f"🎯 {position} SLEEPERS:")
        
        sleeper_count = 0
        for line in ranking_lines:
            if any(f"{i}." in line.strip()[:3] for i in range(6, 16)):
                lines.append(f"  {line.strip()}")
                sleeper_count += 1
                if sleeper_count >= 5:  # Show top 5 sleepers
                    break
        
        lines.append("")
    
    lines.append("💡 Sleeper picks offer high upside with lower ownership")
    
    return "\n".join(lines)

def compare_positions(season: int = 2024, week: int = 1) -> str:
    """Compare scoring potential across positions"""
    
    lines = []
    lines.append(f"⚖️  WEEK {week} POSITION SCORING COMPARISON")
    lines.append("=" * 50)
    lines.append("")
    
    positions = ['QB', 'RB', 'WR', 'TE']
    position_stats = {}
    
    for position in positions:
        rankings_text = get_position_rankings_simple(position, season, week, 10)
        ranking_lines = rankings_text.split('\n')
        
        scores = []
        for line in ranking_lines:
            if '. ' in line and ': ' in line and ' pts ' in line:
                try:
                    pts_part = line.split(': ')[1].split(' pts')[0]
                    score = float(pts_part)
                    scores.append(score)
                except:
                    continue
        
        if scores:
            position_stats[position] = {
                'avg': sum(scores) / len(scores),
                'high': max(scores),
                'low': min(scores)
            }
    
    lines.append("📈 SCORING ANALYSIS:")
    lines.append("")
    
    for position in positions:
        if position in position_stats:
            stats = position_stats[position]
            lines.append(f"{position}:")
            lines.append(f"  🔥 Ceiling: {stats['high']:.1f} pts")
            lines.append(f"  📊 Average: {stats['avg']:.1f} pts") 
            lines.append(f"  🚧 Floor: {stats['low']:.1f} pts")
            lines.append("")
    
    # Find best value position
    if position_stats:
        best_avg = max(position_stats.values(), key=lambda x: x['avg'])
        best_pos = [pos for pos, stats in position_stats.items() if stats['avg'] == best_avg['avg']][0]
        
        lines.append(f"💰 BEST VALUE POSITION: {best_pos}")
        lines.append(f"   Highest average projected points: {best_avg['avg']:.1f} pts")
    
    return "\n".join(lines)

if __name__ == "__main__":
    print("🏈 ENHANCED NFL RANKINGS SYSTEM")
    print("=" * 40)
    print()
    
    # Test comprehensive rankings
    print(get_comprehensive_week_rankings(2024, 1, 5))
    print()
    
    # Test sleeper picks
    print(get_sleeper_picks(2024, 1))
    print()
    
    # Test position comparison
    print(compare_positions(2024, 1))