# Foreign ownership by issue Download

This programm is only used to download foreign ownership data on a daily, company basis. In case you might need other data minor changes should be made to the download files. Analysis files are exclusive to my project and should be rewritten in case of a fork. 

## Download Instructions

To download the "Foreign ownership by issue" from KRX, run the following command from the `data` directory:

```bash
python ../download_fobi.py
```

This will download the data for all days within the hardcoded date range to YYYMMDD.json files. It will skip dates that already have a file

After this, please run the following commands (in this order) from the top-level directory:

```bash
python download_icbi.py
python download_konex.py
python readJSON.py
```
The file python extract_change_data_for_issue_code.py is only used to track the namechanges of companies. 


