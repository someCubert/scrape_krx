import pandas as pd
import numpy as np
import seaborn as sns
import os
import sqlite3
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import matplotlib.ticker as ticker

df = pd.DataFrame(columns= ['Year','GDP Growth Rate'])
years = range(2005, 2024)
df['Year'] = years
df['GDP growth rate (%)'] = [4.31, 5.26, 5.80, 3.01, 0.79, 6.80, 3.69, 2.40, 3.16, 3.20, 2.81, 2.95, 3.16, 2.91, 2.24, -0.71, 4.30, 2.61, 1.36]

plt.figure(figsize=(12, 6))
sns.lineplot(data=df, x='Year', y='GDP growth rate (%)')
plt.grid(True)
plt.xticks(years)
plt.xlim(2005, 2023)  # Set x-axis limits to match data range
os.makedirs('plots', exist_ok=True)  # Create 'plots' subfolder if it doesn't exist
plt.savefig('plots/gdp_growth_rate.png', dpi=300, bbox_inches='tight')
plt.close()

df = pd.DataFrame(columns=['Year','Foreign Ownership Level', 'Country'])
years = range(2005, 2025)
df['Year'] = years

korea_data = [37.15, 35.13, 30.96, 27.19, 30.46, 31.16, 30.56, 32.48, 32.95, 31.61, 29.04, 31.75, 33.53, 32.11, 34.19, 31.11, 29.52, 27.41, 28.75, 28.88]
japan_data = [26.3, 27.8, 27.4, 23.5, 26.0, 26.7, 26.28, 28.0, 30.8, 31.7, 29.8, 30.1, 30.3, 29.1, 29.6, 30.23, 30.45, 30.1, 31.8]

korea_df = pd.DataFrame({'Year': years, 'Foreign Ownership Level (%)': korea_data, 'Country': 'Korea'})
# japan_df = pd.DataFrame({'Year': years, 'Foreign Ownership Level (%)': japan_data, 'Country': 'Japan'})

# df = pd.concat([korea_df, japan_df], ignore_index=True)

plt.figure(figsize=(12, 6))
sns.lineplot(data=korea_df, x='Year', y='Foreign Ownership Level (%)')
plt.grid(True)
plt.xticks(years)
plt.xlim(2005, 2024)
plt.ylim(0, 40) 
plt.savefig('plots/foreign_ownership.png', dpi=300, bbox_inches='tight')
plt.close()


db_path = 'foreign_ownership.db'
conn = sqlite3.connect(db_path)
query1 = f'SELECT "date", "Issue name", "Close", "Issue code", "No. of listed shares" FROM foreign_ownership WHERE not("Industry" is NULL)'
df_main = pd.read_sql_query(query1, conn)
conn.close()

df_main = df_main.dropna(subset=["Close", "No. of listed shares"])
df_main["date"] = pd.to_datetime(df_main["date"])
df_main['Close'] = pd.to_numeric(
    df_main['Close'].str.replace(',', ''), errors='coerce'
)
df_main['No. of listed shares'] = pd.to_numeric(
    df_main['No. of listed shares'].str.replace(',', ''), errors='coerce'
)
df_main = df_main.dropna(subset=['Close', 'No. of listed shares'])
df_main['No. of listed shares'] = df_main['No. of listed shares'].astype(int)   
df_main["market_cap"] = df_main["Close"] * df_main["No. of listed shares"]
df_main["year"] = df_main["date"].dt.year
df_main = df_main.sort_values("date")
last_per_stock_per_year = df_main.groupby(["year", "Issue code"]).tail(1)
total_market_cap_per_year = last_per_stock_per_year.groupby("year")["market_cap"].sum().reset_index()

plt.figure(figsize=(12, 6))
sns.lineplot(data=total_market_cap_per_year, x="year", y="market_cap")
# Change divisor to 1e9 for billions or 1e12 for trillions
divisor = 1e12
plt.gca().yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f'{x / divisor:.0f}'))

plt.gca().xaxis.set_major_locator(ticker.MultipleLocator(1))
plt.gca().xaxis.set_major_formatter(ticker.FormatStrFormatter('%d'))

plt.xlabel("Year")
plt.ylabel("Total Market Cap (Trillion KRW)")  
plt.grid(True)
plt.xlim(2005, 2024)
plt.tight_layout()
plt.savefig('plots/total_market_cap.png', dpi=300, bbox_inches='tight')
plt.close()