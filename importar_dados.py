import os
import psycopg2
import pandas as pd

# --- CONFIGURAÇÃO ---
# IMPORTANTE: Cole a "Internal Database URL" fornecida pela Render aqui.
# Exemplo: "postgres://seu_usuario:sua_senha@seu_host/seu_banco"
# APÓS USAR O SCRIPT, É RECOMENDADO REMOVER A URL DESTE ARQUIVO POR SEGURANÇA.
DATABASE_URL = "colar aqui"
CSV_FILE_PATH = 'alimentos.csv'

def criar_tabela(conn):
    """Cria a tabela 'alimentos' no banco de dados se ela não existir."""
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS alimentos (
                id SERIAL PRIMARY KEY,
                nome_alimento TEXT NOT NULL UNIQUE,
                calorias_kcal NUMERIC(10, 2),
                gordura_total_g NUMERIC(10, 2),
                fibra_alimentar_g NUMERIC(10, 2),
                proteina_g NUMERIC(10, 2)
            );
        """)
        conn.commit()
        print("Tabela 'alimentos' verificada/criada com sucesso.")

def importar_dados(conn, file_path):
    """Lê os dados do arquivo CSV e os insere na tabela 'alimentos'."""
    try:
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        print(f"Erro: O arquivo {file_path} não foi encontrado.")
        return

    with conn.cursor() as cur:
        total_rows = len(df)
        for index, row in df.iterrows():
            # Verifica se o alimento já existe para evitar duplicatas
            cur.execute(
                "SELECT id FROM alimentos WHERE nome_alimento = %s;",
                (row['nome_alimento'],)
            )
            if cur.fetchone() is None:
                # Se não existe, insere o novo alimento
                cur.execute(
                    """
                    INSERT INTO alimentos (nome_alimento, calorias_kcal, gordura_total_g, fibra_alimentar_g, proteina_g)
                    VALUES (%s, %s, %s, %s, %s);
                    """,
                    (row['nome_alimento'], row['calorias_kcal'], row['gordura_total_g'], row['fibra_alimentar_g'], row['proteina_g'])
                )
                print(f"Inserindo {index + 1}/{total_rows}: {row['nome_alimento']}")
            else:
                print(f"Ignorando (já existe) {index + 1}/{total_rows}: {row['nome_alimento']}")

    conn.commit()
    print("\nImportação concluída.")

def main():
    """Função principal que orquestra a conexão e a importação."""
    if DATABASE_URL == "SUA_URL_DE_CONEXAO_INTERNA_AQUI" or not DATABASE_URL:
        print("ERRO: Por favor, defina a variável DATABASE_URL com a sua URL de conexão do PostgreSQL da Render.")
        return

    conn = None
    try:
        # Conecta ao banco de dados PostgreSQL
        conn = psycopg2.connect(DATABASE_URL)
        print("Conexão com o banco de dados bem-sucedida!")

        # 1. Garante que a tabela exista
        criar_tabela(conn)

        # 2. Importa os dados do CSV para a tabela
        importar_dados(conn, CSV_FILE_PATH)

        print("\nDados importados com sucesso!")

    except psycopg2.Error as e:
        print(f"Erro ao conectar ou manipular o banco de dados: {e}")
    finally:
        # Garante que a conexão seja fechada
        if conn:
            conn.close()
            print("Conexão com o banco de dados fechada.")

if __name__ == "__main__":
    main()
