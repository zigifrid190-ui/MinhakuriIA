import sqlite3
import json
from typing import Any, List, Dict
from config import KURI_DB, MAX_MEMORY_MESSAGES
from logger import get_logger

log = get_logger("memory")


class MemoryManager:
    def __init__(self, db_path=KURI_DB):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Inicializa as tabelas do banco de dados se não existirem."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Tabela de Histórico de Conversas
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS historico (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Tabela de Perfil do Usuário (Chave-Valor)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS perfil (
                    chave TEXT PRIMARY KEY,
                    valor TEXT
                )
            """)

            # Tabela de Fatos Aprendidos
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fatos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fato TEXT UNIQUE,
                    importancia INTEGER DEFAULT 1,
                    data_aprendizado DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Tabela de Resumos de Sessão
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS resumos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    resumo TEXT,
                    data_fim DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Tabela de Tarefas (To-Do List)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    titulo TEXT NOT NULL,
                    status TEXT DEFAULT 'pending', -- pending, done
                    prioridade INTEGER DEFAULT 1,  -- 1 (baixa), 2 (media), 3 (alta)
                    due_date DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Tabela de Insights (Aprendizado Contínuo)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS insights (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tipo TEXT NOT NULL,         -- preferencia, habito, estilo, assunto
                    conteudo TEXT NOT NULL,
                    confianca REAL DEFAULT 0.5, -- 0.0 a 1.0
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(tipo, conteudo)
                )
            """)

            # Tabela de Histórico de Ações Executadas (Hooks)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS historico_acoes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome_acao TEXT NOT NULL,
                    argumentos TEXT,
                    resultado TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Kurês — gírias da Kuri (Movimento 2.1)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS girias (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    giria TEXT NOT NULL UNIQUE,
                    sentido TEXT,
                    origem TEXT DEFAULT 'kuri',
                    ativa INTEGER DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Identidade viva — cláusulas que a Kuri incorpora (Movimento 2.2)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS identidade (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    clausula TEXT NOT NULL UNIQUE,
                    origem TEXT DEFAULT 'usuario',
                    ativa INTEGER DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
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
                    (limit,),
                )
                rows = cursor.fetchall()
                # Retorna em ordem cronológica (mais antiga primeiro)
                return [
                    {"role": r["role"], "content": r["content"]} for r in reversed(rows)
                ]
        except Exception as e:
            log.error(f"carregar_historico: {e}")
            return []

    def adicionar_interacao(self, user_msg: str, assistant_msg: str):
        """Salva uma nova interação no banco."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO historico (role, content) VALUES (?, ?)",
                    ("user", user_msg),
                )
                cursor.execute(
                    "INSERT INTO historico (role, content) VALUES (?, ?)",
                    ("assistant", assistant_msg),
                )
                conn.commit()
        except Exception as e:
            log.error(f"adicionar_interacao: {e}")

    # --- Perfil ---
    def carregar_perfil(self) -> Dict[str, Any]:
        """Carrega todo o perfil do usuário."""
        perfil = {
            "nome_usuario": "",
            "apelidos": [],
            "humor_atual": "neutra",
            "fatos_aprendidos": [],
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
            log.error(f"carregar_perfil: {e}")
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
                    (chave, valor_str),
                )
                conn.commit()
        except Exception as e:
            log.error(f"atualizar_perfil: {e}")

    def adicionar_fato(self, fato: str):
        """Adiciona um fato aprendido sobre o usuário."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT OR IGNORE INTO fatos (fato) VALUES (?)", (fato,))
                conn.commit()
        except Exception as e:
            log.error(f"adicionar_fato: {e}")

    def buscar_fatos_relevantes(self, query: str, limit: int = 5) -> List[str]:
        """Busca fatos relevantes baseados em palavras-chave da mensagem do usuário."""
        import re

        query_limpa = re.sub(r"[^\w\s]", "", query.lower())
        keywords = [kw for kw in query_limpa.split() if len(kw) > 2]

        if not keywords:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT fato FROM fatos ORDER BY data_aprendizado DESC LIMIT ?",
                        (limit,),
                    )
                    return [row[0] for row in cursor.fetchall()]
            except Exception as e:
                log.error(f"buscar_fatos_relevantes (fallback): {e}")
                return []

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # Cria a query LIKE para cada keyword
                conditions = " OR ".join(["LOWER(fato) LIKE ?" for _ in keywords])
                params = [f"%{kw}%" for kw in keywords]

                cursor.execute(
                    f"SELECT fato FROM fatos WHERE {conditions} ORDER BY importancia DESC, data_aprendizado DESC LIMIT ?",
                    params + [limit],
                )
                fatos = [row[0] for row in cursor.fetchall()]

                # Se não encontrou nada relevante, faz o fallback para os recentes
                if not fatos:
                    cursor.execute(
                        "SELECT fato FROM fatos ORDER BY data_aprendizado DESC LIMIT ?",
                        (limit,),
                    )
                    fatos = [row[0] for row in cursor.fetchall()]

                return fatos
        except Exception as e:
            log.error(f"buscar_fatos_relevantes: {e}")
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
            log.error(f"salvar_resumo: {e}")

    def carregar_resumos_recentes(self, limit=3) -> str:
        """Busca os resumos mais recentes e os concatena."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT resumo FROM resumos ORDER BY data_fim DESC LIMIT ?",
                    (limit,),
                )
                rows = cursor.fetchall()
                # Junta do mais antigo para o mais novo
                resumos = [row[0] for row in reversed(rows)]
                return "\n---\n".join(resumos) if resumos else ""
        except Exception as e:
            log.error(f"carregar_resumos_recentes: {e}")
            return ""

    # --- Tarefas (To-Do) ---
    def adicionar_tarefa(self, titulo: str, prioridade: int = 1, due_date: str = None):
        """Adiciona uma nova tarefa à lista."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO tasks (titulo, prioridade, due_date) VALUES (?, ?, ?)",
                    (titulo, prioridade, due_date),
                )
                conn.commit()
                return True
        except Exception as e:
            log.error(f"adicionar_tarefa: {e}")
            return False

    def listar_tarefas(self, apenas_pendentes: bool = True) -> List[Dict[str, Any]]:
        """Retorna a lista de tarefas."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                if apenas_pendentes:
                    cursor.execute(
                        "SELECT * FROM tasks WHERE status = 'pending' ORDER BY prioridade DESC, created_at ASC"
                    )
                else:
                    cursor.execute("SELECT * FROM tasks ORDER BY created_at DESC")

                rows = cursor.fetchall()
                return [dict(r) for r in rows]
        except Exception as e:
            log.error(f"listar_tarefas: {e}")
            return []

    def concluir_tarefa(self, task_id: int):
        """Marca uma tarefa como concluída."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE tasks SET status = 'done' WHERE id = ?", (task_id,)
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            log.error(f"concluir_tarefa: {e}")
            return False

    def remover_tarefa(self, task_id: int):
        """Remove uma tarefa definitivamente."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            log.error(f"remover_tarefa: {e}")
            return False

    # --- Insights (Aprendizado Contínuo) ---
    def adicionar_insight(self, tipo: str, conteudo: str, confianca: float = 0.5):
        """Salva um insight comportamental sobre o usuário.

        Args:
            tipo: preferencia | habito | estilo | assunto
            conteudo: descrição do insight
            confianca: 0.0 a 1.0 (quão certa a Kuri está)
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR REPLACE INTO insights (tipo, conteudo, confianca) VALUES (?, ?, ?)",
                    (tipo, conteudo, confianca),
                )
                conn.commit()
                return True
        except Exception as e:
            log.error(f"adicionar_insight: {e}")
            return False

    def buscar_insights(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retorna os insights mais confiáveis para uso no system prompt."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT tipo, conteudo, confianca FROM insights ORDER BY confianca DESC, created_at DESC LIMIT ?",
                    (limit,),
                )
                return [dict(r) for r in cursor.fetchall()]
        except Exception as e:
            log.error(f"buscar_insights: {e}")
            return []

    def listar_insights(self, tipo: str = None) -> List[Dict[str, Any]]:
        """Lista insights filtrados por tipo (ou todos)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                if tipo:
                    cursor.execute(
                        "SELECT * FROM insights WHERE tipo = ? ORDER BY created_at DESC",
                        (tipo,),
                    )
                else:
                    cursor.execute("SELECT * FROM insights ORDER BY created_at DESC")
                return [dict(r) for r in cursor.fetchall()]
        except Exception as e:
            log.error(f"listar_insights: {e}")
            return []

    # --- Histórico de Ações (Hooks) ---
    def adicionar_historico_acao(self, nome_acao: str, argumentos: Any, resultado: str) -> bool:
        """Salva a execução de uma ferramenta (action) e seu resultado no banco."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                args_str = json.dumps(argumentos, ensure_ascii=False) if argumentos else "{}"
                cursor.execute(
                    "INSERT INTO historico_acoes (nome_acao, argumentos, resultado) VALUES (?, ?, ?)",
                    (nome_acao, args_str, str(resultado)),
                )
                conn.commit()
                return True
        except Exception as e:
            log.error(f"adicionar_historico_acao: {e}")
            return False

    # --- Kurês ---
    def adicionar_giria(self, giria: str, sentido: str = "", origem: str = "kuri") -> bool:
        """Persiste uma gíria da Kuri. Duplicata reativa e atualiza o sentido."""
        giria = (giria or "").strip()
        if not giria:
            return False
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO girias (giria, sentido, origem, ativa)
                    VALUES (?, ?, ?, 1)
                    ON CONFLICT(giria) DO UPDATE SET
                        sentido = excluded.sentido,
                        origem = excluded.origem,
                        ativa = 1
                    """,
                    (giria, (sentido or "").strip(), origem),
                )
                conn.commit()
            try:
                from prompt_builder import invalidate_prompt_cache
                invalidate_prompt_cache()
            except Exception:
                pass
            return True
        except Exception as e:
            log.error(f"adicionar_giria: {e}")
            return False

    def listar_girias(self, apenas_ativas: bool = True, limit: int = 40) -> List[Dict[str, Any]]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                if apenas_ativas:
                    cursor.execute(
                        "SELECT giria, sentido, origem FROM girias WHERE ativa = 1 ORDER BY created_at DESC LIMIT ?",
                        (limit,),
                    )
                else:
                    cursor.execute(
                        "SELECT giria, sentido, origem, ativa FROM girias ORDER BY created_at DESC LIMIT ?",
                        (limit,),
                    )
                return [dict(r) for r in cursor.fetchall()]
        except Exception as e:
            log.error(f"listar_girias: {e}")
            return []

    def desativar_giria(self, giria: str) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE girias SET ativa = 0 WHERE giria = ?", (giria.strip(),))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            log.error(f"desativar_giria: {e}")
            return False

    def adicionar_clausula_identidade(self, clausula: str, origem: str = "usuario") -> bool:
        """Anexa um traço permanente. Não reescreve o prompt_kuri.txt."""
        clausula = " ".join((clausula or "").strip().split())
        if not clausula:
            return False
        if len(clausula) > 160:
            clausula = clausula[:157] + "..."
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO identidade (clausula, origem, ativa)
                    VALUES (?, ?, 1)
                    ON CONFLICT(clausula) DO UPDATE SET
                        origem = excluded.origem,
                        ativa = 1
                    """,
                    (clausula, origem),
                )
                conn.commit()
            try:
                from prompt_builder import invalidate_prompt_cache
                invalidate_prompt_cache()
            except Exception:
                pass
            return True
        except Exception as e:
            log.error(f"adicionar_clausula_identidade: {e}")
            return False

    def listar_identidade(self, apenas_ativas: bool = True, limit: int = 12) -> List[Dict[str, Any]]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                if apenas_ativas:
                    cursor.execute(
                        "SELECT clausula, origem FROM identidade WHERE ativa = 1 ORDER BY created_at DESC LIMIT ?",
                        (limit,),
                    )
                else:
                    cursor.execute(
                        "SELECT clausula, origem, ativa FROM identidade ORDER BY created_at DESC LIMIT ?",
                        (limit,),
                    )
                return [dict(r) for r in cursor.fetchall()]
        except Exception as e:
            log.error(f"listar_identidade: {e}")
            return []

    def desativar_clausula_identidade(self, clausula: str) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE identidade SET ativa = 0 WHERE clausula = ?",
                    (clausula.strip(),),
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            log.error(f"desativar_clausula_identidade: {e}")
            return False


