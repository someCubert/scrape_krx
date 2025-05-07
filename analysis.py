import sqlite3
import os
import pandas as pd 
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
from scipy import stats
from scipy.stats import norm
from statsmodels.stats.diagnostic import acorr_ljungbox
from arch.bootstrap import MovingBlockBootstrap

db_path = 'foreign_ownership.db'
conn = sqlite3.connect(db_path)

def calculate_date(date_str, days):
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    
    new_date_obj = date_obj + timedelta(days=days)
    new_date_str = new_date_obj.strftime('%Y-%m-%d')
    
    return new_date_str

def calculate_CAAFO_market(df, date_str):
    df = df.copy()
    date = datetime.strptime(date_str, '%Y-%m-%d')
    df['date'] = pd.to_datetime(df['date'])

    base_date_df = df[df['date'] == date].copy()
    base_date_df['Market Cap'] = base_date_df['Close'] * base_date_df['No. of listed shares']
    total_market_cap = base_date_df['Market Cap'].sum()
    base_date_df['Market Cap Weight'] = base_date_df['Market Cap'] / total_market_cap
    company_weights = base_date_df.set_index('Issue code')['Market Cap Weight']
    df['Market Cap Weight'] = df['Issue code'].map(company_weights)

    df = df[['date', 'Market Cap Weight', 'CAFO']]
    df['wCAFO'] = df['Market Cap Weight'] * df['CAFO']
    df['CAAFO'] = df.groupby('date')['wCAFO'].transform('sum')
    df = df.groupby('date')['CAAFO'].first().reset_index()

    return df

def calculate_CAAFO_industry(df, date_str):
    df = df.copy()
    date = datetime.strptime(date_str, '%Y-%m-%d')
    df['date'] = pd.to_datetime(df['date'])

    base_df = df[df['date'] == date].copy()
    base_df['Market Cap'] = base_df['Close'] * base_df['No. of listed shares']
    base_df = base_df.reset_index(drop=True)

    base_df['Market Cap Weight'] = base_df.groupby('Industry')['Market Cap'].transform(
        lambda x: x / x.sum()
    )

    weights_df = base_df[['Issue code', 'Market Cap Weight']].drop_duplicates()

    df = df.merge(weights_df, on=['Issue code'], how='inner')

    industry_mapping = df[df['date'] == date][['Issue code', 'Industry']].drop_duplicates().set_index('Issue code')['Industry']
    df['Industry'] = df['Issue code'].map(industry_mapping)
    industry_counts = df[df['date'] == date][['Issue code', 'Industry']].groupby('Industry').size()
    valid_industries = industry_counts[industry_counts >= 5].index
    df = df[df['Industry'].isin(valid_industries)]
    df = df[['date', 'Industry', 'Market Cap Weight', 'CAFO']]
    df['wCAFO'] = df['Market Cap Weight'] * df['CAFO']

    df['CAAFO'] = df.groupby(['Industry','date'])['wCAFO'].transform('sum')
    df = df.groupby(['Industry', 'date'])['CAAFO'].first().reset_index()    

    return df

def calculate_CAAFO_KOSPI200(df, const, date_str):
    df = df.copy()
    date = datetime.strptime(date_str, '%Y-%m-%d')
    df['date'] = pd.to_datetime(df['date'])
    df_kospi200 = df[df['Issue code'].isin(const)].copy()
    
    base_df = df_kospi200[df_kospi200['date'] == date].copy()
    base_df['Market Cap'] = base_df['Close'] * base_df['No. of listed shares']
    base_df['Market Cap Weight'] = base_df['Market Cap'] / base_df['Market Cap'].sum()
    weights = base_df.set_index('Issue code')['Market Cap Weight']
    df_kospi200['Market Cap Weight'] = df_kospi200['Issue code'].map(weights)

    df_kospi200 = df_kospi200[['date', 'Market Cap Weight', 'CAFO']]
    df_kospi200['wCAFO'] = df_kospi200['Market Cap Weight'] * df_kospi200['CAFO']
    df_kospi200['CAAFO'] = df_kospi200.groupby('date')['wCAFO'].transform('sum')
    df_kospi200 = df_kospi200.groupby('date')['CAAFO'].first().reset_index()

    return df_kospi200
 
