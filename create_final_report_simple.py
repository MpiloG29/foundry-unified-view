"""
Create a concise final report for the Core Unified View.
"""
import pandas as pd
import matplotlib.pyplot as plt


print("============================================================")
print("CREATING FINAL MANUFACTURING ANALYSIS REPORT")
print("============================================================")

try:
    df = pd.read_csv("unified_manufacturing_view.csv")
    print(f"SUCCESS: Loaded {len(df)} manufacturing records")

    df["cycle_start_timestamp"] = pd.to_datetime(df["cycle_start_timestamp"])

    part_type_col = "part_type" if "part_type" in df.columns else "PART_TYPE"
    alert_columns = [
        column
        for column in [
            "pressure_outlier",
            "temperature_outlier",
            "silicon_drift_alert",
            "missing_alignment_alert",
        ]
        if column in df.columns
    ]

    print("\n" + "=" * 60)
    print("EXECUTIVE SUMMARY")
    print("=" * 60)

    summary_data = {
        "Total Parts Produced": len(df),
        "Production Period": (
            f"{df['cycle_start_timestamp'].min().date()} "
            f"to {df['cycle_start_timestamp'].max().date()}"
        ),
        "Number of Part Types": df[part_type_col].nunique(),
        "Part Types": ", ".join(sorted(df[part_type_col].dropna().unique())),
        "Average Max Pressure": f"{df['max_pressure'].mean():.2f}",
        "Average Casting Temperature": f"{df['casting_temperature_C'].mean():.1f} C",
        "Average Silicon Content": f"{df['silicon_content_percent'].mean():.2f}%",
        "Average Time to Peak Pressure": f"{df['time_to_peak_min'].mean():.1f} minutes",
        "Average Quality Index": f"{df['unified_part_quality_index'].mean():.1f}/100"
        if "unified_part_quality_index" in df.columns
        else "N/A",
        "Data Completeness": f"{(1 - df.isnull().mean().mean()) * 100:.1f}%",
    }

    for key, value in summary_data.items():
        print(f"* {key}: {value}")

    print("\n" + "=" * 60)
    print("KEY INSIGHTS & RECOMMENDATIONS")
    print("=" * 60)

    print("\n1. PART TYPE PERFORMANCE ANALYSIS:")
    part_stats = df.groupby(part_type_col).agg(
        Avg_Pressure=("max_pressure", "mean"),
        Pressure_Std=("max_pressure", "std"),
        Avg_Temp=("casting_temperature_C", "mean"),
        Temp_Std=("casting_temperature_C", "std"),
        Avg_Time_to_Peak=("time_to_peak_min", "mean"),
        Avg_Silicon=("silicon_content_percent", "mean"),
        Avg_Quality_Index=("unified_part_quality_index", "mean"),
    ).round(2)
    print(part_stats)

    print("\n2. QUALITY AND ANOMALY REVIEW:")
    if alert_columns:
        alert_counts = df[alert_columns].sum().astype(int)
        for column, count in alert_counts.items():
            print(f"* {column}: {count}")
    else:
        print("* No alert columns available. Run unified.py to regenerate the Core Unified View.")

    print("\n3. PROCESS STABILITY ANALYSIS:")
    pressure_cv = (df["max_pressure"].std() / df["max_pressure"].mean()) * 100
    temp_cv = (df["casting_temperature_C"].std() / df["casting_temperature_C"].mean()) * 100
    print(f"* Pressure Coefficient of Variation: {pressure_cv:.1f}%")
    print(f"* Temperature Coefficient of Variation: {temp_cv:.1f}%")

    print("\n" + "=" * 60)
    print("CREATING VISUAL DASHBOARD")
    print("=" * 60)

    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    fig.suptitle("Core Unified View Dashboard", fontsize=14, fontweight="bold")

    daily_production = df.groupby(df["cycle_start_timestamp"].dt.date).size()
    axes[0, 0].plot(daily_production.index, daily_production.values, marker="o", linewidth=2)
    axes[0, 0].set_title("Daily Production Volume")
    axes[0, 0].set_xlabel("Date")
    axes[0, 0].set_ylabel("Parts Produced")
    axes[0, 0].grid(True, alpha=0.3)
    axes[0, 0].tick_params(axis="x", rotation=45)

    part_counts = df[part_type_col].value_counts()
    axes[0, 1].pie(part_counts.values, labels=part_counts.index, autopct="%1.1f%%", startangle=90)
    axes[0, 1].set_title("Production Mix by Part Type")

    axes[1, 0].scatter(
        df["casting_temperature_C"],
        df["max_pressure"],
        c=df["time_to_peak_min"],
        cmap="viridis",
        alpha=0.7,
        s=35,
    )
    axes[1, 0].set_title("Pressure vs Temperature")
    axes[1, 0].set_xlabel("Casting Temperature (C)")
    axes[1, 0].set_ylabel("Max Pressure")
    axes[1, 0].grid(True, alpha=0.3)

    if "unified_part_quality_index" in df.columns:
        axes[1, 1].plot(
            df["cycle_start_timestamp"],
            df["unified_part_quality_index"],
            color="green",
            marker="o",
            markersize=3,
            linewidth=1,
        )
        axes[1, 1].set_title("Unified Part Quality Index")
        axes[1, 1].set_ylabel("Score")
    else:
        hourly_pattern = df.groupby(df["cycle_start_timestamp"].dt.hour).size()
        axes[1, 1].bar(hourly_pattern.index, hourly_pattern.values, alpha=0.7, color="orange")
        axes[1, 1].set_title("Production Pattern by Hour")
        axes[1, 1].set_ylabel("Parts Produced")
    axes[1, 1].set_xlabel("Production Time")
    axes[1, 1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig("final_dashboard.png", dpi=150, bbox_inches="tight")
    print("SUCCESS: Saved dashboard as 'final_dashboard.png'")

    with open("executive_summary.txt", "w", encoding="utf-8") as file:
        file.write("MANUFACTURING PROCESS ANALYSIS - EXECUTIVE SUMMARY\n")
        file.write("=" * 50 + "\n\n")
        for key, value in summary_data.items():
            file.write(f"{key}: {value}\n")

        file.write("\n\nKEY FINDINGS:\n")
        file.write("-" * 30 + "\n")
        file.write("1. Core Unified View produces one row per unique part identifier.\n")
        file.write("2. Silicon readings are aligned backward because each reading applies forward.\n")
        file.write("3. Pressure, temperature, and silicon alert flags are available per part.\n")
        file.write("4. Quality index and temperature stability KPIs support batch review.\n")

    df.describe(include="all").round(2).to_csv("detailed_statistics.csv")
    print("SUCCESS: Saved executive_summary.txt and detailed_statistics.csv")

except FileNotFoundError:
    print("ERROR: Unified view file not found. Please run 'python unified.py' first.")
except Exception as error:
    print(f"ERROR: {error}")
