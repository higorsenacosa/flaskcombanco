
# Importação das bibliotecas necessárias para o Flask e funcionalidades
import json
from decimal import Decimal

from flask import Flask, flash, redirect, render_template, request, session, url_for

from database import (
    Categoria,
    Configuracao,
    ItemPedido,
    Pedido,
    Produto,
    Usuario,
    db,
    init_database,
)

# Criação da instância da aplicação Flask
app = Flask(__name__)

# Configurações da aplicação
app.secret_key = 'sua_chave_secreta_aqui_mude_em_producao'

# Configuração do banco de dados SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ecommerce.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializa o banco de dados
db.init_app(app)

# Inicializa o banco na primeira execução
@app.before_request
def criar_banco():
    """
    Executa apenas na primeira requisição para criar o banco
    """
    init_database(app)

# Função auxiliar para verificar se usuário está logado
def usuario_logado():
    """
    Retorna o usuário logado ou None
    """
    if 'usuario_logado' in session:
        return Usuario.query.get(session['usuario_logado']['id'])
    return None

# Função auxiliar para verificar se usuário é admin
def is_admin():
    """
    Verifica se o usuário logado é administrador
    """
    user = usuario_logado()
    return user and user.is_admin()

# Função auxiliar para calcular total do carrinho
def calcular_total_carrinho():
    """
    Calcula o valor total dos itens no carrinho da sessão atual
    Retorna o valor total como Decimal
    """
    total = Decimal('0.00')
    if 'carrinho' in session:
        for item in session['carrinho']:
            total += Decimal(str(item['preco'])) * item['quantidade']
    return total

# Função auxiliar para converter produto do banco para dict do carrinho
def produto_para_carrinho(produto, quantidade=1):
    """
    Converte um produto do banco para formato do carrinho
    """
    return {
        'id': produto.id,
        'nome': produto.nome,
        'preco': float(produto.preco),
        'quantidade': quantidade,
        'imagem_url': produto.imagem_url
    }

# Rota principal - página inicial do e-commerce
@app.route('/')
def index():
    """
    Rota da página inicial que exibe produtos em destaque e categorias
    """
    # Busca produtos em destaque
    produtos_destaque = Produto.query.filter_by(ativo=True, destaque=True).limit(6).all()
    
    # Se não houver produtos em destaque, pega os mais recentes
    if not produtos_destaque:
        produtos_destaque = Produto.query.filter_by(ativo=True).order_by(Produto.data_criacao.desc()).limit(6).all()
    
    # Busca categorias ativas
    categorias = Categoria.query.filter_by(ativa=True).all()
    
    return render_template('index.html', produtos=produtos_destaque, categorias=categorias)

# Rota para exibir produtos por categoria
@app.route('/categoria/<int:categoria_id>')
def produtos_categoria(categoria_id):
    """
    Exibe produtos de uma categoria específica
    """
    categoria = Categoria.query.get_or_404(categoria_id)
    produtos = Produto.query.filter_by(categoria_id=categoria_id, ativo=True).all()
    
    return render_template('categoria.html', categoria=categoria, produtos=produtos)

# Rota para exibir detalhes de um produto específico
@app.route('/produto/<int:produto_id>')
def produto_detalhes(produto_id):
    """
    Exibe os detalhes completos de um produto específico
    """
    produto = Produto.query.get_or_404(produto_id)
    
    if not produto.ativo:
        flash('Produto não disponível!', 'error')
        return redirect(url_for('index'))
    
    # Produtos relacionados da mesma categoria
    produtos_relacionados = Produto.query.filter(
        Produto.categoria_id == produto.categoria_id,
        Produto.id != produto.id,
        Produto.ativo == True
    ).limit(4).all()
    
    return render_template('produto_detalhes.html', produto=produto, produtos_relacionados=produtos_relacionados)

# Rota para adicionar produto ao carrinho
@app.route('/adicionar_carrinho/<int:produto_id>')
def adicionar_carrinho(produto_id):
    """
    Adiciona um produto ao carrinho de compras na sessão
    """
    produto = Produto.query.get_or_404(produto_id)
    
    if not produto.esta_disponivel():
        flash('Produto não disponível!', 'error')
        return redirect(url_for('index'))
    
    # Inicializa carrinho na sessão se não existir
    if 'carrinho' not in session:
        session['carrinho'] = []
    
    # Verifica se produto já está no carrinho
    produto_no_carrinho = False
    for item in session['carrinho']:
        if item['id'] == produto_id:
            # Verifica se há estoque suficiente
            if item['quantidade'] < produto.estoque:
                item['quantidade'] += 1
                produto_no_carrinho = True
                flash(f'Quantidade de {produto.nome} aumentada no carrinho!', 'success')
            else:
                flash(f'Estoque insuficiente para {produto.nome}!', 'error')
                return redirect(url_for('produto_detalhes', produto_id=produto_id))
            break
    
    # Se produto não está no carrinho, adiciona novo item
    if not produto_no_carrinho:
        session['carrinho'].append(produto_para_carrinho(produto))
        flash(f'{produto.nome} adicionado ao carrinho!', 'success')
    
    # Marca sessão como modificada
    session.modified = True
    
    return redirect(url_for('index'))