def generalized_sign_test(df_event, df_est, firm_codes):
    df_est_filtered = df_est[df_est['Issue code'].isin(firm_codes)]
    df_event_filtered = df_event[df_event['Issue code'].isin(firm_codes)]

    S_mean_per_firm = df_est_filtered.groupby('Issue code')['S'].mean()
    p = S_mean_per_firm.mean()
    n = len(S_mean_per_firm)

    cafo_per_firm = df_event_filtered.groupby('Issue code')['CAFO'].last()
    q = (cafo_per_firm > 0).sum()

    npq = n * p * (1 - p)
    if npq <= 0:
        Z = np.nan
        p_value = np.nan 
    else:
        Z = (q - n * p) / np.sqrt(npq)
        p_value = 2 * norm.sf(np.abs(Z)) 

    return p, q, n, Z, p_value

def plot_CAAFO_over_time_variable_ranges(file_name, dfs, labels, event_dates, min_plot_day=-180, max_plot_day=270):
    plt.figure(figsize=(12, 6))

    all_min_days = []
    all_max_days = []

    for df, label, event_date_str in zip(dfs, labels, event_dates):
        df_plot = df.copy()
        event_date = pd.to_datetime(event_date_str)
        df_plot['days_from_event'] = (pd.to_datetime(df_plot['date']) - event_date).dt.days
        df_plot = df_plot.sort_values('days_from_event')

        if not df_plot.empty:
             all_min_days.append(df_plot['days_from_event'].min())
             all_max_days.append(df_plot['days_from_event'].max())

        df_plot = df_plot[(df_plot['days_from_event'] >= min_plot_day) &
                          (df_plot['days_from_event'] <= max_plot_day)]

        if not df_plot.empty:
            start_day_value = df_plot[df_plot['days_from_event'] == 0]['CAAFO'].values[0]
            df_plot['CAAFO_adjusted_for_plot'] = df_plot['CAAFO'] - start_day_value
            plt.plot(df_plot['days_from_event'], df_plot['CAAFO_adjusted_for_plot'], label=label, linestyle='-')
        else:
             print(f"Warning: No data for '{label}' within the specified plot range [{min_plot_day}, {max_plot_day}].")

    plt.axvline(x=0, color='black', linestyle='--', linewidth=1.5, label='Event Date (Day 0)')

    plt.xlabel('Days Relative to Event Date')
    plt.ylabel(f'CAAFO (Normalized to 0 at Event Date)') 

    plt.xlim(min_plot_day, max_plot_day)

    handles, legend_labels = plt.gca().get_legend_handles_labels()
    by_label = dict(zip(legend_labels, handles))
    plt.legend(by_label.values(), by_label.keys())

    plt.grid(True)

    plt.axhline(y=0, color='grey', linestyle=':', linewidth=1)
    os.makedirs('plots', exist_ok=True)  
    plt.savefig(f'plots/{file_name}.png', dpi=300, bbox_inches='tight')
    plt.close()

    actual_min_plot = min(all_min_days) if all_min_days else min_plot_day
    actual_max_plot = max(all_max_days) if all_max_days else max_plot_day
    if actual_min_plot > min_plot_day:
        print(f"Note: Some data series start after the requested min_plot_day ({min_plot_day}). Earliest data point shown is Day {actual_min_plot}.")
    if actual_max_plot < max_plot_day:
        print(f"Note: Some data series end before the requested max_plot_day ({max_plot_day}). Latest data point shown is Day {actual_max_plot}.")

