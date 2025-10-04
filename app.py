import os
import psycopg2
from flask import Flask, render_template, request, jsonify

# --- Inicialização do Flask ---
# Cria uma instância da aplicação Flask.
# O '__name__' é uma variável especial em Python que obtém o nome do módulo atual.
app = Flask(__name__)

# --- Configuração do Banco de Dados ---
# Pega a URL de conexão do banco de dados das variáveis de ambiente configuradas na Render.
# Isso é uma boa prática de segurança para não expor credenciais no código.
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    """Cria e retorna uma nova conexão com o banco de dados."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except psycopg2.Error as e:
        print(f"Erro ao conectar ao banco de dados: {e}")
        return None

# --- Definição da Fórmula de Pontos ---
# Esta é a lógica de negócio principal da nossa aplicação.
# A fórmula pode variar entre diferentes "Dietas dos Pontos".
# Usamos uma fórmula comum como exemplo: Pontos = (Calorias / 60) + (Gorduras / 9)
def calcular_pontos(calorias, gorduras):
    """Calcula os pontos de um alimento com base em suas calorias e gorduras."""
    if calorias is None or gorduras is None:
        return 0
    # A função max(0, ...) garante que o resultado nunca seja negativo.
    return max(0, round((float(calorias) / 60) + (float(gorduras) / 9)))

# --- Rotas da Aplicação (Endpoints) ---

@app.route('/')
def index():
    """
    Rota principal que renderiza a página inicial (index.html).
    O Flask procura por este arquivo na pasta 'templates' por padrão.
    """
    return render_template('index.html')

@app.route('/search')
def search():
    """
    Rota de API para a funcionalidade de autocomplete.
    Recebe um parâmetro 'q' da URL (ex: /search?q=arro) e busca no banco.
    """
    query = request.args.get('q', '')
    
    # Previne buscas vazias ou muito curtas para não sobrecarregar o banco.
    if len(query) < 2:
        return jsonify([])

    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Falha na conexão com o banco de dados"}), 500

    results = []
    try:
        with conn.cursor() as cur:
            # Usamos 'ILIKE' para uma busca case-insensitive (não diferencia maiúsculas/minúsculas).
            # O padrão 'query%' busca por alimentos que COMEÇAM com o texto digitado.
            # O 'LIMIT 10' restringe o número de resultados para melhorar a performance.
            search_query = f"{query}%"
            cur.execute(
                "SELECT nome_alimento FROM alimentos WHERE nome_alimento ILIKE %s ORDER BY nome_alimento LIMIT 10", 
                (search_query,)
            )
            # O fetchall() busca todas as linhas retornadas pela consulta.
            # Como cada linha é uma tupla com um elemento (o nome), extraímos esse elemento.
            results = [row[0] for row in cur.fetchall()]
    except psycopg2.Error as e:
        print(f"Erro na busca: {e}")
    finally:
        conn.close()

    # Retorna a lista de nomes de alimentos em formato JSON.
    return jsonify(results)

@app.route('/calculate', methods=['POST'])
def calculate():
    """
    Rota de API que recebe os dados do formulário, busca o alimento no banco,
    calcula os pontos e retorna o resultado.
    """
    data = request.get_json()
    food_name = data.get('food')
    quantity_str = data.get('quantity')

    # Validação básica dos dados recebidos.
    if not food_name or not quantity_str:
        return jsonify({'error': 'Nome do alimento e quantidade são obrigatórios.'}), 400

    try:
        quantity = float(quantity_str)
        if quantity <= 0:
            raise ValueError
    except ValueError:
        return jsonify({'error': 'A quantidade deve ser um número positivo.'}), 400

    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Falha na conexão com o banco de dados"}), 500

    try:
        with conn.cursor() as cur:
            # Busca os dados nutricionais exatos do alimento selecionado.
            cur.execute(
                "SELECT calorias_kcal, gordura_total_g FROM alimentos WHERE nome_alimento = %s",
                (food_name,)
            )
            food_data = cur.fetchone() # fetchone() pega a primeira (e única) linha do resultado.
        
        if food_data:
            calorias_por_100g, gorduras_por_100g = food_data
            
            # Cálculo proporcional à quantidade informada pelo usuário.
            calorias_total = (float(calorias_por_100g) / 100) * quantity
            gorduras_total = (float(gorduras_por_100g) / 100) * quantity
            
            # Usa a nossa função de cálculo de pontos.
            pontos = calcular_pontos(calorias_total, gorduras_total)
            
            # Retorna o resultado em formato JSON para o frontend.
            return jsonify({
                'pontos': pontos,
                'food_name': food_name,
                'quantity': quantity
            })
        else:
            return jsonify({'error': 'Alimento não encontrado no banco de dados.'}), 404

    except psycopg2.Error as e:
        print(f"Erro no cálculo: {e}")
        return jsonify({'error': 'Ocorreu um erro ao processar sua solicitação.'}), 500
    finally:
        conn.close()


# --- Execução da Aplicação ---
# Este bloco de código só é executado quando o script `app.py` é rodado diretamente.
# Quando a Render executa a aplicação via Gunicorn, esta parte não é usada.
if __name__ == '__main__':
    # O 'debug=True' é útil para desenvolvimento, pois reinicia o servidor
    # automaticamente a cada alteração no código e mostra erros detalhados no navegador.
    # NUNCA use debug=True em produção.
    app.run(debug=True)
