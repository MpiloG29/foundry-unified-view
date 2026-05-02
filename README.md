# Devskiller Test - Core Unified View build

## PRELUDE
1. For any manufacturing plant, there are different processes involved in producing a single part.
This can be a pot, an engine block, a wheel, etc.

2. These processes happen at different times and need to be aligned.

3. Building a unified view aims to bring all these processes together to track the production 
of a single part - from start to end, as if all processes happened simultaneously.

4. Some data will need preprocessing to extract valuable features.

5. For this task consider this context:

    A certain foundry is producing some automotive parts and they would like to know
    the casting temperature, silicon content and furnace pressure relevant to each part,
    for a specific period of production.

    This data has been collected in the following dataframes:

    production_data_df: contains the unique_part_identifer, cycle_start_timestamp and PART_TYPE
    pressure_data_df: contains the pressure profile recorded by the pressure_sensor
    temperature_data_df: contains the casting Temperature
    silicon_data_df: contains the furnace_silicon_content

6. Use the unified.py script with the included parquet files for this exercise.


## OBJECTIVE
1. The objective is to build a unified view that will extract all relevant information for each part produced. 
You will have to build a dataframe where each row represents a single part and each column represents the relevant
data from each process that needs to be extracted and aligned.

2. You will have to execute the processing and alignment operations (merging) for four data sets and critically
review the outcome. Do not hesitate to share images and snippets of data to support your comments.
<img width="1756" height="1475" alt="final_dashboard" src="https://github.com/user-attachments/assets/3a48294f-16f2-4d84-9888-dc1d5cc38932" />

## CORE UNIFIED VIEW
The main output is `unified_manufacturing_view.csv` and `unified_manufacturing_view.parquet`.
It has one row per `unique_part_identifier`, creating a single source of truth with:

- `part_type`
- `production_batch_id`
- `cycle_start_timestamp`
- `max_pressure`
- `peak_pressure_timestamp`
- `time_to_peak_min`
- `casting_temperature_C`
- `temperature_timestamp`
- `silicon_content_percent`
- `silicon_timestamp`
- alert flags for pressure, temperature, silicon drift, and missing joins
- KPI fields such as `temperature_stability_index` and `unified_part_quality_index`

The silicon merge uses `pandas.merge_asof(..., direction="backward", tolerance="4 hours")`
because a furnace chemistry reading applies forward from the time it was recorded. Temperature
uses nearest-time matching within a 20-minute window because it is logged at the beginning of casting.

## DASHBOARD LAYERS
The scripts generate dashboard images that map to the requested analysis layers:

- `process_alignment_dashboard.png`: timeline alignment chart, cycle Gantt chart, pressure-temperature scatter, and silicon trend line.
- `quality_insights_dashboard.png`: time-to-peak heatmap, outlier highlighting, batch consistency, and efficiency metrics.
- `unified_view_analysis.png`: baseline manufacturing analysis dashboard.
- `final_dashboard.png`: executive summary dashboard created by `create_final_report_simple.py`.

## QUALITY AND ANOMALY DETECTION
The Core Unified View includes practical monitoring fields:

- `pressure_outlier`: pressure deviates from batch norms.
- `temperature_outlier`: temperature deviates from batch norms.
- `silicon_drift_alert`: silicon content changes sharply between aligned parts.
- `missing_alignment_alert`: pressure, temperature, or silicon alignment is missing.
- `unified_quality_alerts.csv`: exported subset of parts with at least one alert.

## MIND-BLOWING ADDITIONS INCLUDED AS DATA FOUNDATIONS
The current implementation prepares the data needed for richer interactive layers:

- Interactive replay mode: use `cycle_start_timestamp`, `peak_pressure_timestamp`,
  `temperature_timestamp`, and `silicon_timestamp` to animate each part lifecycle.
- Digital twin overlay: compare `max_pressure`, `time_to_peak_min`, and
  `casting_temperature_C` against ideal targets by part type or batch.
- Efficiency metrics: use grouped averages for `time_to_peak_min`,
  `temperature_stability_index`, and `unified_part_quality_index`.

Run the pipeline with:

```bash
python unified.py
python create_final_report_simple.py
```

## LIVE DASHBOARD
The deployable Dash app is in `dashboard_app.py`.

Features:

- Unified Part View: interactive table with filters for part type, batch, and date.
- Pressure Cycle Explorer: line chart with peak pressure markers.
- Temperature Stability Monitor: batch trend chart with stability index overlay.
- Silicon Content Overlay: step-line view of the silicon value applied to production cycles.
- Anomaly Alerts: highlighted rows and alert cards for pressure, temperature, silicon drift,
  and missing alignments.

Run locally:

```bash
python dashboard_app.py
```

Deploy on Render:

1. Push this repository to GitHub.
2. Create a new Render Web Service from the repo.
3. Render can use `render.yaml`, or set these manually:
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn dashboard_app:server`
4. Keep `unified_manufacturing_view.csv` in the repo, or let the app generate sample data on first startup.



## DATASETS
1. production_data_df:
Parts are produced per batch of the same product type. A part is produced every 30 minutes
and has a unique part identifier. Batches of the same product type are identified with the product 
type name which is logged on the control system when the type changes and will apply from the next part.



2. pressure_data_df:
During casting, the pressure senosr logs the exerted pressure every 10 seconds 
(the pressure increases during this time), until the casting is completed. The result is 
a pressure cycle that lasts for ~30 minutes and resets when casting is completed.
You will need to extract the maximum pressure reached for each cycle and the time elapsed (in minutes) from when to production cycle starts to the moment this peak is reached 


3. temperature_data_df:
The casting temperature is recorded at the beginning of the casting cycle (in the first 10 minutes)


4. silicon_data_df:
Bulk quantities of metal are melted in the furnace, and as a result, the chemistry remains
relatively similar for a few hours of production, and is therefore recorded less frequently.
The silicon in particular is recorded every ~4 hours, and should apply for the next 4 hours of production.


## RECOMMENDATIONS
1. Pandas and Matplotlib are the recommended packages proposed to be used for the exercise,
however you are free to use alternatives if you prefer.