def plot_CAFO_by_industry_over_time_normalized(file_name, df_industry, event_date_str):
    event_date = pd.to_datetime(event_date_str)
    df_plot = df_industry.copy()
    df_plot['date'] = pd.to_datetime(df_plot['date'])
    df_plot['days_from_event'] = (df_plot['date'] - event_date).dt.days

    df_plot = df_plot.dropna(subset=['Industry', 'CAAFO'])

    df_plot = df_plot.sort_values(['Industry', 'days_from_event'])
    normalized_df = []

    for industry, group in df_plot.groupby('Industry'):
        group = group.copy()
        if 0 in group['days_from_event'].values:
            base_value = group.loc[group['days_from_event'] == 0, 'CAAFO'].values[0]
        else:
            base_value = group.iloc[0]['CAAFO']
        group['CAFO_normalized'] = group['CAAFO'] - base_value
        normalized_df.append(group)

    df_plot = pd.concat(normalized_df)

    # Plotting
    plt.figure(figsize=(16, 10))
    sns.lineplot(data=df_plot, x='days_from_event', y='CAFO_normalized', hue='Industry')

    plt.axvline(x=0, color='black', linestyle='--', linewidth=1.2, label='Event Date (Day 0)')
    plt.xlabel('Days Relative to Event Date')
    plt.ylabel('CAFO (Normalized to 0 at Event Date)')
    plt.legend(title='Industry', bbox_to_anchor=(1, .5), loc='center left')
    plt.tight_layout()
    plt.grid(True)

    os.makedirs('plots', exist_ok=True)
    plt.savefig(f'plots/{file_name}.png', dpi=300)
    plt.close()

def run_ljung_box(data_series, lags_to_test=10):
    n_obs = len(data_series)
    actual_lags = min(lags_to_test, n_obs - 1)

    if actual_lags < 1:
        return None, 0

    try:
        lb_results = acorr_ljungbox(data_series['CAAFO'], lags=actual_lags, return_df=True)

        p_value = lb_results['lb_pvalue'].iloc[-1]
        return p_value, actual_lags
    except Exception as e:
        print(f"Error running Ljung-Box test: {e}")
        return None, actual_lags 

