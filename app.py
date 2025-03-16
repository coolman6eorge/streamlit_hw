import streamlit as st
import pandas as pd
import asyncio

from analysis import (
    analyze_city_data, analyze_city_data_parallel, 
    analyze_city_data_sequential, check_temperature_anomaly
)
from weather_api import WeatherAPI
from utils import (
    load_data, get_current_season, create_time_series_plot,
    create_seasonal_profile
)
from data_generator import generate_temperature_data

st.set_page_config(
    page_title="Анализ климатических данных",
    layout="wide",
    initial_sidebar_state="expanded"
)

async def run_async_function(func, *args, **kwargs):
    return await func(*args, **kwargs)

if 'data' not in st.session_state:
    st.session_state.data = None
if 'api_key' not in st.session_state:
    st.session_state.api_key = None
if 'weather_api' not in st.session_state:
    st.session_state.weather_api = WeatherAPI()
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None
if 'selected_city' not in st.session_state:
    st.session_state.selected_city = None

st.title("🌡️ Анализ температурных данных и мониторинг текущей температуры через OpenWeatherMap API")

st.sidebar.header("Ввод данных")

if st.sidebar.button("Сгенерировать пример данных"):
    with st.spinner("Генерация пример данных..."):
        data = generate_temperature_data()
        st.session_state.data = data
        st.sidebar.success("Пример данных успешно сгенерирован!")

uploaded_file = st.sidebar.file_uploader("Или загрузите CSV файл с данными о температуре", type=["csv"])
if uploaded_file is not None:
    try:
        st.session_state.data = load_data(uploaded_file)
        st.sidebar.success("Данные успешно загружены!")
    except Exception as e:
        st.sidebar.error(f"Ошибка загрузки данных: {e}")

api_key = st.sidebar.text_input("Ключ API OpenWeatherMap", type="password")
if api_key:
    st.session_state.api_key = api_key
    st.session_state.weather_api.set_api_key(api_key)

if st.session_state.data is not None:
    cities = st.session_state.data['city'].unique().tolist()
    
    selected_city = st.sidebar.selectbox("Выберите город", cities)
    if selected_city != st.session_state.selected_city:
        st.session_state.selected_city = selected_city
        st.session_state.analysis_results = None
    
    st.sidebar.header("Параметры анализа")
    window_size = st.sidebar.slider("Размер окна скользящего среднего (дней)", 7, 60, 30)
    
    analysis_method = st.sidebar.radio(
        "Метод анализа",
        ["Последовательно", "Параллельно"]
    )
    
    api_method = st.sidebar.radio(
        "Метод запроса API",
        ["Синхронно", "Асинхронно"]
    )
    
    if st.sidebar.button("Запустить анализ"):
        with st.spinner("Анализ температурных данных..."):
            if analysis_method == "Параллельно":
                results, execution_time = analyze_city_data_parallel(
                    st.session_state.data, [selected_city], window_size
                )
                st.session_state.analysis_results = results[selected_city]
            else:
                results, execution_time = analyze_city_data_sequential(
                    st.session_state.data, [selected_city], window_size
                )
                st.session_state.analysis_results = results[selected_city]
            
            st.sidebar.info(f"Анализ завершён за {execution_time:.4f} секунд")
    
    if st.session_state.analysis_results:
        results = st.session_state.analysis_results
        city_data = results['city_data']
        rolling_mean = results['rolling_mean']
        rolling_std = results['rolling_std']
        anomalies = results['anomalies']
        upper_bound = results['upper_bound']
        lower_bound = results['lower_bound']
        seasonal_stats = results['seasonal_stats']
        
        st.header(f"Анализ температуры для {selected_city}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Сводная статистика")
            summary = pd.DataFrame({
                'Метрика': ['Средняя температура (°C)', 'Минимальная температура (°C)', 'Максимальная температура (°C)', 
                            'Стандартное отклонение', 'Всего дней', 'Обнаружено аномалий'],
                'Значение': [
                    f"{city_data['temperature'].mean():.2f}",
                    f"{city_data['temperature'].min():.2f}",
                    f"{city_data['temperature'].max():.2f}",
                    f"{city_data['temperature'].std():.2f}",
                    f"{len(city_data)}",
                    f"{len(anomalies)} ({len(anomalies)/len(city_data)*100:.1f}%)"
                ]
            })
            st.table(summary)
        
        with col2:
            st.subheader("Сезонная статистика")
            seasonal_table = seasonal_stats.copy()
            seasonal_table.columns = ['Сезон', 'Среднее (°C)', 'Стнд. отклонение (°C)', 'Мин (°C)', 'Макс (°C)']
            seasonal_table = seasonal_table.round(2)
            st.table(seasonal_table)
        
        st.subheader("Временной ряд температуры")
        fig = create_time_series_plot(
            city_data, selected_city, rolling_mean, upper_bound, lower_bound, anomalies
        )
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("Сезонный температурный профиль")
        seasonal_fig, _ = create_seasonal_profile(city_data, selected_city)
        st.plotly_chart(seasonal_fig, use_container_width=True)
        
        if st.session_state.api_key:
            st.header("Анализ текущей температуры")
            
            try:
                with st.spinner("Получение текущей температуры..."):
                    if api_method == "Синхронно":
                        weather_data = st.session_state.weather_api.get_current_temperature_sync(selected_city)
                    else:
                        weather_data = asyncio.run(
                            run_async_function(
                                st.session_state.weather_api.get_current_temperature_async,
                                selected_city
                            )
                        )
                    
                    current_temp = weather_data['temperature']
                    current_season = get_current_season()
                    
                    is_anomalous, message = check_temperature_anomaly(
                        current_temp, seasonal_stats, current_season
                    )
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric(
                            label=f"Текущая температура в {selected_city}",
                            value=f"{current_temp:.1f}°C",
                            delta=f"{current_temp - city_data['temperature'].mean():.1f}°C по сравнению с историческим средним"
                        )
                        st.text(f"Описание погоды: {weather_data['description']}")
                        st.text(f"Время запроса: {weather_data['request_time']:.4f} секунд")
                        st.text(f"Метод API: {api_method}")
                    
                    with col2:
                        if is_anomalous:
                            st.error(message)
                        else:
                            st.success(message)
                        
                        st.text(f"Текущий сезон: {current_season.capitalize()}")
                        season_data = seasonal_stats[seasonal_stats['season'] == current_season]
                        if not season_data.empty:
                            st.text(f"Среднее за сезон: {season_data['mean'].values[0]:.1f}°C")
                            st.text(f"Стандартное отклонение за сезон: {season_data['std'].values[0]:.1f}°C")
                
            except ValueError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"Произошла ошибка: {str(e)}")
    
    else:
        if st.session_state.selected_city:
            st.info("Нажмите 'Запустить анализ', чтобы проанализировать данные о температуре.")
        else:
            st.info("Выберите город и нажмите 'Запустить анализ', чтобы начать.")
else:
    st.info("Загрузите CSV файл с данными о температуре или сгенерируйте пример данных.")