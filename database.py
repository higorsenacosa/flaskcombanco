
# Configuração do banco de dados SQLite e modelos
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# Instância do SQLAlchemy
db = SQLAlchemy()

# Modelo de Usuário
class Usuario(db.Model):
    """
    Modelo para representar usuários do sistema
    Inclui clientes e administradores
    """
    __tablename__ = 'usuarios'
    
    # Campos da tabela
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha_hash = db.Column(db.String(255), nullable=False)
    telefone = db.Column(db.String(20), nullable=True)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    ativo = db.Column(db.Boolean, default=True)
    
    # Tipo de usuário: 'cliente' ou 'admin'
    tipo_usuario = db.Column(db.String(20), default='cliente')
    
    # Relacionamentos
    enderecos = db.relationship('Endereco', backref='usuario', lazy=True, cascade='all, delete-orphan')
    pedidos = db.relationship('Pedido', backref='usuario', lazy=True)
    
    def __init__(self, nome, email, senha, telefone=None, tipo_usuario='cliente'):
        """
        Construtor do usuário
        Automaticamente gera hash da senha
        """
        self.nome = nome
        self.email = email
        self.senha_hash = generate_password_hash(senha)
        self.telefone = telefone
        self.tipo_usuario = tipo_usuario
    
    def verificar_senha(self, senha):
        """
        Verifica se a senha fornecida está correta
        """
        return check_password_hash(self.senha_hash, senha)
    
    def alterar_senha(self, nova_senha):
        """
        Altera a senha do usuário
        """
        self.senha_hash = generate_password_hash(nova_senha)
    
    def is_admin(self):
        """
        Verifica se o usuário é administrador
        """
        return self.tipo_usuario == 'admin'
    
    def to_dict(self):
        """
        Converte o usuário para dicionário (para sessão)
        """
        return {
            'id': self.id,
            'nome': self.nome,
            'email': self.email,
            'tipo_usuario': self.tipo_usuario
        }

# Modelo de Endereço
class Endereco(db.Model):
    """
    Modelo para representar endereços dos usuários
    Um usuário pode ter múltiplos endereços
    """
    __tablename__ = 'enderecos'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    
    # Dados do endereço
    logradouro = db.Column(db.String(200), nullable=False)
    numero = db.Column(db.String(10), nullable=False)
    complemento = db.Column(db.String(100), nullable=True)
    bairro = db.Column(db.String(100), nullable=False)
    cidade = db.Column(db.String(100), nullable=False)
    estado = db.Column(db.String(2), nullable=False)
    cep = db.Column(db.String(10), nullable=False)
    
    # Tipo de endereço: 'residencial', 'comercial', 'entrega'
    tipo = db.Column(db.String(20), default='residencial')
    
    # Endereço principal
    principal = db.Column(db.Boolean, default=False)
    
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)

# Modelo de Categoria
class Categoria(db.Model):
    """
    Modelo para representar categorias de produtos
    """
    __tablename__ = 'categorias'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), unique=True, nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    ativa = db.Column(db.Boolean, default=True)
    
    # Relacionamento
    produtos = db.relationship('Produto', backref='categoria_obj', lazy=True)

# Modelo de Produto
class Produto(db.Model):
    """
    Modelo para representar produtos do e-commerce
    """
    __tablename__ = 'produtos'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    preco = db.Column(db.Decimal(10, 2), nullable=False)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categorias.id'), nullable=True)
    imagem_url = db.Column(db.String(255), nullable=True)
    
    # Controle de estoque
    estoque = db.Column(db.Integer, default=0)
    estoque_minimo = db.Column(db.Integer, default=5)
    
    # Status do produto
    ativo = db.Column(db.Boolean, default=True)
    destaque = db.Column(db.Boolean, default=False)
    
    # Dados administrativos
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    data_atualizacao = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamento
    itens_pedido = db.relationship('ItemPedido', backref='produto', lazy=True)
    
    def esta_disponivel(self):
        """
        Verifica se o produto está disponível para venda
        """
        return self.ativo and self.estoque > 0
    
    def precisa_reposicao(self):
        """
        Verifica se o produto precisa de reposição de estoque
        """
        return self.estoque <= self.estoque_minimo

# Modelo de Pedido
class Pedido(db.Model):
    """
    Modelo para representar pedidos de compra
    """
    __tablename__ = 'pedidos'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    
    # Dados do pedido
    data_pedido = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pendente')  # pendente, processando, enviado, entregue, cancelado
    total = db.Column(db.Decimal(10, 2), nullable=False)
    
    # Dados de entrega
    endereco_entrega = db.Column(db.Text, nullable=False)  # JSON com dados do endereço
    frete = db.Column(db.Decimal(10, 2), default=0.00)
    
    # Dados de pagamento
    forma_pagamento = db.Column(db.String(50), nullable=True)
    data_pagamento = db.Column(db.DateTime, nullable=True)
    
    # Observações
    observacoes = db.Column(db.Text, nullable=True)
    
    # Relacionamento
    itens = db.relationship('ItemPedido', backref='pedido', lazy=True, cascade='all, delete-orphan')
    
    def calcular_total(self):
        """
        Calcula o total do pedido baseado nos itens
        """
        total_itens = sum(item.subtotal() for item in self.itens)
        return total_itens + self.frete

# Modelo de Item do Pedido
class ItemPedido(db.Model):
    """
    Modelo para representar itens individuais de um pedido
    """
    __tablename__ = 'itens_pedido'
    
    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedidos.id'), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey('produtos.id'), nullable=False)
    
    # Dados do item no momento da compra
    quantidade = db.Column(db.Integer, nullable=False)
    preco_unitario = db.Column(db.Decimal(10, 2), nullable=False)  # Preço no momento da compra
    
    def subtotal(self):
        """
        Calcula o subtotal do item (quantidade × preço unitário)
        """
        return self.quantidade * self.preco_unitario