def policy_change_analysis(conn, date_str, event_1, event_2, est_1, est_2, const, name):
    event_1 = event_1 - 1
    event_before = calculate_date(date_str, event_1)
    event_after = calculate_date(date_str, event_2)

    # prepare data
    query1 = f'SELECT "date", "Issue name", "Close", "Issue code", "No. of listed shares", "No. of shares of foreign ownership", "Foreign ownership ratio", "Foreign ownership limit quantity", "Exhaustion rate", "Industry" FROM foreign_ownership WHERE "date" <= "{event_after}" AND "date" >= "{event_before}" AND not("Industry" is NULL)'
    df_main = pd.read_sql_query(query1, conn)
    df_main['Close'] = df_main['Close'].astype(str).str.replace(',','').astype(float)
    df_main['No. of listed shares'] = df_main['No. of listed shares'].astype(str).str.replace(',','').astype(int)
    df_main = df_main.dropna(subset=['Exhaustion rate']) # some old data apparently dont have foreign ownership values
    df_main = df_main[df_main['Exhaustion rate'] != '']
    df_main['Exhaustion rate'] = df_main['Exhaustion rate'].astype(float)
    df_main = df_main.sort_values(['Issue code', 'date'])
    df_main['Daily change (ER)'] = df_main.groupby('Issue code')['Exhaustion rate'].diff().fillna(0)

    est_2 = est_2 - 1
    est_before = calculate_date(date_str, est_2)
    est_after = calculate_date(date_str, est_1)
    query2 = f'SELECT "date", "Issue name", "Close", "Issue code", "No. of listed shares", "No. of shares of foreign ownership", "Foreign ownership ratio", "Foreign ownership limit quantity", "Exhaustion rate", "Industry" FROM foreign_ownership WHERE "date" <= "{est_after}" AND "date" >= "{est_before}" AND not("Industry" is NULL)'
    df_est = pd.read_sql_query(query2, conn)
    df_est = df_est.dropna(subset=['Exhaustion rate'])
    df_est = df_est[df_est['Exhaustion rate'] != '']
    df_est['Exhaustion rate'] = df_est['Exhaustion rate'].astype(float)
    df_est['Close'] = df_est['Close'].astype(str).str.replace(',','').astype(float)
    df_est['No. of listed shares'] = df_est['No. of listed shares'].astype(str).str.replace(',','').astype(int)
    df_est = df_est.sort_values(['Issue code', 'date'])
    df_est['Daily change (ER)'] = df_est.groupby('Issue code')['Exhaustion rate'].diff().fillna(0)

    df_est['date'] = pd.to_datetime(df_est['date'])
    df_est = df_est[df_est['date'] != pd.to_datetime(est_before)]   
    EstChangePerIssueCode = df_est.groupby('Issue code')['Daily change (ER)'].mean()
    df_main['Est. daily change'] = df_main['Issue code'].map(EstChangePerIssueCode)
    # print(df_main[df_main['Issue code'] == '005930'][['date', 'Exhaustion rate', 'Daily change (ER)', 'Est. daily change']])
    
    df_main['date'] = pd.to_datetime(df_main['date'])
    df_main = df_main[df_main['date'] != pd.to_datetime(event_before)]

    # Head in the sand xD
    df_main = df_main.dropna(subset=['Est. daily change'])

    df_main['AFO'] = df_main['Daily change (ER)'] - df_main['Est. daily change']
    df_main['CAFO'] = df_main.groupby('Issue code')['AFO'].transform(lambda x: x.cumsum())

    market = calculate_CAAFO_market(df_main, date_str)
    KOSPI200 = calculate_CAAFO_KOSPI200(df_main, const, date_str)
    industry = calculate_CAAFO_industry(df_main, date_str)

    # autocorrelation test
    num_lags_lb = 10
    lb_pvalue_market, lags_used_market = run_ljung_box(market, lags_to_test=num_lags_lb)
    if lb_pvalue_market is not None:
        print(f"\nLjung-Box test (up to {lags_used_market} lags) p-value: {lb_pvalue_market:.4g}", end="")
        if lb_pvalue_market < 0.05:
            print(" (Suggests significant autocorrelation)")
        else:
            print(" (Suggests no significant autocorrelation)")
    else:
        print(f"  Ljung-Box test could not be run (N={len(market)}).")

    # ttest, null hypothesis: mean = 0
    print(f"\nt-test results for {name}:")
    hyp0 = 0
    ttest_result_market = stats.ttest_1samp(market['CAAFO'], hyp0)
    conf_interval_market = ttest_result_market.confidence_interval()
    ci_low_market = conf_interval_market.low
    ci_high_market = conf_interval_market.high
    sample_mean = market['CAAFO'].mean()
    cohens_d_market = sample_mean / market['CAAFO'].std()
    print(f"  [Market] t-statistic: {ttest_result_market.statistic}, p-value: {ttest_result_market.pvalue}, df: {ttest_result_market.df}, Mean: {sample_mean:.4f}, Confidence Interval (95%): ({ci_low_market:.4f}, {ci_high_market:.4f}), Cohen's d: {cohens_d_market:.4f}")

    for i in industry['Industry'].unique():
        industry_subset = industry[industry['Industry'] == i]
        ttest_result_industry = stats.ttest_1samp(industry_subset['CAAFO'], hyp0)
        conf_interval_industry = ttest_result_industry.confidence_interval()
        ci_low_industry = conf_interval_industry.low
        ci_high_industry = conf_interval_industry.high
        sample_mean_industry = industry_subset['CAAFO'].mean()
        cohens_d_industry = sample_mean_industry / industry_subset['CAAFO'].std()
        print(f"  [Industry: {i}] t-statistic: {ttest_result_industry.statistic}, p-value: {ttest_result_industry.pvalue}, df: {ttest_result_industry.df}, Mean: {sample_mean_industry:.4f}, Confidence Interval (95%): ({ci_low_industry:.4f}, {ci_high_industry:.4f}), Cohen's d: {cohens_d_industry:.4f}")

    ttest_result_KOSPI = stats.ttest_1samp(KOSPI200['CAAFO'], hyp0)
    conf_interval_KOSPI = ttest_result_KOSPI.confidence_interval() 
    ci_low_KOSPI = conf_interval_KOSPI.low
    ci_high_KOSPI = conf_interval_KOSPI.high
    sample_mean_KOSPI = KOSPI200['CAAFO'].mean()
    cohens_d_KOSPI = sample_mean_KOSPI / KOSPI200['CAAFO'].std()
    print(f"  [KOSPI200] t-statistic: {ttest_result_KOSPI.statistic}, p-value: {ttest_result_KOSPI.pvalue}, df: {ttest_result_KOSPI.df}, Mean: {sample_mean_KOSPI:.4f}, Confidence Interval (95%): ({ci_low_KOSPI:.4f}, {ci_high_KOSPI:.4f}), Cohen's d: {cohens_d_KOSPI:.4f}")

    # generalized sign test
    df_est['Est. daily change'] = df_est['Issue code'].map(EstChangePerIssueCode)
    df_est['AFO'] = df_est['Daily change (ER)'] - df_est['Est. daily change']
    df_est['S'] = (df_est['AFO'] > 0).astype(int)

    print(f"\nGeneralized Sign Test Results for {name}:")

    all_firms = df_main['Issue code'].unique()
    p_m, q_m, n_m, Z_m, p_value_m = generalized_sign_test(df_main, df_est, all_firms)
    print(f"  [Market] p = {p_m:.4f}, q = {q_m}, n = {n_m}, Z = {Z_m:.4f}, p-value = {p_value_m}")

    kospi200_firms = df_main[df_main['Issue code'].isin(const)]['Issue code'].unique()
    p_k, q_k, n_k, Z_k, p_value_k = generalized_sign_test(df_main, df_est, kospi200_firms)
    print(f"  [KOSPI200] p = {p_k:.4f}, q = {q_k}, n = {n_k}, Z = {Z_k:.4f}, p-value = {p_value_k}")

    df_industry = df_main.copy()
    date = datetime.strptime(date_str, '%Y-%m-%d')
    industry_mapping = df_industry[df_industry['date'] == date][['Issue code', 'Industry']].drop_duplicates().set_index('Issue code')['Industry']
    df_industry['Industry'] = df_industry['Issue code'].map(industry_mapping)
    for industry_name in df_industry['Industry'].dropna().unique():
        industry_firms = df_industry[df_industry['Industry'] == industry_name]['Issue code'].unique()
        p_i, q_i, n_i, Z_i, p_value_i = generalized_sign_test(df_industry, df_est, industry_firms)
        print(f"  [Industry: {industry_name}] p = {p_i:.4f}, q = {q_i}, n = {n_i}, Z = {Z_i:.4f}, p-value = {p_value_i:.4f}")

    # for graphs
    df_combined = pd.concat([df_est, df_main], ignore_index=True)
    df_combined['date'] = pd.to_datetime(df_combined['date'])
    df_combined = df_combined.sort_values(['Issue code', 'date'])

    df_combined['AFO'] = df_combined['Daily change (ER)'] - df_combined['Est. daily change']
    df_combined['CAFO'] = df_combined.groupby('Issue code')['AFO'].cumsum()
    market = calculate_CAAFO_market(df_combined, date_str)
    industry = calculate_CAAFO_industry(df_combined, date_str)
    KOSPI200 = calculate_CAAFO_KOSPI200(df_combined, const, date_str)

    return market, industry, KOSPI200

