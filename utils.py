import pandas as pd
from datetime import datetime
import plotly.graph_objects as go

def load_data(file):
    df = pd.read_csv(file)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df

def get_current_season():
    month = datetime.now().month
    if 3 <= month <= 5:
        return 'spring'
    elif 6 <= month <= 8:
        return 'summer'
    elif 9 <= month <= 11:
        return 'autumn'
    else:
        return 'winter'

def create_time_series_plot(df, city, rolling_mean, upper_bound, lower_bound, anomalies):
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df['timestamp'], 
        y=df['temperature'],
        mode='lines',
        name='Температура',
        line=dict(color='royalblue')
    ))
    
    fig.add_trace(go.Scatter(
        x=df['timestamp'], 
        y=rolling_mean,
        mode='lines',
        name='30-ти дневное скользящее среднее',
        line=dict(color='green', width=2)
    ))
    
    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=upper_bound,
        mode='lines',
        line=dict(width=0),
        showlegend=False
    ))
    
    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=lower_bound,
        mode='lines',
        line=dict(width=0),
        fill='tonexty',
        fillcolor='rgba(0, 255, 0, 0.1)',
        name='Среднее (±2σ)'
    ))
    
    if not anomalies.empty:
        fig.add_trace(go.Scatter(
            x=anomalies['timestamp'],
            y=anomalies['temperature'],
            mode='markers',
            name='Аномалии',
            marker=dict(color='red', size=8, symbol='circle')
        ))
    
    fig.update_layout(
        title=f'Временной ряд температуры для {city}',
        xaxis_title='Дата',
        yaxis_title='Температура (°C)',
        hovermode='x unified',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
    )
    
    return fig

def create_seasonal_profile(df, city):
    if df.empty:
        return None, None
    
    if 'season' not in df.columns or 'temperature' not in df.columns:
        return None, None
    
    try:
        seasonal_stats = df.groupby('season').agg(
            mean=('temperature', 'mean'),
            std=('temperature', 'std'),
            min=('temperature', 'min'),
            max=('temperature', 'max')
        ).reset_index()
        
        season_order = ['winter', 'spring', 'summer', 'autumn']
        seasonal_stats['season'] = pd.Categorical(
            seasonal_stats['season'], 
            categories=season_order, 
            ordered=True
        )
        seasonal_stats = seasonal_stats.sort_values('season')
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=seasonal_stats['season'],
            y=seasonal_stats['mean'],
            name='Средняя температура',
            error_y=dict(
                type='data',
                array=seasonal_stats['std']*2,
                visible=True
            ),
            marker_color='rgb(55, 83, 109)'
        ))
        
        fig.add_trace(go.Scatter(
            x=seasonal_stats['season'],
            y=seasonal_stats['min'],
            mode='markers',
            name='Минимум',
            marker=dict(color='blue', size=10, symbol='triangle-down')
        ))
        
        fig.add_trace(go.Scatter(
            x=seasonal_stats['season'],
            y=seasonal_stats['max'],
            mode='markers',
            name='Максимум',
            marker=dict(color='red', size=10, symbol='triangle-up')
        ))
        
        fig.update_layout(
            title=f'Сезонный температурный профиль для {city}',
            xaxis_title='Сезон',
            yaxis_title='Температура (°C)',
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
        )
        
        return fig, seasonal_stats
    
    except Exception as e:
        print(f"Error creating seasonal profile: {e}")
        return None, None