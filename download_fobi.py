from datetime import datetime, timedelta
from tqdm import tqdm
import pandas as pd
import requests
import os
import time

start_date = datetime(2005, 10, 4) # The first data to check
end_date = datetime.now()

date_list = [(start_date + timedelta(days=i)) for i in range((end_date - start_date).days + 1)]
# Filter date_list to only include weekdays (Monday=0, Friday=4)
date_list = [date.strftime("%Y%m%d") for date in date_list if date.weekday() < 5]


# Create a persistent session for all requests
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Referer": "http://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd?menuId=MDC0201",
    "Connection": "keep-alive"
})

# Configure session for connection pooling
adapter = requests.adapters.HTTPAdapter(
    pool_connections=10,
    pool_maxsize=10,
    max_retries=3
)
session.mount('http://', adapter)
session.mount('https://', adapter)

now = datetime.now()
start_of_week = (now - timedelta(days=now.weekday())).strftime("%Y%m%d")
end_of_week = (now + timedelta(days=4-now.weekday())).strftime("%Y%m%d")

date_todo = []
for date in date_list:
    if os.path.exists(f"{date}.json"):
        print(f"Skip processing date {date}")
        continue

    date_todo.append(date)

# Assuming date_list is already generated
for date in tqdm(date_todo, desc="Requesting data for days", unit="day"):
    with open(f"{date}.json", 'w') as f:
        # If the file doesn't exist, fetch the data
        try:
            # KRX API endpoint for foreign ownership data
            url = "http://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd"

            # Parameters for foreign ownership by issue stock
            params = {
            "bld": "dbms/MDC/STAT/standard/MDCSTAT03701",  # Foreign ownership by issue endpoint
            "locale": "en",
            "trdDd": date,                             # Trading date in YYYYMMDD format
            "mktId": "ALL",                                # Get data for all stocks
            "share": "1",                                  # Include share data
            "searchType": "1",                                  # Include monetary values
            "csvxls_isNo": "false",
            "param1isuCd_finder_stkisu0_1": "ALL",
            "strtDd": start_of_week,  # Start date of current week
            "endDd": end_of_week,    # End date of current week

            }


            response = session.get(url, params=params, timeout=30)

            f.write(response.text)

            response.raise_for_status()

            #print(f"Success processing date {date}")
        except Exception as e:
            print(f"Error processing date {date}: {e}")

    time.sleep(10)
