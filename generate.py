import subprocess
from datetime import datetime, timedelta

import processData

def main():
    # hardcoded arguments
    influxdb_apikey = ""
    influxdb_org = "paros"
    influxdb_url = "https://influxdb.paros.casa.umass.edu/"

    # get influxdb api key
    with open('./INFLUXAPIKEY', 'r') as file:
        influxdb_apikey = file.read().rstrip()

    # Calcualte range timestamps
    start_time = datetime(11,21,2022,0,0,0)
    end_time = datetime(3,29,2023,0,0,0)

    step_size = 1  # hours between each step

    cur_starttime = start_datetime
    cur_endtime = start_datetime + timedelta(hours = step_size * 2)

    step = timedelta(hours = step_size)

    while cur_endtime <= end_datetime:
        print(f"Running {cur_starttime.isoformat()} to {cur_endtime.isoformat()}")
        processData.process(cur_starttime, cur_endtime, "live")

        cur_starttime += step
        cur_endtime += step

if __name__ == "__main__":
    main()
