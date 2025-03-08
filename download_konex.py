from datetime import datetime, timedelta
from tqdm import tqdm
import pandas as pd
import requests
import os
import time
import json

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

url = "http://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd"

MAP_ISSUE_AND_DATE_TO_INDUSTRY = dict()

params = {
    "bld": "dbms/MDC/STAT/standard/MDCSTAT03402",
        "locale": "en",
        "mktTpCd": "6",
        "tboxisuSrtCd_finder_listisu0_5": "ALL",
        "isuSrtCd": "ALL",
        "isuSrtCd2": "ALL",
        "codeNmisuSrtCd_finder_listisu0_5": "",
        "param1isuSrtCd_finder_listisu0_5": "",
        "sortType": "A",
        "sectTpCd": "ALL",
        "parval": "ALL",
        "mktcap": "ALL",
        "acntclsMm": "ALL",
        "tboxmktpartcNo_finder_designadvser0_5": "",
        "mktpartcNo": "",
        "mktpartcNo2": "",
        "codeNmmktpartcNo_finder_designadvser0_5": "",
        "param1mktpartcNo_finder_designadvser0_5": "",
        "condListShrs": "1",
        "listshrs": "",
        "listshrs2": "",
        "condCap": "1",
        "cap": "",
        "cap2": "",
        "share": "1",
        "money": "1",
        "csvxls_isNo": "false"
}

MAP_KONEX_ISSUE_AND_DATE_TO_INDUSTRY = {}

# Assuming date_list is already generated
try:
    # KRX API endpoint for foreign ownership data
    response = session.get(url, params=params, timeout=30)
    response.raise_for_status()

    obj: dict = response.json()
    if "block0" in obj.keys() or "block2" in obj.keys(): raise Exception("Other blocks")

    for issue in obj["block1"]:
        key = issue['REP_ISU_SRT_CD']
        industry = "KONEX: "+ issue['IND_NM']

        if key in MAP_KONEX_ISSUE_AND_DATE_TO_INDUSTRY:
            raise Exception("Code should only exit once")

        MAP_KONEX_ISSUE_AND_DATE_TO_INDUSTRY[key] = industry

except Exception as e:
    print(f"Error processing date {params}: {str(e)}")
    print(f"Exception details: {repr(e)}")
    print(f"Exception traceback:")
    import traceback
    traceback.print_exc()

with open("MAP_KONEX_ISSUE_AND_DATE_TO_INDUSTRY.json","w") as f:
    json.dump(MAP_KONEX_ISSUE_AND_DATE_TO_INDUSTRY,f)
