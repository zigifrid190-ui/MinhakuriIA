"""
kuri_bridge.py — Ponte de comunicação entre a GUI (PyQt6) e o core Python (asyncio).

Estados da Kuri:
    IDLE       → Neutra, aguardando
    LISTENING  → Ouvindo o microfone
    THINKING   → Processando resposta (LLM)
    SPEAKING   → Reproduzindo áudio
    ERROR      → Erro ou timeout
"""

from enum import Enum, auto
import threading
import queue


class KuriState(Enum):
    IDLE = auto()
    LISTENING = auto()
    THINKING = auto()
    SPEAKING = auto()
    SLEEPING = auto()   # Modo sono / suspenso - baixo consumo
    ERROR = auto()


class KuriBridge:
    """
    Bridge thread-safe entre GUI e core.
    A GUI observa mudanças de estado e envia comandos de controle.
    O core Python reporta estado e envia textos de resposta.
    """

    def __init__(self):
        # Core → GUI: mudanças de estado e texto
        self._state_callbacks: list = []
        self._text_callbacks: list = []
        self._emotion_callbacks: list = []

        # GUI → Core: comandos (ex: "start_listen", "stop")
        self.command_queue: queue.Queue = queue.Queue()

        self._state = KuriState.IDLE
        self._emotion = "neutral"
        self._mouth_open = 0.0
        self._lock = threading.Lock()

    # ── Estado ──────────────────────────────────────────────────────────────

    @property
    def state(self) -> KuriState:
        with self._lock:
            return self._state

    def set_state(self, new_state: KuriState):
        """Chamado pelo core para atualizar o estado (thread-safe)."""
        with self._lock:
            self._state = new_state
        for cb in self._state_callbacks:
            cb(new_state)

    def on_state_change(self, callback):
        """Registra callback da GUI para receber mudanças de estado."""
        self._state_callbacks.append(callback)

    # ── Emoção ──────────────────────────────────────────────────────────────

    def set_emotion(self, new_emotion: str):
        """Chamado pelo core para mudar a emoção do avatar."""
        with self._lock:
            if self._emotion == new_emotion:
                return
            self._emotion = new_emotion
        for cb in self._emotion_callbacks:
            cb(new_emotion)

    def on_emotion(self, callback):
        """Registra callback da GUI para receber mudanças de emoção."""
        self._emotion_callbacks.append(callback)

    # ── Boca (lip sync) ───────────────────────────────────────────────────────

    @property
    def mouth_open(self) -> float:
        with self._lock:
            return self._mouth_open

    def set_mouth(self, value: float):
        """0.0 fechada … 1.0 aberta. Chamado pelo TTS a cada frame de áudio."""
        clamped = max(0.0, min(1.0, float(value)))
        with self._lock:
            self._mouth_open = clamped

    # ── Texto da Kuri ────────────────────────────────────────────────────────

    def emit_text(self, text: str):
        """Chamado pelo core para enviar o último texto da Kuri para a GUI."""
        for cb in self._text_callbacks:
            cb(text)

    def on_text(self, callback):
        """Registra callback da GUI para receber textos da Kuri."""
        self._text_callbacks.append(callback)

    # ── Comandos da GUI ──────────────────────────────────────────────────────

    def send_command(self, command: str):
        """Chamado pela GUI para enviar comando ao core (ex: 'stop')."""
        self.command_queue.put_nowait(command)

    def get_command(self, timeout: float = 0.05) -> str | None:
        """Chamado pelo core para verificar comandos pendentes da GUI."""
        try:
            return self.command_queue.get(timeout=timeout)
        except queue.Empty:
            return None


# Instância global compartilhada entre GUI e core
bridge = KuriBridge()
