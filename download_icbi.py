from datetime import datetime, timedelta
from tqdm import tqdm
import pandas as pd
import requests
import os
import time
import json

def KOSPI(date):
    return {
        "bld": "dbms/MDC/STAT/standard/MDCSTAT03901",  # Foreign ownership by issue endpoint
        "locale": "en",
        "trdDd": date.strftime("%Y%m%d"),                             # Trading date in YYYYMMDD format
        "mktId": "STK",                                # Get data for all stocks
        "money": "1",
        "csvxls_isNo": "false",
    }

def KOSDAQ(date):
    return {
        "bld": "dbms/MDC/STAT/standard/MDCSTAT03901",  # Foreign ownership by issue endpoint
        "locale": "en",
        "trdDd": date.strftime("%Y%m%d"),                             # Trading date in YYYYMMDD format
        "mktId": "KSQ",                                # Get data for all stocks
        "segTpCd": "ALL",
        "money": "1",
        "csvxls_isNo": "false",
    }

type_func = [KOSPI,KOSDAQ]


def get_all_days_of_month_as_str(year,month)->list[str]:
    all_in_month = []
    # Get the last day of the month
    if month == 12:
        next_month = datetime(year + 1, 1, 1)
    else:
        next_month = datetime(year, month + 1, 1)
    last_day = (next_month - timedelta(days=1)).day

    # Add all days in the month
    for day in range(1, last_day + 1):
        all_in_month.append(datetime(year, month, day).strftime("%Y%m%d"))

    return all_in_month

# Start date
start_date = datetime(2005, 10, 4)
# Current date (to avoid future dates)
current_date = datetime.now()
# Generate weekly dates from start_date to current_date
dates = [
    (datetime(2005, 10, 4), datetime(2005, 10, 13),get_all_days_of_month_as_str(2005,10)),
    (datetime(2005, 11, 1), datetime(2005, 11, 13),get_all_days_of_month_as_str(2005,11)),
    (datetime(2005, 12, 1), datetime(2005, 12, 13),get_all_days_of_month_as_str(2005,12))
]

# Add remaining months with the first weekday of each month
for year in range(start_date.year+1, current_date.year+1):
    for month in range(1, 13):
        first_weekday = datetime(year, month, 1)
        other_date = datetime(year, month, 13)
        dates.append((first_weekday, other_date, get_all_days_of_month_as_str(year, month)))

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

# Create a list of all combinations of type_func and dates
params_list = [(dayinmonth, func(date), func(dateOther)) for func in type_func for (date,dateOther,dayinmonth) in dates]

url = "http://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd"

MAP_ISSUE_AND_DATE_TO_INDUSTRY = dict()

# Assuming date_list is already generated
for (days_in_month, params, paramsOther) in tqdm(params_list, desc="Requesting Industray classifiaciton for dates", unit="date"):
    try:
        # KRX API endpoint for foreign ownership data
        response = session.get(url, params=params, timeout=30)
        response.raise_for_status()

        obj: dict = response.json()
        if "block0" in obj.keys() or "block2" in obj.keys(): raise Exception("Other blocks")

        time.sleep(2)

        # KRX API endpoint for foreign ownership data
        responseOther = session.get(url, params=paramsOther, timeout=30)
        responseOther.raise_for_status()

        objOther: dict = responseOther.json()
        if "block0" in objOther.keys() or "block2" in objOther.keys(): raise Exception("Other blocks")

        for issue in obj["block1"]:
            key = issue['ISU_SRT_CD']
            industry = issue['IDX_IND_NM']

            if not key in MAP_ISSUE_AND_DATE_TO_INDUSTRY:
                MAP_ISSUE_AND_DATE_TO_INDUSTRY[key] = dict()

            for d in days_in_month[:12]:
                MAP_ISSUE_AND_DATE_TO_INDUSTRY[key][d] = industry

        for issue in objOther["block1"]:
            key = issue['ISU_SRT_CD']
            industry = issue['IDX_IND_NM']

            if not key in MAP_ISSUE_AND_DATE_TO_INDUSTRY:
                MAP_ISSUE_AND_DATE_TO_INDUSTRY[key] = dict()

            for d in days_in_month[12:]:
                MAP_ISSUE_AND_DATE_TO_INDUSTRY[key][d] = industry

        #print(f"Success processing date {date}")
    except Exception as e:
        print(f"Error processing date {params}: {str(e)}")
        print(f"Exception details: {repr(e)}")
        print(f"Exception traceback:")
        import traceback
        traceback.print_exc()

    time.sleep(2)

with open("MAP_ISSUE_AND_DATE_TO_INDUSTRY.json","w") as f:
    json.dump(MAP_ISSUE_AND_DATE_TO_INDUSTRY,f)
