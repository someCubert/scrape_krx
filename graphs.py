import pandas as pd
import numpy as np
import seaborn as sns
import os
import matplotlib.pyplot as plt

df = pd.DataFrame(columns= ['Year','GDP Growth Rate'])
years = range(2005, 2024)
df['Year'] = years
df['GDP growth rate'] = [4.31, 5.26, 5.80, 3.01, 0.79, 6.80, 3.69, 2.40, 3.16, 3.20, 2.81, 2.95, 3.16, 2.91, 2.24, -0.71, 4.30, 2.61, 1.36]

plt.figure(figsize=(12, 6))
sns.lineplot(data=df, x='Year', y='GDP growth rate')
plt.grid(True)
plt.xticks(years)
plt.xlim(2005, 2023)  # Set x-axis limits to match data range
os.makedirs('plots', exist_ok=True)  # Create 'plots' subfolder if it doesn't exist
plt.savefig('plots/gdp_growth_rate.png', dpi=300, bbox_inches='tight')
plt.close()

