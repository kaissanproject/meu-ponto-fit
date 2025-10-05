import os
import psycopg2
from flask import Flask, render_template, request, jsonify

# --- CONFIGURAÇÃO ---
app = Flask(__name__)

# Função para obter a conexão com o banco de dados
def get_db_connection():
    """Cria e retorna uma nova conexão com o banco de dados."""
    conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
    return conn

# --- FÓRMULAS DA DIETA DOS PONTOS ---
def calcular_pontos(calorias, gordura, fibra, proteina):
    """Calcula os pontos de um alimento com base em seus valores nutricionais."""
    # A fibra é limitada a 4g no cálculo original
    fibra_limitada = min(fibra, 4)
    
    # Fórmula dos Pontos (uma das versões mais comuns)
    pontos_proteina = proteina / 10
    pontos_calorias = calorias / 50
    pontos_gordura = gordura / 12
    pontos_fibra = fibra_limitada / 5
    
    total_pontos = pontos_calorias + pontos_gordura - pontos_fibra - pontos_proteina
    
    # Arredonda para o número inteiro mais próximo e garante que seja no mínimo 0
    return max(0, round(total_pontos))

# --- ROTAS DA APLICAÇÃO (ENDPOINTS) ---

@app.route('/')
def index():
    """Renderiza a página principal da aplicação."""
    return render_template('index.html')

@app.route('/search')
def search():
    """Endpoint de busca para o autocomplete de alimentos."""
    query = request.args.get('q', '')
    if len(query) < 2:
        return jsonify([])

    conn = get_db_connection()
    with conn.cursor() as cur:
        # Busca por alimentos que começam com o texto digitado (case-insensitive)
        cur.execute("SELECT nome_alimento FROM alimentos WHERE nome_alimento ILIKE %s LIMIT 10", (query + '%',))
        alimentos = [row[0] for row in cur.fetchall()]
    conn.close()
    return jsonify(alimentos)

@app.route('/calculate', methods=['POST'])
def calculate():
    """Endpoint que recebe um alimento e quantidade, e calcula os pontos."""
    # Tenta obter os dados como JSON. silent=True evita que ele quebre se não for JSON.
    data = request.get_json(silent=True)

    # Se não for JSON, tenta obter os dados como um formulário tradicional.
    if data is None and request.form:
        data = request.form.to_dict()

    if not data or 'alimento' not in data or 'quantidade' not in data or not data['alimento'] or not data['quantidade']:
        return jsonify({'error': 'Nome do alimento e quantidade são obrigatórios.'}), 400

    nome_alimento = data['alimento']
    try:
        quantidade_gramas = float(data['quantidade'])
    except (ValueError, TypeError):
        return jsonify({'error': 'Quantidade deve ser um número válido.'}), 400

    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT calorias_kcal, gordura_total_g, fibra_alimentar_g, proteina_g FROM alimentos WHERE nome_alimento = %s", (nome_alimento,))
        alimento_data = cur.fetchone()
    conn.close()

    if not alimento_data:
        return jsonify({'error': 'Alimento não encontrado no banco de dados.'}), 404

    # Calcula os valores para a quantidade informada, tratando valores nulos (None)
    calorias, gordura, fibra, proteina = [((float(val) / 100) * quantidade_gramas) if val is not None else 0 for val in alimento_data]
    
    pontos = calcular_pontos(calorias, gordura, fibra, proteina)

    return jsonify({
        'alimento': nome_alimento,
        'quantidade': int(quantidade_gramas),
        'pontos': pontos
    })

# --- INICIALIZAÇÃO DA APLICAÇÃO ---
if __name__ == '__main__':
    # Esta parte é usada para rodar a aplicação localmente (não usada pela Render)
    # A Render usa o comando definido no "Start Command", como 'gunicorn app:app'
    app.run(debug=True)

