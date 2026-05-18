import unittest
from unittest.mock import patch
import actions
from kuri_skills.base import hook_manager

class TestDynamicSkillsAndHooks(unittest.TestCase):

    def test_dynamic_registry_populated(self):
        """Verifica que as skills dinâmicas foram carregadas no REGISTRY público."""
        self.assertGreater(len(actions.REGISTRY), 0)
        self.assertIn("abrir_aplicativo", actions.REGISTRY)
        self.assertIn("pesquisar_web", actions.REGISTRY)
        self.assertIn("que_horas_sao", actions.REGISTRY)
        self.assertIn("recarregar_skills", actions.REGISTRY)

    def test_hooks_firing(self):
        """Testa se os hooks de pré e pós-execução estão sendo disparados corretamente."""
        pre_called = []
        post_called = []

        def dummy_pre(name, args):
            pre_called.append((name, args))

        def dummy_post(name, args, result):
            post_called.append((name, args, result))

        # Registra temporariamente os hooks
        hook_manager.register_pre_hook(dummy_pre)
        hook_manager.register_post_hook(dummy_post)

        # Executa uma skill simples
        actions.que_horas_sao()

        # Verifica se os hooks foram disparados
        self.assertTrue(any(item[0] == "que_horas_sao" for item in pre_called))
        self.assertTrue(any(item[0] == "que_horas_sao" for item in post_called))

    @patch("memory.adicionar_historico_acao")
    def test_sqlite_persistence_via_hook(self, mock_add_action):
        """Verifica se as execuções de ações são salvas no SQLite através do Hook."""
        actions.que_horas_sao()
        # O mock deve ser chamado para registrar a execução
        mock_add_action.assert_called()
        self.assertEqual(mock_add_action.call_args[1]["nome_acao"], "que_horas_sao")

    def test_recarregar_skills(self):
        """Verifica se a ferramenta recarregar_skills roda com sucesso."""
        result = actions.recarregar_skills()
        self.assertIn("Sucesso", result)
        self.assertIn("ferramentas prontas", result)

if __name__ == "__main__":
    unittest.main()
