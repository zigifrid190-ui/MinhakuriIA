"""Movimento 1 — runtime único, tools no stream, atenção."""

import inspect
import unittest

import brain
import kuri_runtime
from actions import REGISTRY, TOOLS_SCHEMA
from kuri_runtime import conversation_open, is_kuri_speaking, is_wake_word, open_conversation, set_speaking


class TestWakeWord(unittest.TestCase):
    def test_chama_kuri(self):
        self.assertTrue(is_wake_word("Kuri que horas são"))
        self.assertTrue(is_wake_word("ei kuri"))
        self.assertTrue(is_wake_word("acorda kuri"))

    def test_nao_e_chamado(self):
        self.assertFalse(is_wake_word("abre o chrome"))
        self.assertFalse(is_wake_word("Está tranquilo."))
        self.assertFalse(is_wake_word(""))
        self.assertFalse(is_wake_word(None))

    def test_kuri_no_meio_da_frase(self):
        self.assertTrue(is_wake_word("oi kuri abre o notepad"))


class TestConversationWindow(unittest.TestCase):
    def test_abre_janela(self):
        open_conversation()
        self.assertTrue(conversation_open())


class TestSpeakingFlag(unittest.TestCase):
    def test_anti_eco_flag(self):
        set_speaking(False)
        set_speaking(True)
        self.assertTrue(is_kuri_speaking())
        set_speaking(False)
        self.assertTrue(is_kuri_speaking())  # cauda curta após o fim da fala


class TestStreamTools(unittest.TestCase):
    def test_pensar_stream_envia_tools(self):
        src = inspect.getsource(brain.pensar_stream)
        self.assertIn("TOOLS_SCHEMA", src)
        self.assertIn("tool_choice", src)

    def test_process_utterance_existe(self):
        self.assertTrue(callable(kuri_runtime.process_utterance))

    def test_skill_que_horas_executa(self):
        self.assertIn("que_horas_sao", REGISTRY)
        result = REGISTRY["que_horas_sao"]()
        self.assertIn("Agora são", result)

    def test_schema_e_registry_alinhados(self):
        names = {t["function"]["name"] for t in TOOLS_SCHEMA}
        self.assertEqual(names, set(REGISTRY.keys()))


if __name__ == "__main__":
    unittest.main()
