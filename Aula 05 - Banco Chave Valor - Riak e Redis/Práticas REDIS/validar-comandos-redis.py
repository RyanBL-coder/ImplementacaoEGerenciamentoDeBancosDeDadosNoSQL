## python3 validar_exercicios_redis.py

import time
import redis


def conectar_redis():
    """Conecta ao servidor Redis local no WSL (localhost:6379)."""
    try:
        r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
        r.ping()
        print("✅ Conexão com o Redis estabelecida com sucesso!\n")
        return r
    except redis.ConnectionError:
        print("❌ Erro: Não foi possível conectar ao Redis.")
        print("Certifique-se de que o servidor está rodando no WSL:")
        print("   sudo service redis-server start")
        exit(1)


def executar_exercicios():
    r = conectar_redis()

    # Limpa o banco de dados antes de iniciar para garantir ambiente limpo
    r.flushdb()

    print("=" * 60)
    print("      EXECUÇÃO E VALIDAÇÃO DOS EXERCÍCIOS - REDIS CLI")
    print("=" * 60 + "\n")

    # -------------------------------------------------------------
    # 1. STRINGS (MANIPULAÇÃO BÁSICA DE CHAVES)
    # -------------------------------------------------------------
    print("--- [BLOCO 1: STRINGS] ---")

    # Exercício 01
    r.set("sistema:nome", "DataPlatform")
    res1 = r.get("sistema:nome")
    print(
        f"[Ex 01] SET / GET -> sistema:nome = '{res1}' | "
        f"{'OK' if res1 == 'DataPlatform' else 'FAIL'}"
    )

    # Exercício 02
    r.mset(
        {"env:db": "postgres", "env:cache": "redis", "env:queue": "rabbitmq"}
    )
    res2 = r.mget("env:db", "env:cache")
    print(
        f"[Ex 02] MSET / MGET -> env:db={res2[0]}, env:cache={res2[1]} | "
        f"{'OK' if res2 == ['postgres', 'redis'] else 'FAIL'}"
    )

    # Exercício 03
    r.setex("sessao:usuario:101", 30, "xyz123")
    ttl = r.ttl("sessao:usuario:101")
    res3 = r.get("sessao:usuario:101")
    print(
        f"[Ex 03] SETEX / TTL -> valor='{res3}', TTL={ttl}s | "
        f"{'OK' if res3 == 'xyz123' and ttl > 0 else 'FAIL'}"
    )

    # Exercício 04
    r.incr("pageviews:home")  # 1
    r.incrby("pageviews:home", 5)  # 6
    r.decrby("pageviews:home", 2)  # 4
    res4 = int(r.get("pageviews:home"))
    print(
        f"[Ex 04] INCR / INCRBY / DECRBY -> pageviews:home = {res4} | "
        f"{'OK' if res4 == 4 else 'FAIL'}"
    )

    print()

    # -------------------------------------------------------------
    # 2. HASHES (OBJETOS E DICIONÁRIOS)
    # -------------------------------------------------------------
    print("--- [BLOCO 2: HASHES] ---")

    # Exercício 05
    r.hset(
        "usuario:201",
        mapping={
            "nome": "Carlos",
            "email": "carlos@email.com",
            "nivel": "admin",
        },
    )
    res5 = r.hexists("usuario:201", "nome")
    print(
        f"[Ex 05] HSET -> Hash 'usuario:201' criado | "
        f"{'OK' if res5 else 'FAIL'}"
    )

    # Exercício 06
    email = r.hget("usuario:201", "email")
    todos_campos = r.hgetall("usuario:201")
    print(f"[Ex 06] HGET email -> {email}")
    print(f"        HGETALL usuario:201 -> {todos_campos}")

    # Exercício 07
    r.hincrby("usuario:201", "tentativas_login", 1)
    chaves_hash = r.hkeys("usuario:201")
    print(
        f"[Ex 07] HINCRBY / HKEYS -> Chaves no hash: {chaves_hash} | "
        f"{'OK' if 'tentativas_login' in chaves_hash else 'FAIL'}"
    )

    print()

    # -------------------------------------------------------------
    # 3. LISTS (FILAS E PILHAS)
    # -------------------------------------------------------------
    print("--- [BLOCO 3: LISTS] ---")

    # Exercício 08
    r.rpush("fila:email", "email_1", "email_2", "email_3")
    tamanho_lista = r.llen("fila:email")
    print(
        f"[Ex 08] RPUSH -> Fila criada com {tamanho_lista} itens | "
        f"{'OK' if tamanho_lista == 3 else 'FAIL'}"
    )

    # Exercício 09
    item_removido = r.lpop("fila:email")
    print(
        f"[Ex 09] LPOP -> Item removido da fila: '{item_removido}' | "
        f"{'OK' if item_removido == 'email_1' else 'FAIL'}"
    )

    # Exercício 10
    itens_restantes = r.lrange("fila:email", 0, -1)
    print(
        f"[Ex 10] LRANGE -> Itens restantes na fila: {itens_restantes} | "
        f"{'OK' if itens_restantes == ['email_2', 'email_3'] else 'FAIL'}"
    )

    print()

    # -------------------------------------------------------------
    # 4. SETS (CONJUNTOS NÃO ORDENADOS E SEM DUPLICATAS)
    # -------------------------------------------------------------
    print("--- [BLOCO 4: SETS] ---")

    # Exercício 11
    r.sadd("tags:post:1", "dados", "redis", "nosql", "redis")
    qtd_elementos = r.scard("tags:post:1")
    print(
        f"[Ex 11] SADD / SCARD -> Elementos únicos inseridos: {qtd_elementos} | "
        f"{'OK' if qtd_elementos == 3 else 'FAIL'}"
    )

    # Exercício 12
    r.sadd("tags:post:2", "redis", "python", "backend")
    intersecao = r.sinter("tags:post:1", "tags:post:2")
    print(
        f"[Ex 12] SINTER -> Interseção dos posts: {intersecao} | "
        f"{'OK' if intersecao == {'redis'} else 'FAIL'}"
    )

    # Exercício 13
    is_member = r.sismember("tags:post:1", "python")
    print(
        f"[Ex 13] SISMEMBER -> 'python' pertence a 'tags:post:1'? {bool(is_member)} | "
        f"{'OK' if not is_member else 'FAIL'}"
    )

    print()

    # -------------------------------------------------------------
    # 5. SORTED SETS (CONJUNTOS ORDENADOS POR SCORE)
    # -------------------------------------------------------------
    print("--- [BLOCO 5: SORTED SETS] ---")

    # Exercício 14
    r.zadd("placar:game", {"alice": 1500, "bob": 2200, "carol": 1800})
    total_jogadores = r.zcard("placar:game")
    print(
        f"[Ex 14] ZADD -> Placar criado com {total_jogadores} jogadores | "
        f"{'OK' if total_jogadores == 3 else 'FAIL'}"
    )

    # Exercício 15
    ranking = r.zrevrange("placar:game", 0, -1, withscores=True)
    print(f"[Ex 15] ZREVRANGE -> Ranking por Pontuação:")
    for pos, (jogador, score) in enumerate(ranking, start=1):
        print(f"        {pos}º Lugar: {jogador} - {int(score)} pts")

    # Exercício 16
    r.zincrby("placar:game", 800, "alice")  # 1500 + 800 = 2300 (assume 1º lugar)
    nova_posicao = r.zrevrank("placar:game", "alice")  # Índice 0 = 1º lugar
    novo_score = r.zscore("placar:game", "alice")
    print(
        f"[Ex 16] ZINCRBY / ZREVRANK -> Alice agora tem {int(novo_score)} pts "
        f"e está na posição {nova_posicao + 1}º do ranking | "
        f"{'OK' if nova_posicao == 0 else 'FAIL'}"
    )

    print()

    # -------------------------------------------------------------
    # 6. PUB/SUB, TRANSAÇÕES E ADMINISTRAÇÃO
    # -------------------------------------------------------------
    print("--- [BLOCO 6: PUB/SUB, TRANSAÇÕES E ADMIN] ---")

    # Exercício 17 (Pub/Sub)
    pubsub = r.pubsub()
    pubsub.subscribe("notificacoes")
    time.sleep(0.1)  # Aguarda tempo de registro do subscription

    r.publish("notificacoes", "Novo relatorio disponivel")

    # Captura a mensagem enviada
    msg = None
    while True:
        mensagem = pubsub.get_message(timeout=1.0)
        if mensagem and mensagem["type"] == "message":
            msg = mensagem["data"]
            break

    print(
        f"[Ex 17] SUBSCRIBE / PUBLISH -> Mensagem recebida no canal: '{msg}' | "
        f"{'OK' if msg == 'Novo relatorio disponivel' else 'FAIL'}"
    )
    pubsub.unsubscribe("notificacoes")

    # Exercício 18 (Transações - Pipeline / MULTI EXEC)
    r.set("conta:A", 100)
    r.set("conta:B", 50)

    pipe = r.pipeline(transaction=True)
    pipe.decrby("conta:A", 50)
    pipe.incrby("conta:B", 50)
    resultados_transacao = pipe.execute()

    saldo_A = int(r.get("conta:A"))
    saldo_B = int(r.get("conta:B"))
    print(
        f"[Ex 18] MULTI/EXEC (Transação) -> Saldo Conta A: R${saldo_A}, Saldo Conta B: R${saldo_B} | "
        f"{'OK' if saldo_A == 50 and saldo_B == 100 else 'FAIL'}"
    )

    # Exercício 19 (Gerenciamento de Chaves)
    r.set("sistema:nome", "AppTeste")
    existe_antes = r.exists("sistema:nome")
    r.rename("sistema:nome", "sistema:app")
    r.delete("sistema:app")
    existe_depois = r.exists("sistema:app")

    print(
        f"[Ex 19] EXISTS / RENAME / DEL -> Chave renomeada e excluída | "
        f"{'OK' if existe_antes == 1 and existe_depois == 0 else 'FAIL'}"
    )

    # Exercício 20 (Inspeção e Limpeza)
    info_memoria = r.info("memory")
    memoria_usada = info_memoria.get("used_memory_human", "N/A")
    print(f"[Ex 20] INFO memory -> Memória em uso pelo Redis: {memoria_usada}")

    r.flushdb()
    total_chaves = r.dbsize()
    print(
        f"        FLUSHDB -> Chaves restantes no banco: {total_chaves} | "
        f"{'OK' if total_chaves == 0 else 'FAIL'}"
    )

    print("\n" + "=" * 60)
    print("    TODOS OS 20 EXERCÍCIOS FORAM EXECUTADOS COM SUCESSO!")
    print("=" * 60)


if __name__ == "__main__":
    executar_exercicios()