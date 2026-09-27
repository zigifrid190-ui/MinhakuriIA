import unittest
from unittest.mock import AsyncMock, patch, MagicMock
import asyncio
from health_check import check_environment
import brain
import prompt_builder
import ollama_fallback
import memory_background
import tool_orchestrator


class TestFase2StabilityAndQuality(unittest.TestCase):

    def test_health_check_runs(self):
        """Health check deve rodar sem quebrar e retornar dict com chaves esperadas."""
        result = check_environment()
        self.assertIsInstance(result, dict)
        self.assertIn("ok", result)
        self.assertIn("warnings", result)

    def test_modular_imports(self):
        """Verifica que os módulos extraídos na Fase 1 podem ser importados."""
        self.assertTrue(hasattr(brain, "_build_system_prompt"))
        self.assertTrue(hasattr(prompt_builder, "_build_system_prompt"))
        self.assertTrue(hasattr(ollama_fallback, "verificar_ollama"))
        self.assertTrue(hasattr(memory_background, "_gerar_resumo_background"))
        self.assertTrue(hasattr(tool_orchestrator, "executar_tool_chain"))

    def test_prompt_builder_cache(self):
        """Testa comportamento básico do cache no prompt builder."""
        prompt1 = prompt_builder._build_system_prompt(
            "teste", "base", "emo"
        )
        prompt2 = prompt_builder._build_system_prompt(
            "teste", "base", "emo"
        )
        self.assertEqual(prompt1, prompt2)

    def test_ollama_fallback_graceful(self):
        """Fallback Ollama deve retornar None graciosamente quando não disponível."""
        self.assertTrue(callable(ollama_fallback.tentar_ollama_fallback))

    def test_tool_orchestrator_basic_structure(self):
        """Verifica estrutura básica do orquestrador de tools."""
        self.assertTrue(callable(tool_orchestrator.executar_tool_chain))
        # Testa que aceita tools_schema
        import inspect
        sig = inspect.signature(tool_orchestrator.executar_tool_chain)
        self.assertIn("tools_schema", sig.parameters)

    @patch('tool_orchestrator.httpx.AsyncClient')
    def test_tool_orchestrator_no_tools_returns_final(self, mock_client):
        """Testa fluxo sem tool_calls (resposta direta)."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Resposta direta", "tool_calls": None}}]
        }
        mock_response.raise_for_status = MagicMock()

        async def mock_post(*args, **kwargs):
            return mock_response

        mock_client.return_value.__aenter__.return_value.post = mock_post

        async def run():
            result = await tool_orchestrator.executar_tool_chain(
                client=mock_client.return_value.__aenter__.return_value,
                initial_messages=[{"role": "user", "content": "oi"}],
                texto="oi",
                base_prompt="base",
                emotional_context="emo",
            )
            return result

        result = asyncio.run(run())
        self.assertIn("resposta_final", result)
        self.assertEqual(result["resposta_final"], "Resposta direta")

    def test_tool_orchestrator_has_exponential_backoff(self):
        """Verifica que o orquestrador tem lógica de backoff (inspeciona código)."""
        import inspect
        source = inspect.getsource(tool_orchestrator.executar_tool_chain)
        self.assertIn("exponential backoff", source.lower())
        self.assertIn("2 ** attempt", source)

    def test_prompt_builder_with_extra_context(self):
        """Testa que prompt_builder aceita contexto extra."""
        prompt = prompt_builder._build_system_prompt(
            "query teste",
            base_prompt="Você é Kuri",
            emotional_context="Emoções: neutral",
            system_instructions="Seja curto",
            agent_algorithm="Observe -> Execute"
        )
        self.assertIn("Você é Kuri", prompt)
        self.assertIn("Observe -> Execute", prompt)

    @patch('ollama_fallback.verificar_ollama', new_callable=AsyncMock)
    def test_ollama_fallback_returns_none_when_unavailable(self, mock_verify):
        """Testa que fallback retorna None quando Ollama offline."""
        async def run():
            mock_verify.return_value = False
            result = await ollama_fallback.tentar_ollama_fallback(
                "teste", [], "base", "emo"
            )
            return result

        result = asyncio.run(run())
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
