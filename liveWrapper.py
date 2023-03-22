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
    now = datetime.utcnow()

    delay_buffer = 15  # in minutes (set to cron top frequency)
    amount_to_process = 30  # in minutes (Cron should run every half of this value in minutes (if 10 then every 5 mins))

    start_time = now - timedelta(minutes = delay_buffer + amount_to_process)
    end_time = now - timedelta(minutes = delay_buffer)

    start_time = start_time.replace(microsecond = 0, second = 0)
    end_time = end_time.replace(microsecond = 0, second = 0)

    print("Running processing between these timestamps: ")
    print(f"Start Time: {start_time.isoformat()}")
    print(f"End Time: {end_time.isoformat()}")
    print()

    processData.process(start_time, end_time)

if __name__ == "__main__":
    main()