# Add KOSPI200 constituents for each event date
KOSPI200_const_FSCMA = ['005930', '005490', '015760', '009540', '017670', '105560', '033780', '005380', '055550', '066570', '030200', '034220', '004170', '000810', '034020', '096770', '003550', '010140', '010950', '000830', '000720', '012330', '053000', '051910', '023530', '032390', '003600', '000660', '010060', '086790', '042660', '024110', '016360', '004940', '011200', '036460', '004020', '090430', '006800', '047040', '010620', '006360', '006400', '000270', '002380', '037620', '012630', '035250', '078930', '000150', '003490', '051900', '009150', '047050', '006260', '042670', '028050', '005940', '012450', '001740', '000240', '000880', '000100', '021240', '000700', '003450', '001300', '010130', '012750', '004800', '011170', '004990', '000210', '001230', '071050', '069960', '036570', '010120', '004370', '004000', '025860', '003690', '005300', '009830', '067250', '005270', '008930', '003240', '000670', '005280', '001040', '000640', '001800', '011810', '001440', '018880', '030000', '001120', '042100', '002990', '002790', '006280', '006120', '068870', '077970', '034120', '001430', '029530', '093050', '010520', '011790', '011780', '069620', '064420', '002020', '003410', '003300', '003000', '007310', '069260', '003480', '004150', '005180', '019680', '017800', '002240', '003920', '000480', '073240', '003570', '008000', '016800', '002350', '091090', '093370', '007570', '000070', '084010', '003030', '000020', '000140', '001210', '001520', '001630', '002000', '002030', '003940', '006380', '014830', '020000', '003120', '002270', '009720', '009440', '009290', '009200', '008730', '008320', '008060', '000990', '006650', '000050', '003640', '001130', '025000', '025540', '017960', '001680', '005680', '016380', '001940', '014820', '011930', '006840', '006390', '005810', '005090', '004710', '004130', '003520', '002300', '001370', '001060', '000230', '064960', '049770', '042700', '029460', '027970', '025850', '013570', '015590', '015860', '005740', '084870', '004560', '014990', '011400', '004980', '013240']
KOSPI200_const_short1 = ['005930', '000660', '207940', '035420', '051910', '068270', '006400', '005380', '028260', '051900', '012330', '017670', '005490', '036570', '035720', '105560', '055550', '015760', '018260', '000270', '034730', '033780', '003550', '032830', '090430', '066570', '009150', '096770', '000810', '251270', '086790', '010130', '010950', '011170', '009540', '316140', '030200', '032640', '018880', '021240', '035250', '024110', '002790', '034220', '271560', '086280', '029780', '006800', '267250', '097950', '078930', '012750', '071050', '000720', '008770', '139480', '128940', '000100', '016360', '010140', '000120', '004990', '161390', '004020', '003410', '011070', '005940', '282330', '007070', '004170', '000210', '005830', '028050', '023530', '009830', '241560', '047810', '036460', '003490', '001040', '008560', '081660', '042660', '030000', '000080', '028670', '008930', '001450', '006360', '020150', '011780', '011790', '007310', '138930', '026960', '004370', '069960', '047050', '004800', '009240', '051600', '047040', '031430', '000880', '017800', '006280', '002380', '001740', '214320', '012450', '010620', '003000', '009420', '010120', '204320', '088350', '111770', '069620', '000240', '000670', '000990', '006260', '114090', '014680', '064350', '073240', '010060', '001800', '005250', '185750', '161890', '057050', '003240', '003520', '004000', '005300', '005440', '170900', '011210', '034020', '049770', '120110', '010780', '000150', '005850', '008060', '018250', '042670', '294870', '069260', '192400', '192820', '285130', '052690', '000640', '115390', '001680', '002350', '005180', '005610', '006650', '007570', '012630', '014820', '020000', '079550', '093370', '103140', '001060', '003850', '004490', '006390', '105630', '064960', '071840', '079160', '027410', '000070', '145990', '001230', '001430', '002240', '002270', '002960', '003920', '006120', '014830', '019680', '025540', '025860', '060980', '093050', '096760', '108670', '001120', '001520', '006840', '003620', '298040', '079430']
KOSPI200_const_short2 = ['005930', '373220', '000660', '207940', '005490', '005380', '051910', '006400', '035420', '000270', '003670', '068270', '105560', '012330', '028260', '035720', '055550', '066570', '096770', '032830', '003550', '000810', '086790', '033780', '034730', '323410', '047050', '015760', '017670', '138040', '018260', '009150', '010130', '329180', '034020', '316140', '352820', '024110', '030200', '259960', '090430', '011200', '003490', '010950', '009540', '001570', '402340', '010140', '011170', '086280', '326030', '005830', '012450', '377300', '036570', '042660', '011070', '009830', '161390', '051900', '302440', '361610', '028050', '271560', '000100', '034220', '267250', '047810', '004020', '032640', '097950', '006800', '241560', '000720', '018880', '078930', '251270', '128940', '383220', '011780', '011790', '029780', '005940', '016360', '021240', '010620', '035250', '071050', '180640', '064350', '003410', '004370', '004990', '006260', '008770', '272210', '282330', '001450', '002790', '007070', '000990', '001040', '008930', '028670', '039490', '081660', '088350', '111770', '002380', '030000', '138930', '052690', '036460', '010060', '010120', '012750', '175330', '023530', '112610', '139480', '020150', '014680', '079550', '017800', '000120', '000880', '004170', '298050', '026960', '047040', '204320', '009420', '000080', '001440', '003230', '004000', '298020', '011210', '042670', '051600', '185750', '007310', '000150', '000240', '001740', '004800', '005300', '375500', '005850', '073240', '137310', '139130', '192820', '005420', '006280', '006360', '009240', '336260', '069960', '120110', '161890', '069620', '000210', '001120', '001800', '006650', '285130', '103140', '114090', '280360', '093370', '000670', '003090', '009900', '010780', '014820', '016380', '300720', '069260', '105630', '178920', '192080', '271940', '294870', '032350', '001680', '003240', '003850', '004490', '039130', '008730', '019170', '020560', '005250', '020000', '031430', '381970', '284740', '057050', '013890']
KOSPI200_const_LEIs = ['005930', '000660', '373220', '207940', '005380', '005490', '035420', '000270', '051910', '006400', '003670', '068270', '028260', '035720', '105560', '012330', '055550', '066570', '032830', '096770', '003550', '018260', '034730', '323410', '015760', '033780', '086790', '000810', '138040', '009150', '011200', '017670', '329180', '010130', '034020', '259960', '047050', '352820', '316140', '030200', '024110', '003490', '009540', '042660', '090430', '010950', '326030', '010140', '402340', '011170', '086280', '001570', '377300', '012450', '005830', '361610', '011070', '161390', '009830', '051900', '302440', '028050', '036570', '000100', '097950', '004020', '267250', '251270', '006800', '047810', '034220', '241560', '032640', '271560', '128940', '021240', '000720', '078930', '180640', '011780', '029780', '018880', '016360', '071050', '035250', '011790', '005940', '010620', '383220', '272210', '004990', '003410', '000120', '001040', '001450', '006260', '064350', '079550', '008770', '008930', '000990', '007070', '052690', '039490', '004370', '014680', '112610', '002790', '012750', '028670', '030000', '036460', '081660', '088350', '138930', '282330', '010120', '175330', '139480', '023530', '000240', '000880', '111770', '010060', '020150', '002380', '004170', '009420', '298050', '026960', '047040', '017800', '000080', '003230', '004000', '007310', '011210', '298020', '073240', '137310', '185750', '204320', '051600', '000150', '001440', '001740', '004800', '005300', '005420', '375500', '006280', '006360', '042670', '139130', '192820', '336260', '005850', '009240', '069620', '280360', '120110', '161890', '069960', '000210', '001120', '003090', '285130', '093370', '103140', '006650', '000670', '300720', '008730', '009900', '010780', '014820', '016380', '020560', '039130', '069260', '105630', '114090', '178920', '192080', '271940', '294870', '001800', '001680', '003240', '003850', '032350', '005250', '019170', '031430', '004490', '020000', '381970', '284740', '057050', '013890']
KOSPI200_const_forex = ['005930', '000660', '373220', '005380', '207940', '000270', '068270', '105560', '005490', '035420', '006400', '051910', '028260', '055550', '012330', '003670', '035720', '066570', '000810', '086790', '032830', '042700', '138040', '011200', '329180', '402340', '259960', '003550', '034020', '015760', '012450', '018260', '009150', '033780', '034730', '009540', '047050', '096770', '017670', '024110', '316140', '010130', '267260', '323410', '090430', '042660', '030200', '086280', '003490', '010140', '352820', '010950', '005830', '000100', '450080', '011070', '011790', '326030', '010120', '034220', '022100', '267250', '051900', '161390', '097950', '241560', '454910', '066970', '047810', '036460', '079550', '021240', '005070', '011170', '001570', '251270', '028050', '009830', '003230', '029780', '064350', '032640', '078930', '006800', '302440', '006260', '180640', '036570', '011780', '005940', '071050', '010620', '004020', '377300', '128940', '016360', '272210', '000720', '271560', '001040', '000150', '039490', '361610', '035250', '001450', '001440', '004370', '175330', '052690', '088350', '138930', '018880', '002790', '004990', '002380', '081660', '383220', '192820', '000120', '007070', '030000', '012750', '028670', '008930', '112610', '204320', '000880', '026960', '008770', '014680', '005850', '073240', '103140', '023530', '009420', '010060', '282330', '042670', '047040', '051600', '111770', '139480', '161890', '017800', '298020', '298050', '004170', '007310', '011210', '280360', '000080', '000240', '002710', '004490', '006280', '006360', '009240', '139130', '336260', '457190', '009970', '014820', '069620', '069960', '001120', '375500', '137310', '145720', '185750', '000210', '004000', '004800', '005300', '006110', '005420', '003620', '003090', '001800', '001740', '001680', '300720', '192080', '120110', '039130', '008730', '032350', '006650', '093370', '105630', '114090', '271940', '009900', '003030', '178920', '001430', '069260', '285130', '016380', '000670', '005250']

