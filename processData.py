# IMPORT MODULES
import os
import importlib.util
from pathlib import Path
import inspect

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from datetime import datetime, timedelta
import argparse

import pandas as pd

def parseArgs():
    # cli arguments
    parser = argparse.ArgumentParser(description="Calculates FFTs from datastream bucket")
    parser.add_argument("starttime", type=str, help="ISO format start timestamp in UTC time")
    parser.add_argument("endtime", type=str, help="ISO format end timestamp in UTC time")
    parser.add_argument("-m", "--module", type=str, default=[], action="append", help="Specify modules to run (default is all)")

    args = parser.parse_args()

    start_time = datetime.fromisoformat(args.starttime)
    end_time = datetime.fromisoformat(args.endtime)

    return start_time, end_time, args.module

def process(start_time, end_time, modules = []):
    # hardcoded parameters
    df_chunk_size = 128  # Don't change this - the standard HTTP request chunk size
    bucket_prefix = "paros-"

    influxdb_sensorid_tagkey = "sensor_id"

    influxdb_apikey = ""
    influxdb_org = "paros"
    influxdb_url = "https://influxdb.paros.casa.umass.edu/"

    # get influxdb api key
    with open('./INFLUXAPIKEY', 'r') as file:
        influxdb_apikey = file.read().rstrip()

    # modify time objects
    start_time = start_time.replace(second = 0, microsecond = 0)
    end_time = end_time.replace(second = 0, microsecond = 0)

    # create influxdb client and API objects
    influxdb_client = InfluxDBClient(
        url=influxdb_url,
        token=influxdb_apikey,
        org=influxdb_org
    )

    influxdb_write_api = influxdb_client.write_api(write_options=SYNCHRONOUS)
    influxdb_query_api = influxdb_client.query_api()

    # Create string to be used for timestamp range query
    idb_range_str = "range(start: " + start_time.isoformat() + "Z, stop: " + end_time.isoformat() + "Z)"

    # Path to the 'modules' directory relative to the current file
    modules_path = Path(__file__).parent / 'modules'

    # Iterate over each file in the 'modules' directory
    for file in modules_path.iterdir():
        if file.suffix == '.py' and file.is_file():
            # Import the Python file
            module_name = file.stem
            module_name_trimmed = module_name.split("_")[1]

            if len(modules) > 0 and module_name_trimmed not in modules:
                # skip this module
                continue

            spec = importlib.util.spec_from_file_location(module_name, file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Check if the module has a main() function and run it with two arguments
            if hasattr(module, "main"):
                print(f"Running module {module_name_trimmed}...")
                print()

                params = list(inspect.signature(module.main).parameters)
                input_bucket_name = bucket_prefix + params[0]
                output_bucket_name = bucket_prefix + module_name_trimmed

                print(f"Input data: {input_bucket_name}")
                print(f"Output data: {output_bucket_name}")
                print()

                # ! TODO check if buckets exist

                # get input data from influxdb
                # 1. get each measurement in bucket (each measurement is a box)
                idb_measurement_query = \
                    'import "influxdata/influxdb/schema"'\
                    'schema.measurements('\
                    'bucket: "' + input_bucket_name + '",'\
                    'start: ' + start_time.isoformat() + 'Z,'\
                    'stop: ' + end_time.isoformat() + 'Z'\
                    ')'

                measurement_result = influxdb_query_api.query(org=influxdb_org, query=idb_measurement_query)
                measurement_list = []
                for table in measurement_result:
                    for record in table.records:
                        measurement_list.append(record.get_value())

                for measurement in measurement_list:
                    idb_deviceid_query = \
                        'import "influxdata/influxdb/schema"'\
                        'schema.tagValues('\
                        'bucket: "' + input_bucket_name + '",'\
                        'predicate: (r) => r["_measurement"] == "' + measurement + '",'\
                        'tag: "' + influxdb_sensorid_tagkey + '",'\
                        'start: ' + start_time.isoformat() + 'Z,'\
                        'stop: ' + end_time.isoformat() + 'Z'\
                        ')'

                    device_result = influxdb_query_api.query(org=influxdb_org, query=idb_deviceid_query)

                    device_list = []
                    for table in device_result:
                        for record in table.records:
                            device_list.append(record.get_value())

                    idb_query = 'from(bucket:"' + input_bucket_name + '")'\
                        '|> ' + idb_range_str + ''\
                        '|> filter(fn: (r) => r["_measurement"] == "' + measurement + '")'

                    for device in device_list:
                        # query for that device only
                        print(f"Running query for box {measurement} and sensor {device} between {start_time.isoformat()} and {end_time.isoformat()}...")
                        cur_query = idb_query + \
                            '|> filter(fn: (r) => r["' + influxdb_sensorid_tagkey + '"] == "' + device + '")'

                        cur_result = influxdb_query_api.query(org=influxdb_org, query=cur_query)

                        data = [{"timestamp": record.get_time(), "field": record.get_field(), "value": record.get_value()} for table in cur_result for record in table.records]
                        df = pd.DataFrame(data)
                        df = df.pivot(index="timestamp", columns="field", values="value")

                        # we must check if there are any missing values:
                        time_deltas = df.index.to_series().diff()

                        if time_deltas.nunique() > 1:
                            print("Found missing data, skipping")
                            continue

                        # run module
                        print("Query Done")
                        print()

                        print(f"Running module {module_name_trimmed} on sensor {device}...")
                        output = module.main(df)
                        print("Module Done")
                        print()
                        
                        output[influxdb_sensorid_tagkey] = device

                        # Split up Dataframe into Batch Chunks
                        df_mem_usage = df.memory_usage(index=True, deep=True).sum()
                        df_chunk_size_bytes = df_chunk_size * 1024
                        df_chunksize = int((df_chunk_size_bytes / df_mem_usage) * len(df))
                        
                        print(f"Using a dataframe chunk size of {df_chunksize} rows")
                        print()

                        output_chunks = [output[i:i + df_chunksize] for i in range(0, output.shape[0], df_chunksize)]
                        total_chunks = len(output_chunks)

                        print("Starting Upload to InfluxDB...")
                        for i,chunk in enumerate(output_chunks):
                            print(f"[{i + 1}/{total_chunks}]")
                            influxdb_write_api.write(output_bucket_name, influxdb_org, record=chunk, data_frame_measurement_name=measurement, data_frame_tag_columns=[influxdb_sensorid_tagkey], utc=True)
                        
                        print("Upload Done")
                        print()

                    print("OK")

def main():
    process(parseArgs())

if __name__ == "__main__":
    main()