# Instância única para uso global
memory = MemoryManager()


# Funções de conveniência para manter compatibilidade onde possível
def carregar_historico():
    return memory.carregar_historico()


# --- Fase 4: Estratégia clara de memória (aprofundada) ---
def aplicar_estrategia_memoria():
    """Aplica estratégia de polimento da memória:
    - Prune histórico antigo (mantém recentes + fatos/resumos protegidos)
    - Mantém fatos priorizados e resumos
    - Limpa ações antigas
    """
    try:
        with sqlite3.connect(memory.db_path) as conn:
            cursor = conn.cursor()

            # Protege fatos e resumos: nunca deleta linhas que são referenciadas por fatos ou resumos
            # Prune histórico: mantém os mais recentes + todos os que têm fatos associados indiretamente via perfil/historico
            cursor.execute(f"""
                DELETE FROM historico 
                WHERE id NOT IN (
                    SELECT id FROM historico 
                    ORDER BY timestamp DESC 
                    LIMIT {MAX_MEMORY_MESSAGES * 2}
                )
            """)

            # Limpa ações muito antigas (mantém últimas 150 para auditoria)
            cursor.execute("""
                DELETE FROM historico_acoes 
                WHERE id NOT IN (
                    SELECT id FROM historico_acoes 
                    ORDER BY timestamp DESC 
                    LIMIT 150
                )
            """)

            # Opcional: compacta fatos muito antigos de baixa importância (mantém os importantes)
            cursor.execute("""
                DELETE FROM fatos 
                WHERE importancia < 2 
                  AND id NOT IN (
                      SELECT id FROM fatos 
                      ORDER BY importancia DESC, timestamp DESC 
                      LIMIT 50
                  )
            """)

            conn.commit()
            log.info("Estratégia de memória aplicada: prune + proteção de fatos/resumos")
    except Exception as e:
        log.error(f"aplicar_estrategia_memoria: {e}")


