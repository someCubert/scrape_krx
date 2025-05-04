import sqlite3
import pandas as pd
from scipy.stats import skew, kurtosis
import numpy as np
from statsmodels.stats.diagnostic import acorr_ljungbox

db_path = 'foreign_ownership.db'
conn = sqlite3.connect(db_path)

def studentized_range(data):
    return (np.max(data) - np.min(data)) / np.std(data, ddof=1)


# descriptive statistics for "Exhaustion rate"
query1 = f'SELECT "Exhaustion rate" FROM foreign_ownership WHERE not("Industry" is NULL)'

df = pd.read_sql_query(query1, conn)
df = df[df['Exhaustion rate'] != '']
df['Exhaustion rate'] = df['Exhaustion rate'].astype(float)

def calc_stats(series):
    series = series.dropna()
    n = len(series)
    mean = series.mean()
    median = series.median()
    std_dev = series.std(ddof=0)
    skewness = skew(series, bias=False)
    kurt = kurtosis(series, fisher=False, bias=False)  # fisher=False to match Excel-style kurtosis
    range = studentized_range(series)

    return {
        'Mean': mean,
        'Median': median,
        'Standard Deviation': std_dev,
        'Coefficient of Skewness': skewness,
        'Coefficient of Kurtosis': kurt,
        "Studentized Range": range
    }

stats = calc_stats(df['Exhaustion rate'])
print(pd.Series(stats).round(5))

# test for autocorrelation
query2 = f'SELECT "date", "Issue code", "Exhaustion rate" FROM foreign_ownership WHERE "Exhaustion rate" != "" AND "Exhaustion rate" IS NOT NULL AND not("Industry" is NULL)'
df_auto = pd.read_sql_query(query2, conn)
df_auto.columns = df_auto.columns.str.strip()

df_auto['Exhaustion rate'] = df_auto['Exhaustion rate'].astype(float)
df_auto['date'] = pd.to_datetime(df_auto['date'])
df_auto = df_auto.sort_values(['Issue code', 'date'])
df_auto['Daily change (ER)'] = df_auto.groupby('Issue code')['Exhaustion rate'].diff()

max_lag = 10
acf_results = {lag: [] for lag in range(1, max_lag + 1)}

for stock, group in df_auto.groupby('Issue code'):
    changes = group['Daily change (ER)'].dropna().values
    if len(changes) > max_lag:
        for lag in range(1, max_lag + 1):
            acf = pd.Series(changes).autocorr(lag=lag)
            acf_results[lag].append(acf)

acf_df = pd.DataFrame(acf_results)
acf_summary = acf_df.agg(['mean', 'std']).T
print("Autocorrelation Summary (Mean and Std per Lag):")
print(acf_summary)


conn.close()
