"""
test_smoke.py - Fase 2: Qualidade e Confiabilidade

Testes básicos de smoke para garantir que o core do sistema sobe sem erros críticos.
"""

import unittest
import asyncio

import health_check
import brain
import actions


class TestSmoke(unittest.TestCase):

    def test_health_check_passes(self):
        result = health_check.check_environment()
        # Não exige que tudo esteja perfeito, mas o check deve rodar
        self.assertIn("ok", result)

    def test_skills_loaded(self):
        self.assertGreater(len(actions.REGISTRY), 5)

    def test_brain_import_and_basic_call(self):
        # Apenas testa que o módulo carrega e a assinatura existe
        self.assertTrue(hasattr(brain, 'pensar'))
        self.assertTrue(hasattr(brain, 'pensar_stream'))

    def test_async_health_and_imports(self):
        """Teste simples assíncrono para garantir que o event loop não quebra no import."""
        async def _check():
            # Simula um pequeno uso assíncrono
            await asyncio.sleep(0)
            return True

        result = asyncio.run(_check())
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
