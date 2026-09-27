import streamlit as st
import folium
from streamlit_folium import st_folium
import json

def render_map(data, categories):
    """Renderizar mapa interativo com dados geoespaciais"""
    
    # Centro do mapa (São Paulo)
    map_center = [-23.5505, -46.6333]
    
    # Criar mapa base
    m = folium.Map(
        location=map_center,
        zoom_start=13,
        tiles='OpenStreetMap'
    )
    
    # Dicionário de cores por categoria
    category_colors = {cat['name']: cat.get('color', '#3388ff') for cat in categories}
    
    # Adicionar dados ao mapa
    for item in data:
        geometry = item['geometry']
        properties = item.get('properties', {})
        name = item['name']
        category = item['category']
        color = category_colors.get(category, '#3388ff')
        
        # Criar popup
        popup_content = f"""
        <b>{name}</b><br>
        Categoria: {category}<br>
        """
        
        for key, value in properties.items():
            popup_content += f"{key}: {value}<br>"
        
        popup = folium.Popup(popup_content, max_width=300)
        
        # Adicionar baseado no tipo de geometria
        if geometry['type'] == 'Point':
            lon, lat = geometry['coordinates']
            folium.CircleMarker(
                location=[lat, lon],
                radius=8,
                popup=popup,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.7
            ).add_to(m)
        
        elif geometry['type'] == 'Polygon':
            coords = geometry['coordinates'][0]
            # Converter [lon, lat] para [lat, lon]
            polygon_coords = [[coord[1], coord[0]] for coord in coords]
            
            folium.Polygon(
                locations=polygon_coords,
                popup=popup,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.3,
                weight=2
            ).add_to(m)
    
    # Renderizar mapa no Streamlit
    st_folium(m, width=None, height=600)
    
    # Legenda
    st.markdown("---")
    st.markdown("**Legenda:**")
    
    cols = st.columns(len(categories))
    for idx, cat in enumerate(categories):
        with cols[idx]:
            color = cat.get('color', '#3388ff')
            st.markdown(f"🟢 **{cat['name'].title()}**")