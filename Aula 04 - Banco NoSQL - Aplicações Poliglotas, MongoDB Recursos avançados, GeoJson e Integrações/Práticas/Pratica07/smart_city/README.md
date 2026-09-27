# 🏙️ Smart City Dashboard

Dashboard analítico e geoespacial para visualização de dados de cidade inteligente, utilizando arquitetura de banco de dados duplo (MongoDB + SQLite).

## 🎯 Funcionalidades

- **Mapas Interativos**: Visualização de pontos, linhas e polígonos em mapas
- **Analytics Avançado**: Gráficos estatísticos com Plotly
- **Filtros Dinâmicos**: Filtre por categoria, raio, data e região
- **Persistência de Estado**: Salve e carregue configurações de visualização
- **Queries Geoespaciais**: Busca por proximidade, dentro de polígonos e interseções
- **API REST Completa**: Backend robusto com FastAPI

## 🏗️ Arquitetura

### Banco de Dados Duplo

**MongoDB (NoSQL)**
- Dados geoespaciais (GeoJSON)
- Índices 2dsphere para queries eficientes
- Flexibilidade para documentos complexos

**SQLite (SQL)**
- Metadados e categorias
- Persistência de visualizações salvas
- Logs de auditoria

### Componentes

- **Backend**: FastAPI + MongoDB + SQLite
- **Frontend**: Streamlit + Folium + Plotly
- **Banco Geoespacial**: MongoDB com índices 2dsphere
- **Banco Relacional**: SQLite para estado e metadados

## 🚀 Instalação e Execução

### Pré-requisitos

- Python 3.11+
- MongoDB (local ou Docker)
- pip

### Opção 1: Execução Local

1. **Instalar dependências**
```bash
pip install -r requirements.txt