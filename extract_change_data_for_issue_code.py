from datetime import datetime
from io import TextIOBase
from pandas.io.common import TextIOWrapper
from tqdm import tqdm
import pandas as pd
import requests
import os
import time
import json

json_files = []
data_dir = "data"
for filename in os.listdir(data_dir):
    if filename.endswith(".json"):
        json_files.append(os.path.join(data_dir, filename))

json_files.sort()

class MICT_VAL:
    def __init__(self, code, date, name) -> None:
        self.code = code
        self.current_name = name
        self.changes = [(date, name)]

    def proc(self, date: str, name) -> str | None:
        if name == self.current_name: return None

        self.current_name = name
        self.changes.append((date, name))

        return date

class MICTC:
    def __init__(self) -> None:
        self.MAP_ISSUE_CODE_TO_CHANGE: dict[str,MICT_VAL] = dict()
        self.date_set = set()

    def proc_row(self, date, row) -> None:
        code = row['ISU_SRT_CD']
        name = row['ISU_ABBRV']

        if not code in self.MAP_ISSUE_CODE_TO_CHANGE:
            self.MAP_ISSUE_CODE_TO_CHANGE[code] = MICT_VAL(code,date,name)
            self.date_set.add(date)

        cd = self.MAP_ISSUE_CODE_TO_CHANGE[code].proc(date,name)
        if cd != None:
            self.date_set.add(date)

    def write_to_file(self, file: TextIOBase):
        issue_to_change_dates = dict(map(lambda x: (x.code,x.changes),self.MAP_ISSUE_CODE_TO_CHANGE.values()))
        all_changes = list(self.date_set);

        all_changes.sort()

        obj = {
            "issue_to_change_dates": issue_to_change_dates,
            "all_change_dates": all_changes
        }

        json.dump(obj,file)

MAP = MICTC()

for json_file in tqdm(json_files, desc="Processing JSON files", unit="file"):
    date_str = os.path.splitext(os.path.basename(json_file))[0]

    BIGdata: dict = dict()
    with open(json_file, 'rb') as f:
        try:
            BIGdata = json.load(f)
        except Exception as e:
            print(f"Error in {json_file} - invalid JSON format: {e}")


    for row in BIGdata['output']:
        MAP.proc_row(date_str,row)

with open("name_changes.json","w") as f:
    MAP.write_to_file(f)
