from pymongo import MongoClient, GEOSPHERE
from pymongo.errors import ConnectionFailure
import os

class MongoDBConnection:
    def __init__(self):
        self.client = None
        self.db = None
        
    def connect(self):
        try:
            mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
            self.client = MongoClient(mongo_uri)
            self.db = self.client["geo_analytics"]
            print("✅ MongoDB conectado com sucesso")
            return True
        except ConnectionFailure as e:
            print(f"❌ Erro ao conectar no MongoDB: {e}")
            return False
    
    def get_collection(self, collection_name):
        if self.db is None:
            self.connect()
        return self.db[collection_name]
    
    def create_geospatial_index(self, collection_name):
        collection = self.get_collection(collection_name)
        collection.create_index([("geometry", GEOSPHERE)])
        print(f"✅ Índice geoespacial criado em {collection_name}")
    
    def close(self):
        if self.client:
            self.client.close()

# Instância global
mongo_conn = MongoDBConnection()