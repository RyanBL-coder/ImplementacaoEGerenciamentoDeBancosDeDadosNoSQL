import sqlite3
import os
import sys

def verificar_integridade(db_path):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check;")
        resultado = cursor.fetchone()[0]
        conn.close()
        return resultado
    except Exception as e:
        return f"Erro ao abrir o banco: {e}"

def recriar_banco(origem, destino):
    try:
        # Conecta no banco original
        conn = sqlite3.connect(origem)
        with open("backup.sql", "w", encoding="utf-8") as f:
            for linha in conn.iterdump():
                f.write(f"{linha}\n")
        conn.close()

        # Cria novo banco a partir do dump
        conn_novo = sqlite3.connect(destino)
        with open("backup.sql", "r", encoding="utf-8") as f:
            conn_novo.executescript(f.read())
        conn_novo.close()

        print(f"Novo banco recriado com sucesso em: {destino}")
    except Exception as e:
        print(f"Erro ao recriar banco: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python recuperar_sqlite.py banco_corrompido.db")
        sys.exit(1)

    banco = sys.argv[1]
    novo_banco = "banco_recuperado.db"

    print(f"Verificando integridade do banco: {banco}")
    status = verificar_integridade(banco)
    print(f"Resultado integrity_check: {status}")

    if status != "ok":
        print("⚠️ Banco corrompido! Tentando recriar...")
        recriar_banco(banco, novo_banco)
    else:
        print("✅ O banco está íntegro. Nenhuma ação necessária.")
