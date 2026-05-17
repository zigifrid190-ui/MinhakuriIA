"""
test_memory.py — Testes unitários para o sistema de memória da Kuri.
Usa um banco de dados temporário em memória para isolamento total.
"""

import unittest
import os
import tempfile
from unittest.mock import patch


class TestMemoryManager(unittest.TestCase):
    """Testes para o MemoryManager com banco temporário."""

    def setUp(self):
        """Cria um banco de dados temporário para cada teste."""
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.tmp.name
        self.tmp.close()

        # Importa e instancia com banco temporário
        from memory import MemoryManager

        self.mm = MemoryManager(db_path=self.db_path)

    def tearDown(self):
        """Remove o banco temporário."""
        try:
            os.unlink(self.db_path)
        except OSError:
            pass

    # --- Histórico ---
    def test_historico_vazio(self):
        result = self.mm.carregar_historico()
        self.assertEqual(result, [])

    def test_adicionar_e_carregar_interacao(self):
        self.mm.adicionar_interacao("Olá Kuri!", "Fala velho!")
        historico = self.mm.carregar_historico()
        self.assertEqual(len(historico), 2)
        roles = [h["role"] for h in historico]
        contents = [h["content"] for h in historico]
        self.assertIn("user", roles)
        self.assertIn("assistant", roles)
        self.assertIn("Olá Kuri!", contents)
        self.assertIn("Fala velho!", contents)

    def test_historico_respeita_limite(self):
        for i in range(30):
            self.mm.adicionar_interacao(f"msg_{i}", f"resp_{i}")
        # Deve ter no máximo MAX_MEMORY_MESSAGES (50) entradas
        historico = self.mm.carregar_historico(limit=10)
        self.assertLessEqual(len(historico), 10)

    # --- Perfil ---
    def test_perfil_padrao(self):
        perfil = self.mm.carregar_perfil()
        self.assertEqual(perfil["nome_usuario"], "")
        self.assertEqual(perfil["humor_atual"], "neutra")

    def test_atualizar_perfil(self):
        self.mm.atualizar_perfil("nome_usuario", "Zigifrid")
        perfil = self.mm.carregar_perfil()
        self.assertEqual(perfil["nome_usuario"], "Zigifrid")

    def test_atualizar_perfil_lista(self):
        self.mm.atualizar_perfil("apelidos", ["coroa", "velho"])
        perfil = self.mm.carregar_perfil()
        self.assertIn("coroa", perfil["apelidos"])

    # --- Fatos ---
    def test_adicionar_fato(self):
        self.mm.adicionar_fato("Gosta de café amargo")
        perfil = self.mm.carregar_perfil()
        self.assertIn("Gosta de café amargo", perfil["fatos_aprendidos"])

    def test_fato_duplicado_ignorado(self):
        self.mm.adicionar_fato("Joga LoL")
        self.mm.adicionar_fato("Joga LoL")
        perfil = self.mm.carregar_perfil()
        count = perfil["fatos_aprendidos"].count("Joga LoL")
        self.assertEqual(count, 1)

    def test_buscar_fatos_relevantes(self):
        self.mm.adicionar_fato("Gosta de rock pesado")
        self.mm.adicionar_fato("Toma café todo dia")
        self.mm.adicionar_fato("Trabalha com programação")
        result = self.mm.buscar_fatos_relevantes("café")
        self.assertTrue(any("café" in f.lower() for f in result))

    # --- Resumos ---
    def test_salvar_e_carregar_resumo(self):
        self.mm.salvar_resumo("Conversa sobre projetos de IA")
        resumo = self.mm.carregar_resumos_recentes(limit=1)
        self.assertIn("projetos de IA", resumo)

    # --- Tarefas ---
    def test_adicionar_tarefa(self):
        self.mm.adicionar_tarefa("Estudar Python", prioridade=2)
        tasks = self.mm.listar_tarefas()
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["titulo"], "Estudar Python")
        self.assertEqual(tasks[0]["prioridade"], 2)

    def test_concluir_tarefa(self):
        self.mm.adicionar_tarefa("Fazer commit")
        tasks = self.mm.listar_tarefas()
        task_id = tasks[0]["id"]
        result = self.mm.concluir_tarefa(task_id)
        self.assertTrue(result)
        # Tarefa não deve aparecer nas pendentes
        pending = self.mm.listar_tarefas(apenas_pendentes=True)
        self.assertEqual(len(pending), 0)

    def test_remover_tarefa(self):
        self.mm.adicionar_tarefa("Temporária")
        tasks = self.mm.listar_tarefas()
        task_id = tasks[0]["id"]
        result = self.mm.remover_tarefa(task_id)
        self.assertTrue(result)
        all_tasks = self.mm.listar_tarefas(apenas_pendentes=False)
        self.assertEqual(len(all_tasks), 0)

    def test_concluir_tarefa_inexistente(self):
        result = self.mm.concluir_tarefa(999)
        self.assertFalse(result)

    # --- Insights ---
    def test_adicionar_insight(self):
        result = self.mm.adicionar_insight("preferencia", "Gosta de dark mode", 0.8)
        self.assertTrue(result)
        insights = self.mm.buscar_insights()
        self.assertEqual(len(insights), 1)
        self.assertEqual(insights[0]["tipo"], "preferencia")
        self.assertEqual(insights[0]["conteudo"], "Gosta de dark mode")

    def test_insight_duplicado_atualiza(self):
        self.mm.adicionar_insight("habito", "Acorda tarde", 0.5)
        self.mm.adicionar_insight("habito", "Acorda tarde", 0.9)
        insights = self.mm.listar_insights("habito")
        self.assertEqual(len(insights), 1)
        self.assertAlmostEqual(insights[0]["confianca"], 0.9)

    def test_listar_insights_por_tipo(self):
        self.mm.adicionar_insight("preferencia", "Café amargo", 0.8)
        self.mm.adicionar_insight("habito", "Dorme tarde", 0.6)
        self.mm.adicionar_insight("preferencia", "Rock pesado", 0.9)
        prefs = self.mm.listar_insights("preferencia")
        self.assertEqual(len(prefs), 2)
        habitos = self.mm.listar_insights("habito")
        self.assertEqual(len(habitos), 1)


if __name__ == "__main__":
    unittest.main()
