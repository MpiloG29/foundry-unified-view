# Devskiller Test - Unified View build

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
