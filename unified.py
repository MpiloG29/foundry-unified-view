import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import timedelta
import warnings
warnings.filterwarnings('ignore')

def build_unified_view() -> pd.DataFrame:
    """
    Build a unified view of manufacturing data from multiple sources.
    Returns a DataFrame where each row represents a single part with all relevant metrics.
    """
    
    # Load all data files
    print("📂 Loading data files...")
    try:
        production_data_df = pd.read_parquet("app/production_logging_data.parquet")
        pressure_data_df = pd.read_parquet("app/pressure_data.parquet")
        temperature_data_df = pd.read_parquet("app/casting_temperature_data.parquet")
        silicon_data_df = pd.read_parquet("app/furnace_silicon_data.parquet")
        print("✅ Data loaded successfully")
    except FileNotFoundError as e:
        print(f"❌ Error loading data: {e}")
        print("Please run 'generate_sample_data.py' first to create sample data")
        return pd.DataFrame()
    
    # === BLOCK 1: PROCESS PRODUCTION DATA ===
    print("\n1️⃣ Processing production data...")
    
    # Ensure timestamp is datetime
    production_data_df['cycle_start_timestamp'] = pd.to_datetime(
        production_data_df['cycle_start_timestamp']
    )
    
    # Sort by timestamp
    production_data_df = production_data_df.sort_values('cycle_start_timestamp')
    
    # Forward fill PART_TYPE to make it dense (as per README specification)
    production_data_df['PART_TYPE'] = production_data_df['PART_TYPE'].ffill()
    
    # Create unified_view starting with production data
    unified_view = production_data_df.copy()
    print(f"   Processed {len(unified_view)} unique parts")
    print(f"   Part types distribution:\n{unified_view['PART_TYPE'].value_counts()}")
    
    # === BLOCK 2: PROCESS PRESSURE DATA ===
    print("\n2️⃣ Processing pressure data...")
    
    # Ensure timestamp is datetime
    pressure_data_df['timestamp'] = pd.to_datetime(pressure_data_df['timestamp'])
    
    # Sort pressure data
    pressure_data_df = pressure_data_df.sort_values(['unique_part_identifier', 'timestamp'])
    
    # Extract pressure metrics per part
    pressure_metrics = []
    
    for part_id, group in pressure_data_df.groupby('unique_part_identifier'):
        if len(group) == 0:
            continue
            
        # Find max pressure and time to peak
        max_pressure_idx = group['pressure_value'].idxmax()
        max_pressure = group.loc[max_pressure_idx, 'pressure_value']
        peak_time = group.loc[max_pressure_idx, 'timestamp']
        
        # Calculate time to peak (in minutes from cycle start)
        cycle_start = group['timestamp'].iloc[0]
        time_to_peak_min = (peak_time - cycle_start).total_seconds() / 60
        
        # Calculate pressure statistics
        pressure_stats = {
            'unique_part_identifier': part_id,
            'max_pressure': max_pressure,
            'time_to_peak_min': time_to_peak_min,
            'avg_pressure': group['pressure_value'].mean(),
            'pressure_variance': group['pressure_value'].var(),
            'pressure_duration_min': (group['timestamp'].iloc[-1] - cycle_start).total_seconds() / 60
        }
        pressure_metrics.append(pressure_stats)
    
    pressure_summary_df = pd.DataFrame(pressure_metrics)
    
    # Merge pressure data into unified view
    unified_view = pd.merge(
        unified_view, 
        pressure_summary_df, 
        on='unique_part_identifier', 
        how='left',
        validate='one_to_one'
    )
    print(f"   Added pressure metrics for {len(pressure_summary_df)} parts")
    print(f"   Average max pressure: {pressure_summary_df['max_pressure'].mean():.2f}")
    
    # === BLOCK 3: PROCESS TEMPERATURE DATA ===
    print("\n3️⃣ Processing temperature data...")
    
    # Ensure timestamp is datetime
    temperature_data_df['timestamp'] = pd.to_datetime(temperature_data_df['timestamp'])
    temperature_data_df = temperature_data_df.sort_values('timestamp')
    
    # Use merge_asof to align temperature with nearest production cycle
    # Temperature is recorded at the beginning of casting (first 10 minutes)
    unified_view = pd.merge_asof(
        unified_view.sort_values('cycle_start_timestamp'),
        temperature_data_df,
        left_on='cycle_start_timestamp',
        right_on='timestamp',
        direction='nearest',
        tolerance=pd.Timedelta('20 minutes')  # Within reasonable window
    )
    
    # Rename temperature column for clarity
    unified_view = unified_view.rename(columns={'casting_temperature': 'casting_temperature_C'})
    
    print(f"   Matched temperature for {unified_view['casting_temperature_C'].notna().sum()} parts")
    print(f"   Average casting temperature: {unified_view['casting_temperature_C'].mean():.1f}°C")
    
    # === BLOCK 4: PROCESS SILICON DATA ===
    print("\n4️⃣ Processing silicon data...")
    
    # Ensure timestamp is datetime
    silicon_data_df['timestamp'] = pd.to_datetime(silicon_data_df['timestamp'])
    silicon_data_df = silicon_data_df.sort_values('timestamp')
    
    # Silicon content applies forward (next 4 hours of production)
    unified_view = pd.merge_asof(
        unified_view.sort_values('cycle_start_timestamp'),
        silicon_data_df,
        left_on='cycle_start_timestamp',
        right_on='timestamp',
        direction='forward',
        tolerance=pd.Timedelta('4 hours')  # Valid for next 4 hours
    )
    
    # Rename silicon column for clarity
    unified_view = unified_view.rename(columns={'furnace_silicon_content': 'silicon_content_percent'})
    
    print(f"   Matched silicon content for {unified_view['silicon_content_percent'].notna().sum()} parts")
    print(f"   Average silicon content: {unified_view['silicon_content_percent'].mean():.2f}%")
    
    # === BLOCK 5: DATA VALIDATION AND CLEANUP ===
    print("\n5️⃣ Final data validation and cleanup...")
    
    # Drop the extra timestamp columns from merges
    if 'timestamp' in unified_view.columns:
        unified_view = unified_view.drop(columns=['timestamp'])
    if 'timestamp_x' in unified_view.columns:
        unified_view = unified_view.drop(columns=['timestamp_x'])
    if 'timestamp_y' in unified_view.columns:
        unified_view = unified_view.drop(columns=['timestamp_y'])
    
    # Calculate derived metrics
    unified_view['production_hour'] = unified_view['cycle_start_timestamp'].dt.hour
    unified_view['production_day'] = unified_view['cycle_start_timestamp'].dt.date
    
    # Reorder columns for clarity
    column_order = [
        'unique_part_identifier',
        'cycle_start_timestamp',
        'PART_TYPE',
        'max_pressure',
        'time_to_peak_min',
        'avg_pressure',
        'pressure_variance',
        'pressure_duration_min',
        'casting_temperature_C',
        'silicon_content_percent',
        'production_hour',
        'production_day'
    ]
    
    # Keep only columns that exist
    column_order = [col for col in column_order if col in unified_view.columns]
    unified_view = unified_view[column_order]
    
    # === BLOCK 6: CRITICAL REVIEW ===
    print("\n🔍 CRITICAL REVIEW OF UNIFIED VIEW")
    print("=" * 50)
    
    # 6.1 Basic statistics
    print("\n📊 Dataset Overview:")
    print(f"Total parts: {len(unified_view)}")
    print(f"Date range: {unified_view['cycle_start_timestamp'].min()} to {unified_view['cycle_start_timestamp'].max()}")
    
    # 6.2 Missing values analysis
    print("\n📈 Missing Values Analysis:")
    missing_data = unified_view.isnull().sum()
    missing_percent = (missing_data / len(unified_view) * 100).round(2)
    missing_df = pd.DataFrame({
        'Missing_Count': missing_data,
        'Missing_Percent': missing_percent
    })
    print(missing_df[missing_df['Missing_Count'] > 0])
    
    # 6.3 Statistical summary
    print("\n📈 Statistical Summary:")
    numeric_cols = unified_view.select_dtypes(include=[np.number]).columns
    print(unified_view[numeric_cols].describe().round(2))
    
    # 6.4 Data quality checks
    print("\n✅ Data Quality Checks:")
    
    # Check for negative pressures (shouldn't happen)
    neg_pressure = (unified_view['max_pressure'] < 0).sum()
    print(f"Parts with negative max pressure: {neg_pressure}")
    
    # Check for unrealistic temperatures
    temp_range = (unified_view['casting_temperature_C'] < 600) | (unified_view['casting_temperature_C'] > 900)
    print(f"Parts with unrealistic temperatures (<600°C or >900°C): {temp_range.sum()}")
    
    # Check time to peak consistency
    peak_time_outliers = (unified_view['time_to_peak_min'] < 0) | (unified_view['time_to_peak_min'] > 30)
    print(f"Parts with unrealistic time to peak: {peak_time_outliers.sum()}")
    
    # === VISUALIZATIONS ===
    print("\n📊 Generating visualizations...")
    
    fig, axes = plt.subplots(3, 2, figsize=(15, 12))
    fig.suptitle('Manufacturing Process Analysis - Unified View', fontsize=16, fontweight='bold')
    
    # 1. Pressure over time
    axes[0, 0].scatter(unified_view['cycle_start_timestamp'], 
                      unified_view['max_pressure'], 
                      alpha=0.6, s=20)
    axes[0, 0].set_title('Max Pressure Over Time')
    axes[0, 0].set_xlabel('Production Time')
    axes[0, 0].set_ylabel('Max Pressure')
    axes[0, 0].grid(True, alpha=0.3)
    
    # 2. Temperature distribution by part type
    if 'PART_TYPE' in unified_view.columns and 'casting_temperature_C' in unified_view.columns:
        part_types = unified_view['PART_TYPE'].unique()
        temp_data = [unified_view[unified_view['PART_TYPE'] == pt]['casting_temperature_C'].dropna() 
                    for pt in part_types]
        axes[0, 1].boxplot(temp_data, labels=part_types)
        axes[0, 1].set_title('Casting Temperature by Part Type')
        axes[0, 1].set_xlabel('Part Type')
        axes[0, 1].set_ylabel('Temperature (°C)')
        axes[0, 1].grid(True, alpha=0.3)
        axes[0, 1].tick_params(axis='x', rotation=45)
    
    # 3. Time to peak pressure histogram
    axes[1, 0].hist(unified_view['time_to_peak_min'].dropna(), bins=20, alpha=0.7, edgecolor='black')
    axes[1, 0].axvline(unified_view['time_to_peak_min'].mean(), color='red', 
                      linestyle='--', label=f'Mean: {unified_view["time_to_peak_min"].mean():.1f} min')
    axes[1, 0].set_title('Time to Peak Pressure Distribution')
    axes[1, 0].set_xlabel('Time to Peak (minutes)')
    axes[1, 0].set_ylabel('Frequency')
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3)
    
    # 4. Silicon content over time
    axes[1, 1].plot(unified_view['cycle_start_timestamp'].sort_values(), 
                   unified_view['silicon_content_percent'].sort_values(), 
                   marker='o', markersize=3, linewidth=1, alpha=0.7)
    axes[1, 1].set_title('Silicon Content Over Production Time')
    axes[1, 1].set_xlabel('Production Time')
    axes[1, 1].set_ylabel('Silicon Content (%)')
    axes[1, 1].grid(True, alpha=0.3)
    
    # 5. Pressure vs Temperature scatter
    scatter = axes[2, 0].scatter(unified_view['casting_temperature_C'], 
                                unified_view['max_pressure'],
                                c=unified_view['time_to_peak_min'] if 'time_to_peak_min' in unified_view.columns else None,
                                cmap='viridis', alpha=0.6, s=30)
    axes[2, 0].set_title('Max Pressure vs Casting Temperature')
    axes[2, 0].set_xlabel('Casting Temperature (°C)')
    axes[2, 0].set_ylabel('Max Pressure')
    axes[2, 0].grid(True, alpha=0.3)
    if 'time_to_peak_min' in unified_view.columns:
        plt.colorbar(scatter, ax=axes[2, 0], label='Time to Peak (min)')
    
    # 6. Production rate over time
    if 'cycle_start_timestamp' in unified_view.columns:
        hourly_production = unified_view.groupby(
            unified_view['cycle_start_timestamp'].dt.floor('H')
        ).size()
        axes[2, 1].plot(hourly_production.index, hourly_production.values, 
                       marker='o', linewidth=2)
        axes[2, 1].set_title('Production Rate (Parts per Hour)')
        axes[2, 1].set_xlabel('Time (Hourly)')
        axes[2, 1].set_ylabel('Number of Parts')
        axes[2, 1].grid(True, alpha=0.3)
        axes[2, 1].tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    plt.savefig('unified_view_analysis.png', dpi=150, bbox_inches='tight')
    print("✅ Visualizations saved as 'unified_view_analysis.png'")
    
    # === SAVE UNIFIED VIEW ===
    unified_view.to_csv('unified_manufacturing_view.csv', index=False)
    unified_view.to_parquet('unified_manufacturing_view.parquet', index=False)
    
    print("\n" + "="*50)
    print("✅ UNIFIED VIEW CREATED SUCCESSFULLY!")
    print("="*50)
    print(f"\n📁 Output files saved:")
    print(f"   - unified_manufacturing_view.csv")
    print(f"   - unified_manufacturing_view.parquet")
    print(f"   - unified_view_analysis.png")
    print(f"\n📊 Final unified view shape: {unified_view.shape}")
    print(f"📅 Date range: {unified_view['cycle_start_timestamp'].min().date()} to {unified_view['cycle_start_timestamp'].max().date()}")
    
    return unified_view

if __name__ == "__main__":
    unified_df = build_unified_view()
    
    # Display sample of the final dataframe
    if not unified_df.empty:
        print("\n📋 Sample of final unified view (first 5 rows):")
        print(unified_df.head().to_string())
        
        print("\n📋 Column descriptions:")
        for col in unified_df.columns:
            non_null = unified_df[col].notna().sum()
            dtype = unified_df[col].dtype
            print(f"  - {col}: {dtype}, {non_null}/{len(unified_df)} non-null")