#test
# m_p1,i_p1,K_p1 = policy_change_analysis(conn, '2020-07-06', 0, 270, -30, -270, KOSPI200_const_forex, 'test')

#real
m_pFSCMA,i_pFSCMA,K_pFSCMA = policy_change_analysis(conn, '2009-02-04', 0, 270, -1, -180, KOSPI200_const_FSCMA, 'FSCMA')
m_pShort1,i_pShort1,K_pShort1 = policy_change_analysis(conn, '2020-03-13', 0, 180, -1, -180, KOSPI200_const_short1, 'Short1')
m_pShort2,i_pShort2,K_pShort2 = policy_change_analysis(conn, '2023-11-06', 0, 180, -1, -180, KOSPI200_const_short2, 'Short2')
m_pLEIs,i_pLEIs,K_pLEIs = policy_change_analysis(conn, '2023-12-14', 0, 270, -1, -180, KOSPI200_const_LEIs, 'LEIs')
m_pForexW, i_pForexW,K_pForexW = policy_change_analysis(conn, '2024-07-01', 0, 270, -181, -360, KOSPI200_const_forex, 'ForexWithPilot')
m_pForex,i_pForex,K_pForex = policy_change_analysis(conn, '2024-07-01', 0, 270, -1, -180, KOSPI200_const_forex, 'Forex')



