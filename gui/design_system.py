"""
design_system.py — Tokens de Design para a Kuri (Design Olympus/Linear).
Centraliza cores, fontes, raios de borda e efeitos de glow.
"""


class DesignTokens:
    # ── Cores Base (Linear Dark) ──────────────────────────────────────────────
    BG_ROOT = "#080808"  # Quase preto, premium
    BG_CARD = "#0D0D0D"
    BG_SECONDARY = "#141414"
    BORDER = "#1A1A1A"
    BORDER_LIGHT = "#2A2A2A"

    # ── Cores de Ação ─────────────────────────────────────────────────────────
    ACCENT_NEON = "#00FF88"  # Verde Kuri Signature
    ACCENT_GLOW = "rgba(0, 255, 136, 0.15)"

    # ── Tipografia ────────────────────────────────────────────────────────────
    FONT_PRIMARY = "'Inter', 'Segoe UI', sans-serif"
    FONT_MONO = "'JetBrains Mono', 'Consolas', monospace"

    # ── Estados ───────────────────────────────────────────────────────────────
    COLOR_IDLE = "#3A3A3A"
    COLOR_LISTENING = "#00FF88"
    COLOR_THINKING = "#6366F1"  # Indigo para pensar
    COLOR_SPEAKING = "#00D1FF"  # Azul claro para falar
    COLOR_SLEEPING = "#4A4A6A"  # Roxo/azul escuro suave para sono
    COLOR_ERROR = "#FF3333"

    # ── Estilos CSS Reutilizáveis ─────────────────────────────────────────────
    @classmethod
    def get_main_style(cls):
        return f"""
        QWidget#kuri_root {{
            background-color: {cls.BG_ROOT};
            border: 1px solid {cls.BORDER};
            border-radius: 12px;
        }}
        
        QLabel#header_title {{
            color: #808080;
            font-family: {cls.FONT_MONO};
            font-size: 10px;
            font-weight: bold;
            letter-spacing: 2px;
        }}
        
        QLabel#header_clock {{
            color: #404040;
            font-family: {cls.FONT_MONO};
            font-size: 10px;
        }}
        
        QFrame#indicator_ring {{
            border: 2px solid {cls.BORDER};
            border-radius: 110px; /* Metade de 220 */
        }}
        
        QLabel#text_bubble {{
            color: #E0E0E0;
            font-family: {cls.FONT_PRIMARY};
            font-size: 11px;
            padding: 12px;
            background-color: {cls.BG_SECONDARY};
            border: 1px solid {cls.BORDER};
            border-radius: 8px;
        }}
        
        QPushButton.btn_icon {{
            background-color: transparent;
            color: #606060;
            border: 1px solid {cls.BORDER_LIGHT};
            border-radius: 6px;
            font-size: 14px;
        }}
        
        QPushButton.btn_icon:hover {{
            color: #FFFFFF;
            border-color: #404040;
            background-color: #1A1A1A;
        }}
        
        QPushButton#btn_mic_active {{
            background-color: rgba(0, 255, 136, 0.1);
            color: {cls.ACCENT_NEON};
            border: 1px solid {cls.ACCENT_NEON};
        }}
        
        QLabel#status_dot {{
            background-color: {cls.COLOR_IDLE};
            border: 1.5px solid {cls.BG_ROOT};
            border-radius: 6px;
        }}
        """