# Rota para exibir o carrinho de compras
@app.route('/carrinho')
def carrinho():
    """
    Exibe todos os itens no carrinho com total calculado
    """
    carrinho_itens = session.get('carrinho', [])
    total = calcular_total_carrinho()
    
    # Busca configuração de frete grátis
    frete_gratis_valor = Decimal(Configuracao.get_config('frete_gratis_valor', '200.00')
    taxa_frete = Decimal(Configuracao.get_config('taxa_frete', '15.00'))
    
    # Calcula frete
    frete = Decimal('0.00') if total >= frete_gratis_valor else taxa_frete
    total_com_frete = total + frete
    
    return render_template('carrinho.html', 
                         carrinho=carrinho_itens, 
                         total=total,
                         frete=frete,
                         total_com_frete=total_com_frete,
                         frete_gratis_valor=frete_gratis_valor)

# Rota para remover item do carrinho
@app.route('/remover_carrinho/<int:produto_id>')
def remover_carrinho(produto_id):
    """
    Remove completamente um produto do carrinho
    """
    if 'carrinho' in session:
        session['carrinho'] = [item for item in session['carrinho'] if item['id'] != produto_id]
        session.modified = True
        flash('Item removido do carrinho!', 'info')
    
    return redirect(url_for('carrinho'))

# Rota para atualizar quantidade de item no carrinho
@app.route('/atualizar_quantidade/<int:produto_id>/<int:nova_quantidade>')
def atualizar_quantidade(produto_id, nova_quantidade):
    """
    Atualiza a quantidade de um produto específico no carrinho
    """
    if 'carrinho' in session:
        produto = Produto.query.get(produto_id)
        
        for item in session['carrinho']:
            if item['id'] == produto_id:
                if nova_quantidade <= 0:
                    session['carrinho'].remove(item)
                elif nova_quantidade <= produto.estoque:
                    item['quantidade'] = nova_quantidade
                else:
                    flash(f'Estoque insuficiente! Disponível: {produto.estoque}', 'error')
                break
        session.modified = True
    
    return redirect(url_for('carrinho'))

# Rota para página de login
@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Página de login do usuário
    """
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        senha = request.form['senha']
        
        # Busca usuário no banco
        usuario = Usuario.query.filter_by(email=email, ativo=True).first()
        
        if usuario and usuario.verificar_senha(senha):
            # Salva dados do usuário na sessão
            session['usuario_logado'] = usuario.to_dict()
            flash(f'Bem-vindo, {usuario.nome}!', 'success')
            
            # Redireciona para área admin se for administrador
            if usuario.is_admin():
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('index'))
        else:
            flash('Email ou senha incorretos!', 'error')
    
    return render_template('login.html')

# Rota para logout
@app.route('/logout')
def logout():
    """
    Realiza logout do usuário
    """
    if 'usuario_logado' in session:
        session.pop('usuario_logado')
        flash('Logout realizado com sucesso!', 'info')
    
    return redirect(url_for('index'))

# Rota para página de cadastro
@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    """
    Página de cadastro de novos usuários
    """
    if request.method == 'POST':
        nome = request.form['nome'].strip()
        email = request.form['email'].strip().lower()
        senha = request.form['senha']
        telefone = request.form.get('telefone', '').strip()
        
        # Verifica se email já existe
        if Usuario.query.filter_by(email=email).first():
            flash('Email já cadastrado!', 'error')
            return render_template('cadastro.html')
        
        # Cria novo usuário
        novo_usuario = Usuario(nome=nome, email=email, senha=senha, telefone=telefone)
        
        try:
            db.session.add(novo_usuario)
            db.session.commit()
            flash('Cadastro realizado com sucesso! Faça login.', 'success')
            return redirect(url_for('login'))
        except Exception:
            db.session.rollback()
            flash('Erro ao criar cadastro. Tente novamente.', 'error')
    
    return render_template('cadastro.html')

# Rota para finalizar compra
@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    """
    Página de finalização da compra
    """
    if not usuario_logado():
        flash('Faça login para finalizar a compra!', 'error')
        return redirect(url_for('login'))
    
    carrinho_itens = session.get('carrinho', [])
    if not carrinho_itens:
        flash('Carrinho vazio!', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        user = usuario_logado()
        
        # Dados de entrega
        endereco_dados = {
            'logradouro': request.form['logradouro'],
            'numero': request.form['numero'],
            'complemento': request.form.get('complemento', ''),
            'bairro': request.form['bairro'],
            'cidade': request.form['cidade'],
            'estado': request.form['estado'],
            'cep': request.form['cep']
        }
        
        # Calcula totais
        total_produtos = calcular_total_carrinho()
        frete_gratis_valor = Decimal(Configuracao.get_config('frete_gratis_valor', '200.00'))
        taxa_frete = Decimal(Configuracao.get_config('taxa_frete', '15.00'))
        frete = Decimal('0.00') if total_produtos >= frete_gratis_valor else taxa_frete
        total_pedido = total_produtos + frete
        
        try:
            # Cria novo pedido
            novo_pedido = Pedido(
                usuario_id=user.id,
                total=total_pedido,
                endereco_entrega=json.dumps(endereco_dados),
                frete=frete,
                forma_pagamento=request.form.get('forma_pagamento', 'Não informado'),
                observacoes=request.form.get('observacoes', '')
            )
            
            db.session.add(novo_pedido)
            db.session.flush()  # Para obter o ID do pedido
            
            # Adiciona itens do pedido e atualiza estoque
            for item_carrinho in carrinho_itens:
                produto = Produto.query.get(item_carrinho['id'])
                
                # Verifica estoque novamente
                if produto.estoque < item_carrinho['quantidade']:
                    raise Exception(f'Estoque insuficiente para {produto.nome}')
                
                # Cria item do pedido
                item_pedido = ItemPedido(
                    pedido_id=novo_pedido.id,
                    produto_id=produto.id,
                    quantidade=item_carrinho['quantidade'],
                    preco_unitario=produto.preco
                )
                
                # Atualiza estoque
                produto.estoque -= item_carrinho['quantidade']
                
                db.session.add(item_pedido)
            
            db.session.commit()
            
            # Limpa carrinho
            session.pop('carrinho', None)
            session.modified = True
            
            flash('Pedido realizado com sucesso!', 'success')
            return redirect(url_for('pedido_confirmacao', pedido_id=novo_pedido.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao processar pedido: {str(e)}', 'error')
    
    # Calcula totais para exibição
    total = calcular_total_carrinho()
    frete_gratis_valor = Decimal(Configuracao.get_config('frete_gratis_valor', '200.00'))
    taxa_frete = Decimal(Configuracao.get_config('taxa_frete', '15.00'))
    frete = Decimal('0.00') if total >= frete_gratis_valor else taxa_frete
    
    return render_template('checkout.html', 
                         carrinho=carrinho_itens, 
                         total=total,
                         frete=frete,
                         total_com_frete=total + frete)

# Rota para confirmação do pedido
@app.route('/pedido/<int:pedido_id>')
def pedido_confirmacao(pedido_id):
    """
    Exibe confirmação do pedido realizado
    """
    user = usuario_logado()
    if not user:
        flash('Faça login para ver seus pedidos!', 'error')
        return redirect(url_for('login'))
    
    pedido = Pedido.query.filter_by(id=pedido_id, usuario_id=user.id).first_or_404()
    
    # Converte endereço de JSON para dict
    endereco = json.loads(pedido.endereco_entrega)
    
    return render_template('pedido_confirmacao.html', pedido=pedido, endereco=endereco)

# Rota para buscar produtos
@app.route('/buscar')
def buscar():
    """
    Busca produtos por nome, descrição ou categoria
    """
    termo = request.args.get('q', '').strip()
    
    if not termo:
        return redirect(url_for('index'))
    
    # Busca produtos que contenham o termo
    produtos_encontrados = Produto.query.filter(
        Produto.ativo == True,
        db.or_(
            Produto.nome.contains(termo),
            Produto.descricao.contains(termo),
            Produto.categoria_obj.has(Categoria.nome.contains(termo))
        )
    ).all()
    
    return render_template('buscar.html', produtos=produtos_encontrados, termo=termo)

# Rota para área administrativa - Dashboard
@app.route('/admin')
def admin_dashboard():
    """
    Dashboard administrativo
    """
    if not is_admin():
        flash('Acesso negado!', 'error')
        return redirect(url_for('index'))
    
    # Estatísticas básicas
    total_usuarios = Usuario.query.filter_by(tipo_usuario='cliente').count()
    total_produtos = Produto.query.filter_by(ativo=True).count()
    total_pedidos = Pedido.query.count()
    
    # Produtos com estoque baixo
    produtos_estoque_baixo = Produto.query.filter(
        Produto.ativo == True,
        Produto.estoque <= Produto.estoque_minimo
    ).all()
    
    # Pedidos recentes
    pedidos_recentes = Pedido.query.order_by(Pedido.data_pedido.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html',
                         total_usuarios=total_usuarios,
                         total_produtos=total_produtos,
                         total_pedidos=total_pedidos,
                         produtos_estoque_baixo=produtos_estoque_baixo,
                         pedidos_recentes=pedidos_recentes)

# Rota para gerenciar produtos (admin)
@app.route('/admin/produtos')
def admin_produtos():
    """
    Lista de produtos para administração
    """
    if not is_admin():
        flash('Acesso negado!', 'error')
        return redirect(url_for('index'))
    
    produtos = Produto.query.all()
    return render_template('admin/produtos.html', produtos=produtos)

# Rota para gerenciar usuários (admin)
@app.route('/admin/usuarios')
def admin_usuarios():
    """
    Lista de usuários para administração
    """
    if not is_admin():
        flash('Acesso negado!', 'error')
        return redirect(url_for('index'))
    
    usuarios = Usuario.query.filter_by(tipo_usuario='cliente').all()
    return render_template('admin/usuarios.html', usuarios=usuarios)

# Ponto de entrada da aplicação
if __name__ == '__main__':
    # Executa o servidor Flask
    app.run(host='0.0.0.0', port=5000, debug=True)
