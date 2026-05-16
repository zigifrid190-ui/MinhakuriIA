import sqlite3
import json
from typing import Any, List, Dict
from config import KURI_DB, MAX_MEMORY_MESSAGES

class MemoryManager:
    def __init__(self, db_path=KURI_DB):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Inicializa as tabelas do banco de dados se não existirem."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Tabela de Histórico de Conversas
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS historico (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabela de Perfil do Usuário (Chave-Valor)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS perfil (
                    chave TEXT PRIMARY KEY,
                    valor TEXT
                )
            ''')
            
            # Tabela de Fatos Aprendidos
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS fatos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fato TEXT UNIQUE,
                    importancia INTEGER DEFAULT 1,
                    data_aprendizado DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabela de Resumos de Sessão
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS resumos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    resumo TEXT,
                    data_fim DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()

    # --- Histórico ---
    def carregar_historico(self, limit=MAX_MEMORY_MESSAGES) -> List[Dict[str, str]]:
        """Carrega as últimas mensagens do histórico."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT role, content FROM historico ORDER BY timestamp DESC LIMIT ?",
                    (limit,)
                )
                rows = cursor.fetchall()
                # Retorna em ordem cronológica (mais antiga primeiro)
                return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]
        except Exception as e:
            print(f"[ERRO] carregar_historico: {e}")
            return []

    def adicionar_interacao(self, user_msg: str, assistant_msg: str):
        """Salva uma nova interação no banco."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO historico (role, content) VALUES (?, ?)", ("user", user_msg))
                cursor.execute("INSERT INTO historico (role, content) VALUES (?, ?)", ("assistant", assistant_msg))
                conn.commit()
        except Exception as e:
            print(f"[ERRO] adicionar_interacao: {e}")

    # --- Perfil ---
    def carregar_perfil(self) -> Dict[str, Any]:
        """Carrega todo o perfil do usuário."""
        perfil = {
            "nome_usuario": "",
            "apelidos": [],
            "humor_atual": "neutra",
            "fatos_aprendidos": []
        }
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT chave, valor FROM perfil")
                for chave, valor in cursor.fetchall():
                    if chave == "apelidos":
                        perfil[chave] = json.loads(valor)
                    else:
                        perfil[chave] = valor
                
                # Busca fatos da tabela separada
                cursor.execute("SELECT fato FROM fatos")
                perfil["fatos_aprendidos"] = [row[0] for row in cursor.fetchall()]
        except Exception as e:
            print(f"[ERRO] carregar_perfil: {e}")
        return perfil

    def atualizar_perfil(self, chave: str, valor: Any):
        """Atualiza ou insere um campo no perfil."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                if isinstance(valor, (list, dict)):
                    valor_str = json.dumps(valor, ensure_ascii=False)
                else:
                    valor_str = str(valor)
                
                cursor.execute(
                    "INSERT OR REPLACE INTO perfil (chave, valor) VALUES (?, ?)",
                    (chave, valor_str)
                )
                conn.commit()
        except Exception as e:
            print(f"[ERRO] atualizar_perfil: {e}")

    def adicionar_fato(self, fato: str):
        """Adiciona um fato aprendido sobre o usuário."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT OR IGNORE INTO fatos (fato) VALUES (?)", (fato,))
                conn.commit()
        except Exception as e:
            print(f"[ERRO] adicionar_fato: {e}")

    def buscar_fatos_relevantes(self, query: str, limit: int = 5) -> List[str]:
        """Busca fatos relevantes baseados em palavras-chave da mensagem do usuário."""
        # Limpa pontuações básicas e divide em palavras menores que 3 caracteres
        import re
        query_limpa = re.sub(r'[^\w\s]', '', query.lower())
        keywords = [kw for kw in query_limpa.split() if len(kw) > 2]
        
        if not keywords:
            # Se não tem keyword relevante, busca os mais recentes
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT fato FROM fatos ORDER BY data_aprendizado DESC LIMIT ?", (limit,))
                    return [row[0] for row in cursor.fetchall()]
            except Exception as e:
                print(f"[ERRO] buscar_fatos_relevantes (fallback): {e}")
                return []
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # Cria a query LIKE para cada keyword
                conditions = " OR ".join(["LOWER(fato) LIKE ?" for _ in keywords])
                params = [f"%{kw}%" for kw in keywords]
                
                cursor.execute(
                    f"SELECT fato FROM fatos WHERE {conditions} ORDER BY importancia DESC, data_aprendizado DESC LIMIT ?",
                    params + [limit]
                )
                fatos = [row[0] for row in cursor.fetchall()]
                
                # Se não encontrou nada relevante, faz o fallback para os recentes
                if not fatos:
                    cursor.execute("SELECT fato FROM fatos ORDER BY data_aprendizado DESC LIMIT ?", (limit,))
                    fatos = [row[0] for row in cursor.fetchall()]
                    
                return fatos
        except Exception as e:
            print(f"[ERRO] buscar_fatos_relevantes: {e}")
            return []

    # --- Resumos ---
    def salvar_resumo(self, resumo: str):
        """Salva um resumo de conversa."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO resumos (resumo) VALUES (?)", (resumo,))
                conn.commit()
        except Exception as e:
            print(f"[ERRO] salvar_resumo: {e}")

    def carregar_resumos_recentes(self, limit=3) -> str:
        """Busca os resumos mais recentes e os concatena."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT resumo FROM resumos ORDER BY data_fim DESC LIMIT ?", (limit,))
                rows = cursor.fetchall()
                # Junta do mais antigo para o mais novo
                resumos = [row[0] for row in reversed(rows)]
                return "\n---\n".join(resumos) if resumos else ""
        except Exception as e:
            print(f"[ERRO] carregar_resumos_recentes: {e}")
            return ""

# Instância única para uso global
memory = MemoryManager()

# Funções de conveniência para manter compatibilidade onde possível
def carregar_historico(): return memory.carregar_historico()
def adicionar_interacao(historico: list, user_msg: str, assistant_msg: str):
    memory.adicionar_interacao(user_msg, assistant_msg)
    return memory.carregar_historico()
def carregar_ultimo_resumo(): return memory.carregar_resumos_recentes()
def salvar_resumo(resumo: str): memory.salvar_resumo(resumo)
def carregar_perfil(): return memory.carregar_perfil()
def atualizar_perfil(campo: str, valor: Any): memory.atualizar_perfil(campo, valor)
def adicionar_fato(fato: str): memory.adicionar_fato(fato)
def buscar_fatos_relevantes(query: str, limit: int = 5): return memory.buscar_fatos_relevantes(query, limit)