#graphs
plot_start_day = -180
plot_end_day = 270

plot_CAAFO_over_time_variable_ranges(
    file_name='market',
    dfs=[m_pFSCMA, m_pShort1, m_pShort2, m_pLEIs, m_pForexW, m_pForex],
    labels=['FSCMA (2009)', 'Short Selling Ban (2020)', 'Short Selling Ban (2023)', 'LEIs (2023)', 'Forex With Pilot (2024)', 'Forex without Pilot (2024)'],
    event_dates=['2009-02-04', '2020-03-13', '2023-11-06', '2023-12-14', '2024-07-01', '2024-07-01'],
    min_plot_day=plot_start_day,
    max_plot_day=plot_end_day
)

plot_CAAFO_over_time_variable_ranges(
    file_name='KOSPI200',
    dfs=[K_pFSCMA, K_pShort1, K_pShort2, K_pLEIs, K_pForexW, K_pForex],
    labels=['FSCMA (2009)', 'Short Selling Ban (2020)', 'Short Selling Ban (2023)', 'LEIs (2023)', 'Forex With Pilot (2024)', 'Forex without Pilot (2024)'],
    event_dates=['2009-02-04', '2020-03-13', '2023-11-06', '2023-12-14', '2024-07-01', '2024-07-01'],
    min_plot_day=plot_start_day,
    max_plot_day=plot_end_day
)


plot_CAFO_by_industry_over_time_normalized('CAAFO_FSCMA', i_pFSCMA, event_date_str='2009-02-04')
plot_CAFO_by_industry_over_time_normalized('CAAFO_Short1', i_pShort1, event_date_str='2020-03-13')
plot_CAFO_by_industry_over_time_normalized('CAAFO_Short2', i_pShort2, event_date_str='2023-11-06')
plot_CAFO_by_industry_over_time_normalized('CAAFO_LEIs', i_pLEIs, event_date_str='2023-12-14')
plot_CAFO_by_industry_over_time_normalized('CAAFO_ForexW', i_pForexW, event_date_str='2024-07-01')
plot_CAFO_by_industry_over_time_normalized('CAAFO_Forex', i_pForex, event_date_str='2024-07-01')


conn.close()