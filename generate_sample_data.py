import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

def generate_sample_data():
    """Generate sample parquet files for the exercise"""
    
    # Create app directory if it doesn't exist
    os.makedirs('app', exist_ok=True)
    
    # Set random seed for reproducibility
    np.random.seed(42)
    
    # === 1. PRODUCTION DATA ===
    print("Generating production data...")
    start_date = datetime(2024, 1, 15, 0, 0, 0)
    n_parts = 100
    
    production_data = []
    part_types = ['Engine_Block', 'Wheel_Hub', 'Brake_Caliper', 'Gear_Casing']
    current_part_type = part_types[0]
    type_change_counter = 0
    
    for i in range(n_parts):
        part_id = f"PART_{i:03d}"
        timestamp = start_date + timedelta(minutes=30*i)
        
        # Change part type every 20-30 parts
        type_change_counter += 1
        if type_change_counter >= np.random.randint(20, 30):
            current_part_type = np.random.choice([p for p in part_types if p != current_part_type])
            type_change_counter = 0
        
        production_data.append({
            'unique_part_identifier': part_id,
            'cycle_start_timestamp': timestamp,
            'PART_TYPE': current_part_type if i % np.random.randint(5, 15) == 0 else None  # Simulate sparse logging
        })
    
    production_df = pd.DataFrame(production_data)
    # Forward fill PART_TYPE later in processing
    production_df.to_parquet('app/production_logging_data.parquet')
    print(f"Generated {len(production_df)} production records")
    
    # === 2. PRESSURE DATA ===
    print("Generating pressure data...")
    pressure_data = []
    
    for i, row in production_df.iterrows():
        part_id = row['unique_part_identifier']
        cycle_start = row['cycle_start_timestamp']
        
        # Generate pressure profile for 30-minute cycle (every 10 seconds)
        duration_minutes = 30
        n_readings = duration_minutes * 6  # 6 readings per minute (10 sec intervals)
        
        for j in range(n_readings):
            timestamp = cycle_start + timedelta(seconds=10*j)
            
            # Simulate pressure profile: increase to peak, then decrease
            time_frac = j / n_readings
            if time_frac < 0.7:
                pressure = 2.0 + 3.0 * time_frac + np.random.normal(0, 0.1)
            else:
                pressure = 5.0 - 2.0 * (time_frac - 0.7) + np.random.normal(0, 0.05)
            
            pressure_data.append({
                'unique_part_identifier': part_id,
                'timestamp': timestamp,
                'pressure_value': max(0.5, pressure)  # Ensure positive pressure
            })
    
    pressure_df = pd.DataFrame(pressure_data)
    pressure_df.to_parquet('app/pressure_data.parquet')
    print(f"Generated {len(pressure_df)} pressure readings")
    
    # === 3. TEMPERATURE DATA ===
    print("Generating temperature data...")
    temperature_data = []
    
    # Temperature readings at cycle start (with some variation)
    for i, row in production_df.iterrows():
        timestamp = row['cycle_start_timestamp'] + timedelta(
            minutes=np.random.uniform(0, 10)  # Within first 10 minutes
        )
        
        # Different part types have different typical temperatures
        part_type = row['PART_TYPE'] if pd.notna(row['PART_TYPE']) else 'Engine_Block'
        base_temps = {
            'Engine_Block': 720,
            'Wheel_Hub': 680,
            'Brake_Caliper': 700,
            'Gear_Casing': 750
        }
        
        temperature = base_temps.get(part_type, 700) + np.random.normal(0, 10)
        
        temperature_data.append({
            'timestamp': timestamp,
            'casting_temperature': temperature
        })
    
    temperature_df = pd.DataFrame(temperature_data)
    temperature_df.to_parquet('app/casting_temperature_data.parquet')
    print(f"Generated {len(temperature_df)} temperature readings")
    
    # === 4. SILICON DATA ===
    print("Generating silicon data...")
    silicon_data = []
    
    start_time = datetime(2024, 1, 14, 23, 0, 0)
    end_time = start_date + timedelta(days=1)
    current_time = start_time
    
    while current_time < end_time:
        timestamp = current_time + timedelta(minutes=np.random.uniform(-30, 30))
        silicon_content = 1.0 + np.random.uniform(-0.3, 0.5)
        
        silicon_data.append({
            'timestamp': timestamp,
            'furnace_silicon_content': silicon_content
        })
        
        # Next reading in ~4 hours
        current_time += timedelta(hours=4, minutes=np.random.uniform(-30, 30))
    
    silicon_df = pd.DataFrame(silicon_data)
    silicon_df.to_parquet('app/furnace_silicon_data.parquet')
    print(f"Generated {len(silicon_df)} silicon readings")
    
    print("\n✅ Sample data generation complete!")
    print("Generated files in 'app/' directory:")
    print("  - production_logging_data.parquet")
    print("  - pressure_data.parquet")
    print("  - casting_temperature_data.parquet")
    print("  - furnace_silicon_data.parquet")

if __name__ == "__main__":
    generate_sample_data()