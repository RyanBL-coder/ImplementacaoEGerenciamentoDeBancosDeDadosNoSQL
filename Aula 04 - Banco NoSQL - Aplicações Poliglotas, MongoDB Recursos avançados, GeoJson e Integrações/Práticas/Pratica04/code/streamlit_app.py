import streamlit as st
import pandas as pd
import plotly.express as px
from db_utils import (
    get_mongo_db, 
    get_race_sessions,
    get_session_details,
    get_drivers_from_session, 
    get_laps_for_drivers
)

# --- Configuração da Página ---
st.set_page_config(
    page_title="OpenF1 Data Explorer",
    page_icon="🏎️",
    layout="wide"
)

st.title("🏎️ OpenF1 Data Explorer")
st.markdown("Uma interface para explorar dados de corridas de Fórmula 1 via OpenF1 API e MongoDB.")

# --- Conexão com o Banco de Dados ---
db = get_mongo_db()

if db is None:
    st.sidebar.warning("⚠️ Conexão com MongoDB indisponível. Operando diretamente via OpenF1 REST API.")

# --- Barra Lateral de Filtros (Sidebar) ---
with st.sidebar:
    st.header("Filtros da Sessão")
    
    # Seleção de Ano (Anos disponíveis na OpenF1 API: 2023 em diante)
    available_years = [2024, 2023] 
    selected_year = st.selectbox("Selecione o Ano", options=available_years)
    
    # Seleção de Sessão de Corrida
    with st.spinner("Carregando sessões..."):
        race_sessions = get_race_sessions(db, selected_year)

    if not race_sessions:
        st.warning(f"⚠️ Nenhuma sessão de corrida encontrada para {selected_year}.")
        st.stop()

    session_options = {
        f"{s.get('race_name', 'Corrida Desconhecida')} - {s.get('session_name', 'Sessão')}"
        : s['session_key'] 
        for s in race_sessions
    }

    selected_race_name = st.selectbox(
        "Selecione a Corrida", 
        options=list(session_options.keys())
    )
    selected_session_key = session_options[selected_race_name]

# --- Painel Principal (Main Panel) ---
if selected_session_key:
    session_details = get_session_details(db, selected_session_key)
    if session_details:
        st.header(f"📊 Análise da Sessão: {session_details.get('year', 'N/A')}")
        col1, col2, col3 = st.columns(3)
        col1.metric("País", session_details.get('country_name', 'N/A'))
        col2.metric("Circuito", session_details.get('circuit_short_name', 'N/A'))
        
        date_val = str(session_details.get('date_start', 'N/A'))
        formatted_date = date_val.split('T')[0] if 'T' in date_val else date_val
        col3.metric("Data", formatted_date)
    
    st.markdown("---")

    # Seleção de Pilotos
    st.subheader("Comparativo de Voltas por Piloto")
    with st.spinner("Buscando pilotos da sessão..."):
        drivers = get_drivers_from_session(db, selected_session_key)
    
    if not drivers:
        st.warning("⚠️ Nenhum piloto encontrado para esta sessão.")
        st.stop()

    driver_map = {
        f"{d.get('full_name', 'Desconhecido')} ({d.get('team_name', 'Equipe N/A')})": d['driver_number'] 
        for d in drivers
    }
    
    selected_drivers_names = st.multiselect(
        "Selecione um ou mais pilotos para comparar:",
        options=list(driver_map.keys()),
        default=list(driver_map.keys())[:2]
    )

    if not selected_drivers_names:
        st.info("ℹ️ Por favor, selecione pelo menos um piloto para visualizar os dados.")
        st.stop()

    selected_driver_numbers = [driver_map[name] for name in selected_drivers_names]

    # Buscar e processar dados das voltas
    with st.spinner("Buscando dados de voltas na API..."):
        laps_df = get_laps_for_drivers(db, selected_session_key, selected_driver_numbers)

    if laps_df.empty:
        st.warning("⚠️ Não foram encontrados dados de voltas para os pilotos selecionados nesta sessão.")
    else:
        driver_number_to_name = {v: k for k, v in driver_map.items()}
        laps_df['driver_name'] = laps_df['driver_number'].map(driver_number_to_name)
        
        laps_df = laps_df.dropna(subset=['lap_duration'])
        laps_df = laps_df[laps_df['lap_duration'] > 0]

        # Gráfico de Linha Comparativo de Tempos de Volta
        st.subheader("📈 Gráfico de Desempenho (Tempo de Volta)")
        fig = px.line(
            laps_df,
            x="lap_number",
            y="lap_duration",
            color="driver_name",
            title="Comparativo de Tempo de Volta Durante a Corrida",
            labels={
                "lap_number": "Número da Volta",
                "lap_duration": "Duração da Volta (segundos)",
                "driver_name": "Piloto"
            },
            markers=True
        )
        st.plotly_chart(fig, use_container_width=True)

        with st.expander("📋 Ver tabela de dados das voltas"):
            st.dataframe(
                laps_df[['driver_name', 'lap_number', 'lap_duration']]
                .sort_values(by=['driver_name', 'lap_number'])
                .reset_index(drop=True)
            )