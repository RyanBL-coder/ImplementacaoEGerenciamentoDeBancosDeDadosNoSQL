import requests
import pandas as pd
import geopandas as gpd
from pymongo import MongoClient
from shapely.geometry import Point
import os

# Link1 = https://dados.gov.br/dataset/3b966e22-3a80-4464-9e3e-3c83f2e8b0c5/resource/e8a10748-423c-433a-9523-14c1c2eba6cf/download/ubs.csv
# Link2 = https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/PDA/UNIDADES_BASICAS_SAUDE/ubs.csv
# Link3 = https://dados.gov.br/dataset/3d504e57-3c8d-4e1e-99c2-0f2315a9f0c7/resource/df1b1942-8a4e-4c4e-8eb1-4b6d0cbb3c8f/download/escolas.csv

# Configurações
URL_DADOS = "https://s3-sa-east-1.amazonaws.com/ckan.saude.gov.br/UBS/ubs.csv"
NOME_ARQUIVO = "ubs.csv"
MONGO_URI = "mongodb://localhost:27017/"
NOME_BANCO = "geodados"
NOME_COLECAO = "unidades_saude"

def baixar_dados():
    """Baixa o arquivo CSV de Unidades Básicas de Saúde"""
    print("Baixando dados de UBS...")
    try:
        response = requests.get(URL_DADOS, stream=True)
        response.raise_for_status()
        
        with open(NOME_ARQUIVO, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"Dados salvos em {NOME_ARQUIVO}")
        return True
    except Exception as e:
        print(f"Erro ao baixar dados: {e}")
        return False

def processar_dados():
    """Processa os dados e converte para GeoJSON"""
    print("Processando dados...")
    
    # Carregar CSV
    df = pd.read_csv(NOME_ARQUIVO, sep=';', encoding='latin-1', low_memory=False)
    
    # Selecionar colunas relevantes
    colunas = [
        'CO_UF', 'NO_UF', 'CO_MUNICIPIO_GESTOR', 'NO_MUNICIPIO_GESTOR',
        'CO_CNES', 'NU_LATITUDE', 'NU_LONGITUDE', 'NO_LOGRADOURO',
        'NO_BAIRRO', 'CO_CEP', 'NU_TELEFONE'
    ]
    df = df[colunas].copy()
    
    # Renomear colunas
    df.columns = [
        'cod_uf', 'uf', 'cod_municipio', 'municipio',
        'cod_cnes', 'latitude', 'longitude', 'logradouro',
        'bairro', 'cep', 'telefone'
    ]
    
    # Converter coordenadas para numérico
    df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
    df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
    
    # Remover registros sem coordenadas
    df = df.dropna(subset=['latitude', 'longitude'])
    
    # Criar geometria
    geometry = [Point(xy) for xy in zip(df['longitude'], df['latitude'])]
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4674")
    
    # Converter para GeoJSON
    geojson_data = gdf.to_json()
    
    print(f"Dados processados: {len(gdf)} registros válidos")
    return geojson_data, gdf

def salvar_no_mongodb(geojson_data, gdf):
    """Salva os dados no MongoDB com índice geoespacial"""
    print("Conectando ao MongoDB...")
    
    try:
        # Conectar ao MongoDB
        client = MongoClient(MONGO_URI)
        db = client[NOME_BANCO]
        collection = db[NOME_COLECAO]
        
        # Limpar coleção existente
        collection.delete_many({})
        
        # Converter GeoDataFrame para lista de dicionários
        features = []
        for _, row in gdf.iterrows():
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [row['longitude'], row['latitude']]
                },
                "properties": {
                    "cod_uf": int(row['cod_uf']),
                    "uf": row['uf'],
                    "cod_municipio": int(row['cod_municipio']),
                    "municipio": row['municipio'],
                    "cod_cnes": int(row['cod_cnes']),
                    "logradouro": row['logradouro'],
                    "bairro": row['bairro'],
                    "cep": str(row['cep']).replace('.0', ''),
                    "telefone": str(row['telefone']).replace('.0', '')
                }
            }
            features.append(feature)
        
        # Inserir dados
        result = collection.insert_many(features)
        print(f"Inseridos {len(result.inserted_ids)} documentos no MongoDB")
        
        # Criar índice geoespacial
        collection.create_index([("geometry", "2dsphere")])
        print("Índice geoespacial criado com sucesso")
        
        return True
    except Exception as e:
        print(f"Erro ao salvar no MongoDB: {e}")
        return False

def main():
    """Função principal de execução"""
    # Baixar dados
    if not baixar_dados():
        return
    
    # Processar dados
    geojson_data, gdf = processar_dados()
    
    # Salvar no MongoDB
    if salvar_no_mongodb(geojson_data, gdf):
        print("\nProcesso concluído com sucesso!")
        print(f"Dados disponíveis no MongoDB: {NOME_BANCO}.{NOME_COLECAO}")
    else:
        print("\nOcorreu um erro durante o processo")
    
    # Limpar arquivo temporário
    if os.path.exists(NOME_ARQUIVO):
        os.remove(NOME_ARQUIVO)

if __name__ == "__main__":
    main()
