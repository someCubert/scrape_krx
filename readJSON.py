import sqlite3
import json
import os
import tqdm
import datetime


COLUMN_MAP = {
  "ISU_SRT_CD": '"Issue code"',
  "ISU_ABBRV": '"Issue name"',
  "TDD_CLSPRC": '"Close"',
  "FLUC_TP_CD": '"UpDown"',
  "CMPPREVDD_PRC": '"Change"',
  "FLUC_RT": '"%Change"',
  "LIST_SHRS": '"No. of listed shares"',
  "FORN_HD_QTY": '"No. of shares of foreign ownership"',
  "FORN_SHR_RT": '"Foreign ownership ratio"',
  "FORN_ORD_LMT_QTY": '"Foreign ownership limit quantity"',
  "FORN_LMT_EXHST_RT": '"Exhaustion rate"'
}


conn = sqlite3.connect("foreign_ownership.db")
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS foreign_ownership 
            (date DATE,
             "Issue name" INTEGER,
             "Issue code" TEXT,
             "Close" REAL,
             "UpDown" TEXT,
             "Change" REAL,
             "%Change" REAL,
             "No. of listed shares" INTEGER,
             "No. of shares of foreign ownership" INTEGER,
             "Foreign ownership ratio" REAL,
             "Foreign ownership limit quantity" INTEGER,
             "Exhaustion rate" REAL,
             PRIMARY KEY (date, "Issue name"))''')


json_files = []
data_dir = "data"
for filename in os.listdir(data_dir):
    if filename.endswith(".json"):
        json_files.append(os.path.join(data_dir, filename))

for json_file in tqdm.tqdm(json_files, desc="Processing JSON files", unit="file"):
    date = None
    date_str = os.path.splitext(os.path.basename(json_file))[0]
    try:
        date = datetime.datetime.strptime(date_str, "%Y%m%d")
    except ValueError:
        print(f"Skipping {json_file} - invalid date format")
        continue
    
    BIGdata = None
    with open(json_file, 'rb') as f:
        try:
            BIGdata = json.load(f)
        except Exception as e:
            print(f"Error in {json_file} - invalid JSON format: {e}")
            

    for row in BIGdata['output']:
        columns = []
        values = []
        for key, value in row.items():
            if key in COLUMN_MAP:
                columns.append(COLUMN_MAP[key])
                values.append(value)

        c.execute(f'''INSERT OR REPLACE INTO foreign_ownership (date, {", ".join(columns)}) 
                        VALUES (?, {", ".join(["?"] * len(values))})''', [date] + values)
        
conn.commit()
c.close()
conn.close()
        
