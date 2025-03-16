import time
from concurrent.futures import ProcessPoolExecutor
import multiprocessing
from functools import partial

def calculate_moving_average(df, window=30):
    return df['temperature'].rolling(window=window, center=True).mean()

def calculate_statistics(df):
    return df.groupby(['city', 'season'])['temperature'].agg(['mean', 'std']).reset_index()

def detect_anomalies(df, rolling_mean, std_dev, threshold=2.0):
    upper_bound = rolling_mean + threshold * std_dev
    lower_bound = rolling_mean - threshold * std_dev
    
    anomalies = df[
        (df['temperature'] > upper_bound) | 
        (df['temperature'] < lower_bound)
    ].copy()
    
    return anomalies, upper_bound, lower_bound

def analyze_city_data(df, city, window=30):
    city_data = df[df['city'] == city].sort_values('timestamp').copy()
    
    rolling_mean = calculate_moving_average(city_data, window)
    
    rolling_std = city_data['temperature'].rolling(window=window, center=True).std()
    
    rolling_mean = rolling_mean.fillna(city_data['temperature'].mean())
    rolling_std = rolling_std.fillna(city_data['temperature'].std())
    
    anomalies, upper_bound, lower_bound = detect_anomalies(city_data, rolling_mean, rolling_std)
    
    seasonal_stats = city_data.groupby('season')['temperature'].agg(['mean', 'std', 'min', 'max']).reset_index()
    
    return {
        'city_data': city_data,
        'rolling_mean': rolling_mean,
        'rolling_std': rolling_std,
        'anomalies': anomalies,
        'upper_bound': upper_bound,
        'lower_bound': lower_bound,
        'seasonal_stats': seasonal_stats
    }

def process_city_data(city, df, window=30):
    return city, analyze_city_data(df, city, window)

def analyze_city_data_parallel(df, cities, window=30):
    num_cores = multiprocessing.cpu_count()
    
    start_time = time.time()
    results = {}
    
    process_func = partial(process_city_data, df=df, window=window)
    
    with ProcessPoolExecutor(max_workers=num_cores) as executor:
        for city, result in executor.map(process_func, cities):
            results[city] = result
    
    end_time = time.time()
    
    return results, end_time - start_time

def analyze_city_data_sequential(df, cities, window=30):
    start_time = time.time()
    results = {}
    
    for city in cities:
        results[city] = analyze_city_data(df, city, window)
    
    end_time = time.time()
    
    return results, end_time - start_time

def check_temperature_anomaly(current_temp, seasonal_stats, current_season):
    season_data = seasonal_stats[seasonal_stats['season'] == current_season]
    
    if season_data.empty:
        return False, "Нет данных для этого сезона"
    
    mean = season_data['mean'].values[0]
    std = season_data['std'].values[0]
    
    lower_bound = mean - 2 * std
    upper_bound = mean + 2 * std
    
    is_anomalous = current_temp < lower_bound or current_temp > upper_bound
    
    if is_anomalous:
        if current_temp < lower_bound:
            message = f"Аномально холодно! {current_temp:.1f}°C меньше чем бывает обычно. (От {lower_bound:.1f}°C до {upper_bound:.1f}°C)"
        else:
            message = f"Аномально жарко! {current_temp:.1f}°C больше чем бывает обычно. (От {lower_bound:.1f}°C до {upper_bound:.1f}°C)"
    else:
        message = f"Нормальная температура. {current_temp:.1f}°C в пределах нормы. (От {lower_bound:.1f}°C до {upper_bound:.1f}°C)"
    
    return is_anomalous, message