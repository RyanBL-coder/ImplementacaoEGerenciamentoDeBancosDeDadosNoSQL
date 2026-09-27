import streamlit as st
import requests
import json
import pandas as pd

# Configurações
RIAK_URL = "http://localhost:8098"

# -------------------------------
# Funções auxiliares
# -------------------------------

def inserir_objeto(bucket_type, bucket, key, data, indexes=None):
    url = f"{RIAK_URL}/types/{bucket_type}/buckets/{bucket}/keys/{key}"
    headers = {"Content-Type": "application/json"}

    if indexes:
        for nome, valor in indexes.items():
            headers[f"x-riak-index-{nome}"] = valor

    r = requests.put(url, headers=headers, data=json.dumps(data))
    return r.status_code == 204 or r.status_code == 201


def buscar_por_chave(bucket_type, bucket, key):
    url = f"{RIAK_URL}/types/{bucket_type}/buckets/{bucket}/keys/{key}"
    r = requests.get(url)
    if r.status_code == 200:
        return r.json()
    return None


def buscar_por_indice(bucket_type, bucket, index, value):
    url = f"{RIAK_URL}/types/{bucket_type}/buckets/{bucket}/index/{index}/{value}"
    r = requests.get(url)
    if r.status_code == 200:
        return r.json().get("keys", [])
    return []


def incrementar_contador(bucket, key, valor=1):
    url = f"{RIAK_URL}/buckets/{bucket}/counters/{key}"
    r = requests.post(url, data=str(valor))
    return r.status_code == 204


def ler_contador(bucket, key):
    url = f"{RIAK_URL}/buckets/{bucket}/counters/{key}"
    r = requests.get(url)
    if r.status_code == 200:
        return int(r.text)
    return None


# -------------------------------
# Interface Streamlit
# -------------------------------
st.set_page_config(page_title="Riak Explorer com Python", layout="wide")

st.title("🐶 Riak Explorer com Python + Streamlit")
st.markdown("Interface para inserir, consultar e visualizar objetos no **Riak KV**.")

# Inserir alguns objetos automaticamente
if st.button("🔄 Inserir Objetos de Exemplo"):
    objetos = [
        ("rufus", {"name": "Rufus", "breed": "Labrador", "owner": "Ana"}, {"species_bin": "dog", "age_int": "5"}),
        ("kira", {"name": "Kira", "breed": "Border Collie", "owner": "Bruno"}, {"species_bin": "dog", "age_int": "2"}),
        ("thor", {"name": "Thor", "breed": "Pastor Alemão", "owner": "Carlos"}, {"species_bin": "dog", "age_int": "4"}),
        ("luna", {"name": "Luna", "breed": "Poodle", "owner": "Diana"}, {"species_bin": "dog", "age_int": "7"}),
        ("mimi", {"name": "Mimi", "breed": "Siamês", "owner": "Eva"}, {"species_bin": "cat", "age_int": "3"}),
        ("garfield", {"name": "Garfield", "breed": "Persa", "owner": "Felipe"}, {"species_bin": "cat", "age_int": "6"}),
    ]

    for key, data, indexes in objetos:
        inserir_objeto("animals", "pets", key, data, indexes)

    st.success("✅ Objetos de exemplo inseridos no Riak!")

# -------------------------------
# Consultas
# -------------------------------
st.subheader("🔍 Consultar por Chave")
key = st.text_input("Digite a chave do objeto", "rufus")
if st.button("Buscar por Chave"):
    obj = buscar_por_chave("animals", "pets", key)
    if obj:
        st.json(obj)
    else:
        st.warning("Objeto não encontrado.")

st.subheader("📂 Consultar por Índice")
index = st.selectbox("Escolha o índice", ["species_bin", "age_int"])
value = st.text_input("Valor do índice", "dog")

if st.button("Buscar por Índice"):
    keys = buscar_por_indice("animals", "pets", index, value)
    if keys:
        resultados = []
        for k in keys:
            obj = buscar_por_chave("animals", "pets", k)
            if obj:
                resultados.append({"key": k, **obj})
        df = pd.DataFrame(resultados)
        st.dataframe(df)
    else:
        st.warning("Nenhum objeto encontrado para este índice.")

# -------------------------------
# Contadores
# -------------------------------
st.subheader("📊 Contador de Visualizações")
if st.button("Incrementar Contador"):
    incrementar_contador("metrics", "home_views", 1)

valor = ler_contador("metrics", "home_views")
if valor is not None:
    st.metric("Home Views", valor)
else:
    st.info("Nenhum contador encontrado ainda.")
