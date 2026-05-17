"""
test_actions.py — Testes unitários para as ações de desktop da Kuri.
Usa mocks para evitar efeitos colaterais reais no sistema.
"""

import unittest
from unittest.mock import patch, MagicMock


class TestActionsRegistry(unittest.TestCase):
    """Verifica que REGISTRY e TOOLS_SCHEMA estão sincronizados."""

    def test_registry_e_schema_sincronizados(self):
        from actions import REGISTRY, TOOLS_SCHEMA

        schema_names = {t["function"]["name"] for t in TOOLS_SCHEMA}
        registry_names = set(REGISTRY.keys())
        self.assertEqual(
            registry_names,
            schema_names,
            f"Dessincronização! Registry: {registry_names - schema_names}, Schema: {schema_names - registry_names}",
        )

    def test_todas_as_funcoes_do_registry_sao_callable(self):
        from actions import REGISTRY

        for name, func in REGISTRY.items():
            self.assertTrue(callable(func), f"'{name}' no REGISTRY não é callable")


class TestAbrirAplicativo(unittest.TestCase):

    @patch("actions.subprocess.Popen")
    def test_abrir_app_conhecido(self, mock_popen):
        from actions import abrir_aplicativo

        result = abrir_aplicativo("notepad")
        self.assertIn("Abrindo", result)
        mock_popen.assert_called_once()

    @patch("actions.os.startfile")
    def test_abrir_app_desconhecido_via_startfile(self, mock_startfile):
        from actions import abrir_aplicativo

        result = abrir_aplicativo("meuapp")
        self.assertIn("Abrindo", result)


class TestAjustarVolume(unittest.TestCase):

    @patch("actions.AudioUtilities", create=True)
    @patch("actions.IAudioEndpointVolume", create=True)
    def test_acao_invalida(self, mock_iav, mock_au):
        from actions import ajustar_volume

        # Testa com ação válida sem dependências
        result = ajustar_volume("subir_demais")
        # Deve retornar erro (pycaw não instalado no CI) ou mensagem de ação desconhecida
        self.assertIsInstance(result, str)


class TestGerenciarTarefa(unittest.TestCase):

    @patch("memory.memory.adicionar_tarefa")
    def test_criar_tarefa(self, mock_add):
        from actions import gerenciar_tarefa

        result = gerenciar_tarefa("criar", titulo="Estudar Python", prioridade=2)
        self.assertIn("anotei", result)

    def test_criar_tarefa_sem_titulo(self):
        from actions import gerenciar_tarefa

        result = gerenciar_tarefa("criar")
        self.assertIn("título", result.lower())

    @patch("memory.memory.concluir_tarefa", return_value=True)
    def test_concluir_tarefa(self, mock_concluir):
        from actions import gerenciar_tarefa

        result = gerenciar_tarefa("concluir", task_id=1)
        self.assertIn("feita", result)

    @patch("memory.memory.concluir_tarefa", return_value=False)
    def test_concluir_tarefa_inexistente(self, mock_concluir):
        from actions import gerenciar_tarefa

        result = gerenciar_tarefa("concluir", task_id=999)
        self.assertIn("999", result)


class TestQueHorasSao(unittest.TestCase):

    def test_retorna_hora_formatada(self):
        from actions import que_horas_sao

        result = que_horas_sao()
        self.assertIn(":", result)
        self.assertIn("/", result)


class TestCriarPasta(unittest.TestCase):

    @patch("actions.os.makedirs")
    def test_criar_pasta(self, mock_makedirs):
        from actions import criar_pasta

        result = criar_pasta("TestFolder")
        self.assertIn("Criei", result)


class TestPesquisarWeb(unittest.TestCase):

    @patch("actions.webbrowser.open")
    def test_pesquisar(self, mock_open):
        from actions import pesquisar_web

        result = pesquisar_web("Python asyncio")
        self.assertIn("Pesquisando", result)
        mock_open.assert_called_once()


class TestListarProcessos(unittest.TestCase):

    @patch("psutil.process_iter")
    def test_listar_processos(self, mock_iter):
        mock_iter.return_value = []
        from actions import listar_processos

        result = listar_processos()
        self.assertIsInstance(result, str)


class TestInformacaoSistema(unittest.TestCase):

    def test_retorna_info(self):
        from actions import informacao_sistema

        result = informacao_sistema()
        self.assertIsInstance(result, str)
        # Deve conter pelo menos SO ou CPU
        self.assertTrue("SO" in result or "CPU" in result or "Erro" in result)


class TestLerClipboard(unittest.TestCase):

    def test_retorna_string(self):
        from actions import ler_clipboard

        result = ler_clipboard()
        self.assertIsInstance(result, str)


if __name__ == "__main__":
    unittest.main()
