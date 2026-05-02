import os
import warnings

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")


OUTPUT_UNIFIED_CSV = "unified_manufacturing_view.csv"
OUTPUT_UNIFIED_PARQUET = "unified_manufacturing_view.parquet"
OUTPUT_QUALITY_CSV = "unified_quality_alerts.csv"
OUTPUT_ALIGNMENT_DASHBOARD = "process_alignment_dashboard.png"
OUTPUT_QUALITY_DASHBOARD = "quality_insights_dashboard.png"
OUTPUT_ANALYSIS_DASHBOARD = "unified_view_analysis.png"


def _load_source_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load source parquet files, creating demo data if the app folder is absent."""
    required_files = [
        "app/production_logging_data.parquet",
        "app/pressure_data.parquet",
        "app/casting_temperature_data.parquet",
        "app/furnace_silicon_data.parquet",
    ]

    if not all(os.path.exists(path) for path in required_files):
        print("Source parquet files not found. Generating sample data first...")
        from generate_sample_data import generate_sample_data

        generate_sample_data()

    production_data_df = pd.read_parquet(required_files[0])
    pressure_data_df = pd.read_parquet(required_files[1])
    temperature_data_df = pd.read_parquet(required_files[2])
    silicon_data_df = pd.read_parquet(required_files[3])

    return production_data_df, pressure_data_df, temperature_data_df, silicon_data_df


def _pressure_metrics(pressure_data_df: pd.DataFrame) -> pd.DataFrame:
    pressure_data_df = pressure_data_df.copy()
    pressure_data_df["timestamp"] = pd.to_datetime(pressure_data_df["timestamp"])
    pressure_data_df = pressure_data_df.sort_values(["unique_part_identifier", "timestamp"])

    pressure_metrics = []
    for part_id, group in pressure_data_df.groupby("unique_part_identifier", sort=False):
        max_pressure_idx = group["pressure_value"].idxmax()
        peak_pressure_timestamp = group.loc[max_pressure_idx, "timestamp"]
        cycle_start = group["timestamp"].iloc[0]
        cycle_end = group["timestamp"].iloc[-1]

        pressure_metrics.append(
            {
                "unique_part_identifier": part_id,
                "max_pressure": group.loc[max_pressure_idx, "pressure_value"],
                "peak_pressure_timestamp": peak_pressure_timestamp,
                "time_to_peak_min": (peak_pressure_timestamp - cycle_start).total_seconds() / 60,
                "avg_pressure": group["pressure_value"].mean(),
                "pressure_variance": group["pressure_value"].var(),
                "pressure_duration_min": (cycle_end - cycle_start).total_seconds() / 60,
                "pressure_cycle_end_timestamp": cycle_end,
            }
        )

    return pd.DataFrame(pressure_metrics)


def _build_batch_ids(unified_view: pd.DataFrame) -> pd.Series:
    part_type_changed = unified_view["part_type"].ne(unified_view["part_type"].shift())
    batch_number = part_type_changed.cumsum()
    return "BATCH_" + batch_number.astype(str).str.zfill(3)


def _add_quality_features(unified_view: pd.DataFrame) -> pd.DataFrame:
    df = unified_view.copy()

    batch_stats = df.groupby("production_batch_id").agg(
        batch_pressure_mean=("max_pressure", "mean"),
        batch_pressure_std=("max_pressure", "std"),
        batch_temperature_mean=("casting_temperature_C", "mean"),
        batch_temperature_std=("casting_temperature_C", "std"),
        batch_silicon_mean=("silicon_content_percent", "mean"),
    )

    df = df.merge(batch_stats, on="production_batch_id", how="left")

    df["pressure_zscore_in_batch"] = (
        (df["max_pressure"] - df["batch_pressure_mean"]) / df["batch_pressure_std"].replace(0, np.nan)
    )
    df["temperature_zscore_in_batch"] = (
        (df["casting_temperature_C"] - df["batch_temperature_mean"])
        / df["batch_temperature_std"].replace(0, np.nan)
    )

    silicon_drift = df["silicon_content_percent"].diff().abs()
    df["silicon_drift_alert"] = silicon_drift.gt(0.15)
    df["pressure_outlier"] = df["pressure_zscore_in_batch"].abs().gt(2.0).fillna(False)
    df["temperature_outlier"] = df["temperature_zscore_in_batch"].abs().gt(2.0).fillna(False)
    df["missing_alignment_alert"] = df[
        ["max_pressure", "casting_temperature_C", "silicon_content_percent"]
    ].isna().any(axis=1)

    temp_stability = (
        df.groupby("production_batch_id")["casting_temperature_C"].transform("std").fillna(0)
    )
    pressure_stability = df.groupby("production_batch_id")["max_pressure"].transform("std").fillna(0)

    df["temperature_stability_index"] = (100 - temp_stability.clip(0, 100)).round(2)
    df["quality_alert_count"] = df[
        [
            "silicon_drift_alert",
            "pressure_outlier",
            "temperature_outlier",
            "missing_alignment_alert",
        ]
    ].sum(axis=1)
    df["unified_part_quality_index"] = (
        100
        - df["quality_alert_count"] * 20
        - pressure_stability.fillna(0).clip(0, 10) * 2
        - temp_stability.fillna(0).clip(0, 30)
    ).clip(0, 100).round(1)

    return df


def _plot_process_alignment(df: pd.DataFrame, pressure_data_df: pd.DataFrame, silicon_data_df: pd.DataFrame) -> None:
    sample = df.sort_values("cycle_start_timestamp").head(30).copy()
    silicon_plot = silicon_data_df.copy()
    silicon_time_col = "timestamp" if "timestamp" in silicon_plot.columns else "silicon_timestamp"
    silicon_value_col = (
        "furnace_silicon_content"
        if "furnace_silicon_content" in silicon_plot.columns
        else "silicon_content_percent"
    )
    silicon_plot[silicon_time_col] = pd.to_datetime(silicon_plot[silicon_time_col])

    fig, axes = plt.subplots(2, 2, figsize=(16, 11))
    fig.suptitle("Core Unified View - Process Alignment", fontsize=16, fontweight="bold")

    axes[0, 0].plot(df["cycle_start_timestamp"], df["max_pressure"], label="Max pressure", color="#2563eb")
    axes[0, 0].scatter(
        df["cycle_start_timestamp"],
        df["casting_temperature_C"] / 150,
        label="Casting temp scaled",
        color="#dc2626",
        s=20,
        alpha=0.7,
    )
    axes[0, 0].step(
        df["cycle_start_timestamp"],
        df["silicon_content_percent"],
        where="post",
        label="Silicon %",
        color="#047857",
    )
    axes[0, 0].set_title("Timeline Alignment Chart")
    axes[0, 0].set_xlabel("Part production timestamp")
    axes[0, 0].set_ylabel("Aligned process signals")
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.25)

    for row_number, (_, row) in enumerate(sample.iterrows()):
        start = mdates.date2num(row["cycle_start_timestamp"])
        duration_days = row["pressure_duration_min"] / (60 * 24)
        axes[0, 1].barh(row_number, duration_days, left=start, color="#94a3b8", edgecolor="#475569")
        axes[0, 1].scatter(
            mdates.date2num(row["peak_pressure_timestamp"]),
            row_number,
            color="#dc2626",
            marker="^",
            s=35,
            label="Peak pressure" if row_number == 0 else None,
        )
        if pd.notna(row.get("temperature_timestamp")):
            axes[0, 1].scatter(
                mdates.date2num(row["temperature_timestamp"]),
                row_number,
                color="#f59e0b",
                marker="o",
                s=28,
                label="Temperature" if row_number == 0 else None,
            )
    axes[0, 1].set_title("Cycle Gantt Chart")
    axes[0, 1].set_yticks(range(len(sample)))
    axes[0, 1].set_yticklabels(sample["unique_part_identifier"], fontsize=8)
    axes[0, 1].xaxis_date()
    axes[0, 1].xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    axes[0, 1].set_xlabel("Cycle time")
    axes[0, 1].legend()
    axes[0, 1].grid(True, axis="x", alpha=0.25)

    scatter = axes[1, 0].scatter(
        df["casting_temperature_C"],
        df["max_pressure"],
        c=df["silicon_content_percent"],
        cmap="viridis",
        s=45,
        alpha=0.75,
    )
    axes[1, 0].set_title("Pressure vs Temperature Scatter Plot")
    axes[1, 0].set_xlabel("Casting temperature (C)")
    axes[1, 0].set_ylabel("Max pressure")
    axes[1, 0].grid(True, alpha=0.25)
    plt.colorbar(scatter, ax=axes[1, 0], label="Silicon content (%)")

    axes[1, 1].plot(
        silicon_plot[silicon_time_col],
        silicon_plot[silicon_value_col],
        marker="o",
        color="#047857",
        label="Furnace silicon readings",
    )
    axes[1, 1].scatter(
        df["cycle_start_timestamp"],
        df["silicon_content_percent"],
        s=20,
        alpha=0.45,
        color="#2563eb",
        label="Applied to parts",
    )
    axes[1, 1].set_title("Silicon Content Trend Line")
    axes[1, 1].set_xlabel("Production time")
    axes[1, 1].set_ylabel("Silicon content (%)")
    axes[1, 1].legend()
    axes[1, 1].grid(True, alpha=0.25)

    fig.autofmt_xdate()
    plt.tight_layout()
    plt.savefig(OUTPUT_ALIGNMENT_DASHBOARD, dpi=150, bbox_inches="tight")
    plt.close(fig)


def _plot_quality_dashboard(df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(16, 11))
    fig.suptitle("Core Unified View - Quality and Performance Insights", fontsize=16, fontweight="bold")

    pivot = df.pivot_table(
        index="part_type",
        columns="production_hour",
        values="time_to_peak_min",
        aggfunc="mean",
    )
    heatmap = axes[0, 0].imshow(pivot.fillna(pivot.mean().mean()), aspect="auto", cmap="magma")
    axes[0, 0].set_title("Heatmap of Time-to-Peak Pressure")
    axes[0, 0].set_xlabel("Production hour")
    axes[0, 0].set_ylabel("Part type")
    axes[0, 0].set_xticks(range(len(pivot.columns)))
    axes[0, 0].set_xticklabels(pivot.columns)
    axes[0, 0].set_yticks(range(len(pivot.index)))
    axes[0, 0].set_yticklabels(pivot.index)
    plt.colorbar(heatmap, ax=axes[0, 0], label="Minutes")

    normal = df[~(df["pressure_outlier"] | df["temperature_outlier"])]
    outliers = df[df["pressure_outlier"] | df["temperature_outlier"]]
    axes[0, 1].scatter(
        normal["casting_temperature_C"],
        normal["max_pressure"],
        color="#64748b",
        alpha=0.55,
        label="In batch range",
    )
    axes[0, 1].scatter(
        outliers["casting_temperature_C"],
        outliers["max_pressure"],
        color="#dc2626",
        marker="x",
        s=70,
        label="Outlier",
    )
    axes[0, 1].set_title("Outlier Highlighting")
    axes[0, 1].set_xlabel("Casting temperature (C)")
    axes[0, 1].set_ylabel("Max pressure")
    axes[0, 1].legend()
    axes[0, 1].grid(True, alpha=0.25)

    batch_consistency = df.groupby("production_batch_id").agg(
        pressure_std=("max_pressure", "std"),
        temperature_std=("casting_temperature_C", "std"),
        part_count=("unique_part_identifier", "count"),
    )
    axes[1, 0].bar(batch_consistency.index, batch_consistency["pressure_std"], color="#2563eb", alpha=0.75)
    axes[1, 0].set_title("Batch Consistency Dashboard")
    axes[1, 0].set_xlabel("Batch")
    axes[1, 0].set_ylabel("Pressure std dev")
    axes[1, 0].tick_params(axis="x", rotation=60)
    axes[1, 0].grid(True, axis="y", alpha=0.25)

    efficiency = df.groupby("part_type").agg(
        avg_minutes_to_peak=("time_to_peak_min", "mean"),
        avg_quality_index=("unified_part_quality_index", "mean"),
    )
    axes[1, 1].bar(
        efficiency.index,
        efficiency["avg_minutes_to_peak"],
        color="#f59e0b",
        alpha=0.8,
        label="Avg min to peak",
    )
    axes_twin = axes[1, 1].twinx()
    axes_twin.plot(
        efficiency.index,
        efficiency["avg_quality_index"],
        color="#047857",
        marker="o",
        linewidth=2,
        label="Quality index",
    )
    axes[1, 1].set_title("Efficiency Metrics")
    axes[1, 1].set_xlabel("Part type")
    axes[1, 1].set_ylabel("Minutes")
    axes_twin.set_ylabel("Quality index")
    axes[1, 1].tick_params(axis="x", rotation=30)
    axes[1, 1].grid(True, axis="y", alpha=0.25)

    plt.tight_layout()
    plt.savefig(OUTPUT_QUALITY_DASHBOARD, dpi=150, bbox_inches="tight")
    plt.close(fig)


def _plot_legacy_analysis(df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(3, 2, figsize=(15, 12))
    fig.suptitle("Manufacturing Process Analysis - Unified View", fontsize=16, fontweight="bold")

    axes[0, 0].scatter(df["cycle_start_timestamp"], df["max_pressure"], alpha=0.6, s=20)
    axes[0, 0].set_title("Max Pressure Over Time")
    axes[0, 0].set_xlabel("Production Time")
    axes[0, 0].set_ylabel("Max Pressure")
    axes[0, 0].grid(True, alpha=0.3)

    part_types = df["part_type"].dropna().unique()
    temp_data = [df[df["part_type"] == part_type]["casting_temperature_C"].dropna() for part_type in part_types]
    axes[0, 1].boxplot(temp_data, labels=part_types)
    axes[0, 1].set_title("Casting Temperature by Part Type")
    axes[0, 1].set_xlabel("Part Type")
    axes[0, 1].set_ylabel("Temperature (C)")
    axes[0, 1].tick_params(axis="x", rotation=45)
    axes[0, 1].grid(True, alpha=0.3)

    axes[1, 0].hist(df["time_to_peak_min"].dropna(), bins=20, alpha=0.7, edgecolor="black")
    axes[1, 0].axvline(
        df["time_to_peak_min"].mean(),
        color="red",
        linestyle="--",
        label=f"Mean: {df['time_to_peak_min'].mean():.1f} min",
    )
    axes[1, 0].set_title("Time to Peak Pressure Distribution")
    axes[1, 0].set_xlabel("Time to Peak (minutes)")
    axes[1, 0].set_ylabel("Frequency")
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3)

    axes[1, 1].plot(
        df["cycle_start_timestamp"],
        df["silicon_content_percent"],
        marker="o",
        markersize=3,
        linewidth=1,
        alpha=0.7,
    )
    axes[1, 1].set_title("Silicon Content Over Production Time")
    axes[1, 1].set_xlabel("Production Time")
    axes[1, 1].set_ylabel("Silicon Content (%)")
    axes[1, 1].grid(True, alpha=0.3)

    scatter = axes[2, 0].scatter(
        df["casting_temperature_C"],
        df["max_pressure"],
        c=df["time_to_peak_min"],
        cmap="viridis",
        alpha=0.6,
        s=30,
    )
    axes[2, 0].set_title("Max Pressure vs Casting Temperature")
    axes[2, 0].set_xlabel("Casting Temperature (C)")
    axes[2, 0].set_ylabel("Max Pressure")
    axes[2, 0].grid(True, alpha=0.3)
    plt.colorbar(scatter, ax=axes[2, 0], label="Time to Peak (min)")

    hourly_production = df.groupby(df["cycle_start_timestamp"].dt.floor("H")).size()
    axes[2, 1].plot(hourly_production.index, hourly_production.values, marker="o", linewidth=2)
    axes[2, 1].set_title("Production Rate (Parts per Hour)")
    axes[2, 1].set_xlabel("Time (Hourly)")
    axes[2, 1].set_ylabel("Number of Parts")
    axes[2, 1].tick_params(axis="x", rotation=45)
    axes[2, 1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(OUTPUT_ANALYSIS_DASHBOARD, dpi=150, bbox_inches="tight")
    plt.close(fig)


def build_unified_view() -> pd.DataFrame:
    """
    Build the Core Unified View.

    Each row represents one unique_part_identifier and carries aligned production,
    pressure, casting temperature, silicon chemistry, quality, and KPI features.
    """
    print("Loading data files...")
    production_data_df, pressure_data_df, temperature_data_df, silicon_data_df = _load_source_data()
    print("Data loaded successfully")

    print("\n1. Processing production data...")
    production_data_df = production_data_df.copy()
    production_data_df["cycle_start_timestamp"] = pd.to_datetime(
        production_data_df["cycle_start_timestamp"]
    )
    production_data_df = production_data_df.sort_values("cycle_start_timestamp")
    production_data_df["part_type"] = production_data_df["PART_TYPE"].ffill()

    unified_view = production_data_df[
        ["unique_part_identifier", "cycle_start_timestamp", "part_type"]
    ].copy()
    unified_view["production_batch_id"] = _build_batch_ids(unified_view)
    print(f"Processed {len(unified_view)} unique parts")

    print("\n2. Extracting pressure cycle metrics...")
    pressure_summary_df = _pressure_metrics(pressure_data_df)
    unified_view = unified_view.merge(
        pressure_summary_df,
        on="unique_part_identifier",
        how="left",
        validate="one_to_one",
    )
    print(f"Added pressure metrics for {len(pressure_summary_df)} parts")

    print("\n3. Aligning casting temperature...")
    temperature_data_df = temperature_data_df.copy()
    temperature_data_df["timestamp"] = pd.to_datetime(temperature_data_df["timestamp"])
    temperature_data_df = temperature_data_df.sort_values("timestamp").rename(
        columns={
            "timestamp": "temperature_timestamp",
            "casting_temperature": "casting_temperature_C",
        }
    )
    unified_view = pd.merge_asof(
        unified_view.sort_values("cycle_start_timestamp"),
        temperature_data_df,
        left_on="cycle_start_timestamp",
        right_on="temperature_timestamp",
        direction="nearest",
        tolerance=pd.Timedelta("20 minutes"),
    )
    print(f"Matched temperature for {unified_view['casting_temperature_C'].notna().sum()} parts")

    print("\n4. Aligning silicon content...")
    silicon_data_df = silicon_data_df.copy()
    silicon_data_df["timestamp"] = pd.to_datetime(silicon_data_df["timestamp"])
    silicon_data_df = silicon_data_df.sort_values("timestamp").rename(
        columns={
            "timestamp": "silicon_timestamp",
            "furnace_silicon_content": "silicon_content_percent",
        }
    )

    unified_view = pd.merge_asof(
        unified_view.sort_values("cycle_start_timestamp"),
        silicon_data_df,
        left_on="cycle_start_timestamp",
        right_on="silicon_timestamp",
        direction="backward",
        tolerance=pd.Timedelta("4 hours"),
    )
    print(f"Matched silicon content for {unified_view['silicon_content_percent'].notna().sum()} parts")

    print("\n5. Adding KPIs, alerts, and review fields...")
    unified_view["production_hour"] = unified_view["cycle_start_timestamp"].dt.hour
    unified_view["production_day"] = unified_view["cycle_start_timestamp"].dt.date
    unified_view = _add_quality_features(unified_view)

    column_order = [
        "unique_part_identifier",
        "part_type",
        "production_batch_id",
        "cycle_start_timestamp",
        "pressure_cycle_end_timestamp",
        "max_pressure",
        "peak_pressure_timestamp",
        "time_to_peak_min",
        "avg_pressure",
        "pressure_variance",
        "pressure_duration_min",
        "casting_temperature_C",
        "temperature_timestamp",
        "silicon_content_percent",
        "silicon_timestamp",
        "pressure_outlier",
        "temperature_outlier",
        "silicon_drift_alert",
        "missing_alignment_alert",
        "temperature_stability_index",
        "unified_part_quality_index",
        "production_hour",
        "production_day",
    ]
    unified_view = unified_view[[column for column in column_order if column in unified_view.columns]]

    print("\nCRITICAL REVIEW OF UNIFIED VIEW")
    print("=" * 50)
    print(f"Total parts: {len(unified_view)}")
    print(
        "Date range: "
        f"{unified_view['cycle_start_timestamp'].min()} to {unified_view['cycle_start_timestamp'].max()}"
    )
    print("\nMissing values:")
    missing = unified_view.isnull().sum()
    print(missing[missing > 0])
    print("\nQuality alerts:")
    alert_columns = [
        "pressure_outlier",
        "temperature_outlier",
        "silicon_drift_alert",
        "missing_alignment_alert",
    ]
    print(unified_view[alert_columns].sum().astype(int))
    print("\nEfficiency metrics by part type:")
    print(
        unified_view.groupby("part_type")
        .agg(
            avg_minutes_to_peak=("time_to_peak_min", "mean"),
            avg_quality_index=("unified_part_quality_index", "mean"),
            avg_temperature_stability=("temperature_stability_index", "mean"),
        )
        .round(2)
    )

    print("\n6. Generating dashboard layers...")
    _plot_legacy_analysis(unified_view)
    _plot_process_alignment(unified_view, pressure_data_df, silicon_data_df)
    _plot_quality_dashboard(unified_view)

    unified_view.to_csv(OUTPUT_UNIFIED_CSV, index=False)
    unified_view.to_parquet(OUTPUT_UNIFIED_PARQUET, index=False)
    unified_view[
        unified_view[
            [
                "pressure_outlier",
                "temperature_outlier",
                "silicon_drift_alert",
                "missing_alignment_alert",
            ]
        ].any(axis=1)
    ].to_csv(OUTPUT_QUALITY_CSV, index=False)

    print("\n" + "=" * 50)
    print("CORE UNIFIED VIEW CREATED SUCCESSFULLY")
    print("=" * 50)
    print(f"Output: {OUTPUT_UNIFIED_CSV}")
    print(f"Output: {OUTPUT_UNIFIED_PARQUET}")
    print(f"Output: {OUTPUT_QUALITY_CSV}")
    print(f"Output: {OUTPUT_ANALYSIS_DASHBOARD}")
    print(f"Output: {OUTPUT_ALIGNMENT_DASHBOARD}")
    print(f"Output: {OUTPUT_QUALITY_DASHBOARD}")
    print(f"Final unified view shape: {unified_view.shape}")

    return unified_view


if __name__ == "__main__":
    unified_df = build_unified_view()

    if not unified_df.empty:
        print("\nSample of final unified view:")
        print(unified_df.head().to_string())

        print("\nColumn descriptions:")
        for col in unified_df.columns:
            non_null = unified_df[col].notna().sum()
            dtype = unified_df[col].dtype
            print(f"  - {col}: {dtype}, {non_null}/{len(unified_df)} non-null")