def salvar_fato_usuario(fato: str, importancia: int = 1):
    """Wrapper para adicionar fato com estratégia."""
    memory.adicionar_fato(fato)
    # Opcional: ajustar importancia
    try:
        with sqlite3.connect(memory.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE fatos SET importancia = ? WHERE fato = ?",
                (importancia, fato)
            )
            conn.commit()
    except Exception:
        pass


def adicionar_interacao(historico: list, user_msg: str, assistant_msg: str):
    memory.adicionar_interacao(user_msg, assistant_msg)
    return memory.carregar_historico()


def carregar_ultimo_resumo():
    return memory.carregar_resumos_recentes()


def salvar_resumo(resumo: str):
    memory.salvar_resumo(resumo)


def carregar_perfil():
    return memory.carregar_perfil()


def atualizar_perfil(campo: str, valor: Any):
    memory.atualizar_perfil(campo, valor)


def adicionar_fato(fato: str):
    memory.adicionar_fato(fato)


def buscar_fatos_relevantes(query: str, limit: int = 5):
    return memory.buscar_fatos_relevantes(query, limit)


# Funções de Tarefas
def adicionar_tarefa(titulo: str, prioridade: int = 1, due_date: str = None):
    return memory.adicionar_tarefa(titulo, prioridade, due_date)