# Modelo de Configuração do Sistema
class Configuracao(db.Model):
    """
    Modelo para armazenar configurações do sistema
    """
    __tablename__ = 'configuracoes'
    
    id = db.Column(db.Integer, primary_key=True)
    chave = db.Column(db.String(50), unique=True, nullable=False)
    valor = db.Column(db.Text, nullable=True)
    descricao = db.Column(db.String(200), nullable=True)
    
    @staticmethod
    def get_config(chave, default=None):
        """
        Busca uma configuração pela chave
        """
        config = Configuracao.query.filter_by(chave=chave).first()
        return config.valor if config else default
    
    @staticmethod
    def set_config(chave, valor, descricao=None):
        """
        Define uma configuração
        """
        config = Configuracao.query.filter_by(chave=chave).first()
        if config:
            config.valor = valor
            if descricao:
                config.descricao = descricao
        else:
            config = Configuracao(chave=chave, valor=valor, descricao=descricao)
            db.session.add(config)
        db.session.commit()

def init_database(app):
    """
    Inicializa o banco de dados e cria as tabelas
    """
    with app.app_context():
        # Cria todas as tabelas
        db.create_all()
        
        # Verifica se já existe um administrador
        admin_existente = Usuario.query.filter_by(tipo_usuario='admin').first()
        if not admin_existente:
            # Cria usuário administrador padrão
            admin = Usuario(
                nome='Administrador',
                email='admin@minhaloja.com',
                senha='admin123',
                tipo_usuario='admin'
            )
            db.session.add(admin)
        
        # Cria categorias padrão se não existirem
        if not Categoria.query.first():
            categorias_padrao = [
                Categoria(nome='Eletrônicos', descricao='Smartphones, notebooks, tablets'),
                Categoria(nome='Roupas', descricao='Vestuário masculino e feminino'),
                Categoria(nome='Esportes', descricao='Artigos esportivos e fitness'),
                Categoria(nome='Livros', descricao='Livros e material educativo'),
                Categoria(nome='Casa', descricao='Itens para casa e decoração')
            ]
            
            for categoria in categorias_padrao:
                db.session.add(categoria)
        
        # Cria produtos padrão se não existirem
        if not Produto.query.first():
            # Busca categorias para associar aos produtos
            cat_eletronicos = Categoria.query.filter_by(nome='Eletrônicos').first()
            cat_roupas = Categoria.query.filter_by(nome='Roupas').first()
            cat_esportes = Categoria.query.filter_by(nome='Esportes').first()
            cat_livros = Categoria.query.filter_by(nome='Livros').first()
            
            produtos_padrao = [
                Produto(
                    nome='Smartphone Samsung Galaxy',
                    descricao='Smartphone com tela de 6.5 polegadas, 128GB de armazenamento',
                    preco=1299.99,
                    categoria_id=cat_eletronicos.id if cat_eletronicos else None,
                    imagem_url='https://via.placeholder.com/300x200?text=Smartphone',
                    estoque=25,
                    destaque=True
                ),
                Produto(
                    nome='Notebook Dell Inspiron',
                    descricao='Notebook com processador Intel i5, 8GB RAM, SSD 256GB',
                    preco=2499.99,
                    categoria_id=cat_eletronicos.id if cat_eletronicos else None,
                    imagem_url='https://via.placeholder.com/300x200?text=Notebook',
                    estoque=15
                ),
                Produto(
                    nome='Tênis Nike Air Max',
                    descricao='Tênis esportivo confortável para corrida e caminhada',
                    preco=399.99,
                    categoria_id=cat_esportes.id if cat_esportes else None,
                    imagem_url='https://via.placeholder.com/300x200?text=Tênis',
                    estoque=50,
                    destaque=True
                ),
                Produto(
                    nome='Camiseta Polo',
                    descricao='Camiseta polo 100% algodão, disponível em várias cores',
                    preco=89.99,
                    categoria_id=cat_roupas.id if cat_roupas else None,
                    imagem_url='https://via.placeholder.com/300x200?text=Camiseta',
                    estoque=100
                ),
                Produto(
                    nome='Livro Python para Iniciantes',
                    descricao='Guia completo para aprender programação Python',
                    preco=59.99,
                    categoria_id=cat_livros.id if cat_livros else None,
                    imagem_url='https://via.placeholder.com/300x200?text=Livro',
                    estoque=30
                ),
                Produto(
                    nome='Fone de Ouvido Bluetooth',
                    descricao='Fone sem fio com cancelamento de ruído',
                    preco=199.99,
                    categoria_id=cat_eletronicos.id if cat_eletronicos else None,
                    imagem_url='https://via.placeholder.com/300x200?text=Fone',
                    estoque=40,
                    destaque=True
                )
            ]
            
            for produto in produtos_padrao:
                db.session.add(produto)
        
        # Cria configurações padrão
        configs_padrao = [
            ('nome_loja', 'MinheLoja', 'Nome da loja'),
            ('email_contato', 'contato@minhaloja.com', 'Email de contato'),
            ('frete_gratis_valor', '200.00', 'Valor mínimo para frete grátis'),
            ('taxa_frete', '15.00', 'Taxa padrão de frete')
        ]
        
        for chave, valor, descricao in configs_padrao:
            if not Configuracao.query.filter_by(chave=chave).first():
                config = Configuracao(chave=chave, valor=valor, descricao=descricao)
                db.session.add(config)
        
        # Salva todas as alterações
        db.session.commit()
        
        print("Banco de dados inicializado com sucesso!")
        print("Usuário admin criado: admin@minhaloja.com / admin123")
