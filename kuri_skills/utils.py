import subprocess
from datetime import datetime
from kuri_skills.base import skill

@skill(
    name="que_horas_sao",
    description="Retorna a hora e data atual. Use quando o usuário perguntar que horas são ou que dia é hoje.",
    schema={"type": "object", "properties": {}}
)
def que_horas_sao() -> str:
    agora = datetime.now()
    return f"Agora são {agora.strftime('%H:%M')} de {agora.strftime('%d/%m/%Y')}."


@skill(
    name="ler_clipboard",
    description="Lê o conteúdo atual da área de transferência (clipboard) do usuário.",
    schema={"type": "object", "properties": {}}
)
def ler_clipboard() -> str:
    """Lê o conteúdo atual da área de transferência."""
    try:
        import win32clipboard

        win32clipboard.OpenClipboard()
        try:
            data = win32clipboard.GetClipboardData()
            return f"Clipboard: {data[:500]}" if data else "Clipboard vazio, velho."
        finally:
            win32clipboard.CloseClipboard()
    except ImportError:
        # Fallback via PowerShell
        try:
            result = subprocess.run(
                ["powershell", "-Command", "Get-Clipboard"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return (
                f"Clipboard: {result.stdout.strip()[:500]}"
                if result.stdout.strip()
                else "Clipboard vazio."
            )
        except Exception as e:
            return f"Erro ao ler clipboard: {e}"
    except Exception as e:
        return f"Erro ao ler clipboard: {e}"
