import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

# Configuração da página
st.set_page_config(
    page_title="Smart City Dashboard",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configurações
API_URL = "http://localhost:8000/api/v1"

# Inicializar session state
if 'filters' not in st.session_state:
    st.session_state.filters = {
        'categories': [],
        'radius': 1000,
        'date_from': None,
        'date_to': None
    }

if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False

# Funções auxiliares
@st.cache_data(ttl=60)
def fetch_categories():
    """Buscar categorias da API"""
    try:
        response = requests.get(f"{API_URL}/categories")
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return []

@st.cache_data(ttl=60)
def fetch_spatial_data(category=None):
    """Buscar dados geoespaciais"""
    try:
        params = {}
        if category:
            params['category'] = category
        
        response = requests.get(f"{API_URL}/spatial-data", params=params)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return []

@st.cache_data(ttl=60)
def fetch_analytics():
    """Buscar dados de analytics"""
    try:
        response = requests.get(f"{API_URL}/analytics/aggregated")
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return {}

def save_current_view():
    """Salvar visualização atual"""
    view_name = st.session_state.get('view_name', '')
    if not view_name:
        st.error("Digite um nome para a visualização")
        return
    
    try:
        response = requests.post(
            f"{API_URL}/dashboard-views",
            json={
                "name": view_name,
                "filters": st.session_state.filters
            }
        )
        if response.status_code == 200:
            st.success(f"Visualização '{view_name}' salva com sucesso!")
            st.session_state.view_name = ''
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")

def load_view(view_id):
    """Carregar visualização salva"""
    try:
        response = requests.get(f"{API_URL}/dashboard-views")
        if response.status_code == 200:
            views = response.json()
            view = next((v for v in views if v['id'] == view_id), None)
            if view:
                st.session_state.filters = view['filters']
                st.success(f"Visualização '{view['name']}' carregada!")
                st.rerun()
    except Exception as e:
        st.error(f"Erro ao carregar: {e}")

# ==================== SIDEBAR ====================
with st.sidebar:
    st.title("🏙️ Smart City")
    st.markdown("---")
    
    # Filtros
    st.subheader("🔍 Filtros")
    
    categories = fetch_categories()
    category_names = [cat['name'] for cat in categories]
    
    selected_categories = st.multiselect(
        "Categorias",
        category_names,
        default=st.session_state.filters.get('categories', [])
    )
    st.session_state.filters['categories'] = selected_categories
    
    radius = st.slider(
        "Raio de busca (metros)",
        min_value=100,
        max_value=10000,
        value=st.session_state.filters.get('radius', 1000),
        step=100
    )
    st.session_state.filters['radius'] = radius
    
    col1, col2 = st.columns(2)
    with col1:
        date_from = st.date_input(
            "Data inicial",
            value=datetime.now() - timedelta(days=30)
        )
        st.session_state.filters['date_from'] = date_from
    
    with col2:
        date_to = st.date_input(
            "Data final",
            value=datetime.now()
        )
        st.session_state.filters['date_to'] = date_to
    
    st.markdown("---")
    
    # Salvar/Carregar Views
    st.subheader("💾 Visualizações")
    
    view_name = st.text_input("Nome da visualização", key="view_name")
    if st.button("Salvar Visualização Atual"):
        save_current_view()
    
    st.markdown("**Visualizações Salvas:**")
    try:
        response = requests.get(f"{API_URL}/dashboard-views")
        if response.status_code == 200:
            views = response.json()
            for view in views:
                col1, col2 = st.columns([3, 1])
                with col1:
                    if st.button(view['name'], key=f"load_{view['id']}"):
                        load_view(view['id'])
                with col2:
                    if st.button("🗑️", key=f"del_{view['id']}"):
                        requests.delete(f"{API_URL}/dashboard-views/{view['id']}")
                        st.rerun()
    except:
        st.info("Nenhuma visualização salva")
    
    st.markdown("---")
    st.markdown("**Estatísticas Rápidas**")
    
    # Buscar dados filtrados
    all_data = []
    if selected_categories:
        for cat in selected_categories:
            all_data.extend(fetch_spatial_data(cat))
    else:
        all_data = fetch_spatial_data()
    
    st.metric("Total de Pontos", len(all_data))
    
    if selected_categories:
        for cat in selected_categories:
            count = len([d for d in all_data if d['category'] == cat])
            st.metric(f"{cat.title()}", count)

# ==================== MAIN CONTENT ====================
st.title("📊 Dashboard de Cidade Inteligente")
st.markdown("Análise geoespacial e estatística de dados urbanos")

# Tabs
tab1, tab2 = st.tabs(["🗺️ Mapa Interativo", "📈 Analytics"])

with tab1:
    st.subheader("Visualização Geoespacial")
    
    # Importar mapa
    from dashboard.pages.map_view import render_map
    
    # Buscar dados
    if selected_categories:
        map_data = []
        for cat in selected_categories:
            map_data.extend(fetch_spatial_data(cat))
    else:
        map_data = fetch_spatial_data()
    
    # Renderizar mapa
    if map_data:
        render_map(map_data, categories)
    else:
        st.info("Nenhum dado encontrado com os filtros selecionados")

with tab2:
    st.subheader("Análises Estatísticas")
    
    # Importar analytics
    from dashboard.pages.analytics import render_analytics
    
    # Buscar dados
    analytics_data = fetch_analytics()
    
    if selected_categories:
        chart_data = []
        for cat in selected_categories:
            chart_data.extend(fetch_spatial_data(cat))
    else:
        chart_data = fetch_spatial_data()
    
    # Renderizar analytics
    if chart_data:
        render_analytics(chart_data, analytics_data)
    else:
        st.info("Nenhum dado disponível para análise")