def listar_tarefas(apenas_pendentes: bool = True):
    return memory.listar_tarefas(apenas_pendentes)


def concluir_tarefa(task_id: int):
    return memory.concluir_tarefa(task_id)


def remover_tarefa(task_id: int):
    return memory.remover_tarefa(task_id)


# Funções de Insights
def adicionar_insight(tipo: str, conteudo: str, confianca: float = 0.5):
    return memory.adicionar_insight(tipo, conteudo, confianca)


def buscar_insights(limit: int = 10):
    return memory.buscar_insights(limit)


def adicionar_giria(giria: str, sentido: str = "", origem: str = "kuri"):
    return memory.adicionar_giria(giria, sentido, origem)


def listar_girias(apenas_ativas: bool = True, limit: int = 40):
    return memory.listar_girias(apenas_ativas, limit)


def desativar_giria(giria: str):
    return memory.desativar_giria(giria)


def adicionar_clausula_identidade(clausula: str, origem: str = "usuario"):
    return memory.adicionar_clausula_identidade(clausula, origem)


def listar_identidade(apenas_ativas: bool = True, limit: int = 12):
    return memory.listar_identidade(apenas_ativas, limit)


def desativar_clausula_identidade(clausula: str):
    return memory.desativar_clausula_identidade(clausula)


def listar_insights(tipo: str = None):
    return memory.listar_insights(tipo)


def adicionar_historico_acao(nome_acao: str, argumentos: Any, resultado: str):
    return memory.adicionar_historico_acao(nome_acao, argumentos, resultado)
