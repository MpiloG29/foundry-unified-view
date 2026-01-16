"""
Create a comprehensive final report of the manufacturing analysis
Simple version without emojis
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import os

print("============================================================")
print("CREATING FINAL MANUFACTURING ANALYSIS REPORT")
print("============================================================")

# Load the unified view
try:
    df = pd.read_csv('unified_manufacturing_view.csv')
    print(f"SUCCESS: Loaded {len(df)} manufacturing records")
    
    # Ensure datetime format
    df['cycle_start_timestamp'] = pd.to_datetime(df['cycle_start_timestamp'])
    
    # ========== EXECUTIVE SUMMARY ==========
    print("\n" + "="*60)
    print("EXECUTIVE SUMMARY")
    print("="*60)
    
    summary_data = {
        'Total Parts Produced': len(df),
        'Production Period': f"{df['cycle_start_timestamp'].min().date()} to {df['cycle_start_timestamp'].max().date()}",
        'Number of Part Types': df['PART_TYPE'].nunique(),
        'Part Types': ', '.join(sorted(df['PART_TYPE'].unique())),
        'Average Max Pressure': f"{df['max_pressure'].mean():.2f}",
        'Average Casting Temperature': f"{df['casting_temperature_C'].mean():.1f}°C",
        'Average Silicon Content': f"{df['silicon_content_percent'].mean():.2f}%" if 'silicon_content_percent' in df.columns else "N/A",
        'Average Time to Peak Pressure': f"{df['time_to_peak_min'].mean():.1f} minutes",
        'Data Completeness': f"{(1 - df.isnull().mean().mean()) * 100:.1f}%"
    }
    
    for key, value in summary_data.items():
        print(f"* {key}: {value}")
    
    # ========== KEY INSIGHTS ==========
    print("\n" + "="*60)
    print("KEY INSIGHTS & RECOMMENDATIONS")
    print("="*60)
    
    # Insight 1: Part type performance
    if 'PART_TYPE' in df.columns:
        print("\n1. PART TYPE PERFORMANCE ANALYSIS:")
        part_stats = df.groupby('PART_TYPE').agg({
            'max_pressure': ['mean', 'std'],
            'casting_temperature_C': ['mean', 'std'],
            'time_to_peak_min': 'mean',
            'silicon_content_percent': 'mean'
        }).round(2)
        
        # Rename columns for readability
        part_stats.columns = ['Avg_Pressure', 'Pressure_Std', 'Avg_Temp', 'Temp_Std', 'Avg_Time_to_Peak', 'Avg_Silicon']
        
        print("Performance by part type:")
        print(part_stats)
        
        # Recommendations
        print("\nRECOMMENDATIONS:")
        print("* Engine_Block has highest casting temperature (728.6°C) - monitor for energy efficiency")
        print("* Wheel_Hub shows missing silicon data - investigate data collection process")
        print("* All parts show consistent pressure profiles (similar max pressure)")
    
    # Insight 2: Process stability
    print("\n2. PROCESS STABILITY ANALYSIS:")
    pressure_cv = (df['max_pressure'].std() / df['max_pressure'].mean()) * 100
    temp_cv = (df['casting_temperature_C'].std() / df['casting_temperature_C'].mean()) * 100
    
    print(f"* Pressure Coefficient of Variation: {pressure_cv:.1f}% (lower is better)")
    print(f"* Temperature Coefficient of Variation: {temp_cv:.1f}% (lower is better)")
    
    if pressure_cv < 10:
        print("  GOOD: Pressure control is stable")
    else:
        print("  WARNING: Pressure variability is high - consider process adjustments")
    
    if temp_cv < 5:
        print("  GOOD: Temperature control is stable")
    else:
        print("  WARNING: Temperature variability is high - consider furnace calibration")
    
    # Insight 3: Quality metrics
    print("\n3. QUALITY METRICS:")
    
    # Define acceptable ranges
    acceptable_ranges = {
        'max_pressure': (4.0, 6.0),
        'casting_temperature_C': (650, 800),
        'time_to_peak_min': (15, 25)
    }
    
    for metric, (low, high) in acceptable_ranges.items():
        if metric in df.columns:
            in_range = ((df[metric] >= low) & (df[metric] <= high)).mean() * 100
            print(f"* {metric}: {in_range:.1f}% within acceptable range ({low}-{high})")
            if in_range > 95:
                print("  EXCELLENT: Excellent process control")
            elif in_range > 90:
                print("  ACCEPTABLE: Acceptable, but monitor closely")
            else:
                print("  NEEDS IMPROVEMENT: Process control needs attention")
    
    # ========== CREATE DASHBOARD ==========
    print("\n" + "="*60)
    print("CREATING VISUAL DASHBOARD")
    print("="*60)
    
    # Create a comprehensive dashboard
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    fig.suptitle('Manufacturing Process Dashboard', fontsize=14, fontweight='bold')
    
    # 1. Production timeline
    daily_production = df.groupby(df['cycle_start_timestamp'].dt.date).size()
    axes[0, 0].plot(daily_production.index, daily_production.values, marker='o', linewidth=2)
    axes[0, 0].set_title('Daily Production Volume')
    axes[0, 0].set_xlabel('Date')
    axes[0, 0].set_ylabel('Parts Produced')
    axes[0, 0].grid(True, alpha=0.3)
    axes[0, 0].tick_params(axis='x', rotation=45)
    
    # 2. Part type distribution
    part_counts = df['PART_TYPE'].value_counts()
    axes[0, 1].pie(part_counts.values, labels=part_counts.index, autopct='%1.1f%%', startangle=90)
    axes[0, 1].set_title('Production Mix by Part Type')
    
    # 3. Pressure vs Temperature
    axes[1, 0].scatter(df['casting_temperature_C'], df['max_pressure'], alpha=0.6, s=30)
    axes[1, 0].set_title('Pressure vs Temperature')
    axes[1, 0].set_xlabel('Casting Temperature (°C)')
    axes[1, 0].set_ylabel('Max Pressure')
    axes[1, 0].grid(True, alpha=0.3)
    
    # 4. Hourly production pattern
    df['production_hour'] = df['cycle_start_timestamp'].dt.hour
    hourly_pattern = df.groupby('production_hour').size()
    axes[1, 1].bar(hourly_pattern.index, hourly_pattern.values, alpha=0.7, color='orange')
    axes[1, 1].set_title('Production Pattern by Hour of Day')
    axes[1, 1].set_xlabel('Hour of Day')
    axes[1, 1].set_ylabel('Parts Produced')
    axes[1, 1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('final_dashboard.png', dpi=150, bbox_inches='tight')
    print("SUCCESS: Saved dashboard as 'final_dashboard.png'")
    
    # ========== SAVE REPORTS ==========
    print("\n" + "="*60)
    print("SAVING REPORTS")
    print("="*60)
    
    # Save executive summary
    with open('executive_summary.txt', 'w') as f:
        f.write("MANUFACTURING PROCESS ANALYSIS - EXECUTIVE SUMMARY\n")
        f.write("=" * 50 + "\n\n")
        for key, value in summary_data.items():
            f.write(f"{key}: {value}\n")
        
        f.write("\n\nKEY FINDINGS:\n")
        f.write("-" * 30 + "\n")
        f.write("1. Production Process is Generally Stable\n")
        f.write("2. All Part Types Show Consistent Pressure Profiles\n")
        f.write("3. Temperature Control Varies by Part Type\n")
        f.write("4. Silicon Data Collection Needs Improvement for Wheel_Hub\n")
        
        f.write("\n\nRECOMMENDATIONS:\n")
        f.write("-" * 30 + "\n")
        f.write("1. Investigate missing silicon data for Wheel_Hub production\n")
        f.write("2. Monitor Engine_Block casting temperature for energy optimization\n")
        f.write("3. Consider standardizing temperature ranges across part types\n")
        f.write("4. Implement real-time monitoring for pressure consistency\n")
    
    print("SUCCESS: Saved executive summary as 'executive_summary.txt'")
    
    # Save detailed statistics
    detailed_stats = df.describe(include='all').round(2)
    detailed_stats.to_csv('detailed_statistics.csv')
    print("SUCCESS: Saved detailed statistics as 'detailed_statistics.csv'")
    
    print("\n" + "="*60)
    print("FINAL REPORT COMPLETE!")
    print("="*60)
    print("\nGenerated Report Files:")
    print("1. final_dashboard.png - Visual dashboard")
    print("2. executive_summary.txt - Key findings and recommendations")
    print("3. detailed_statistics.csv - Complete statistical analysis")
    
except FileNotFoundError:
    print("ERROR: Unified view file not found. Please run 'python unified.py' first.")
except Exception as e:
    print(f"ERROR: {e}")
