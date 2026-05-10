import subprocess
import os
import webbrowser
import json
from datetime import datetime

# ===== Mapa de aplicativos conhecidos (Windows) =====
APPS = {
    "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "firefox": r"C:\Program Files\Mozilla Firefox\firefox.exe",
    "notepad": "notepad.exe",
    "calculadora": "calc.exe",
    "paint": "mspaint.exe",
    "explorador": "explorer.exe",
    "cmd": "cmd.exe",
    "powershell": "powershell.exe",
}


def abrir_aplicativo(nome: str) -> str:
    nome_lower = nome.lower().strip()

    # Primeiro tenta no mapa de apps conhecidos
    if nome_lower in APPS:
        try:
            subprocess.Popen(APPS[nome_lower], shell=True)
            return f"Abrindo {nome}..."
        except Exception as e:
            return f"Erro ao abrir {nome}: {e}"

    # Tenta abrir pelo nome direto (Windows pode resolver)
    try:
        os.startfile(nome_lower)
        return f"Abrindo {nome}..."
    except OSError:
        pass

    # Tenta buscar no menu iniciar
    try:
        subprocess.Popen(f"start {nome_lower}", shell=True)
        return f"Tentando abrir {nome}..."
    except Exception:
        return f"Não achei o {nome} no seu PC, velho. Tenta me dizer o caminho exato."


def fechar_aplicativo(nome: str) -> str:
    nome_lower = nome.lower().strip()
    try:
        result = subprocess.run(
            ["taskkill", "/IM", f"{nome_lower}.exe", "/F"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return f"Fechei o {nome}!"
        return f"O {nome} nem tava aberto ou não consegui fechar."
    except Exception as e:
        return f"Erro ao fechar {nome}: {e}"


def pesquisar_web(query: str) -> str:
    url = f"https://www.google.com/search?q={query}"
    webbrowser.open(url)
    return f"Pesquisando '{query}' no Google pra você..."


def que_horas_sao() -> str:
    agora = datetime.now()
    return f"Agora são {agora.strftime('%H:%M')} de {agora.strftime('%d/%m/%Y')}."


def criar_pasta(nome: str) -> str:
    caminho = os.path.expanduser(f"~/Desktop/{nome}")
    try:
        os.makedirs(caminho, exist_ok=True)
        return f"Criei a pasta '{nome}' na sua área de trabalho!"
    except Exception as e:
        return f"Erro ao criar pasta: {e}"


def abrir_pasta(caminho: str) -> str:
    expanded = os.path.expanduser(caminho)
    pastas_conhecidas = {
        "downloads": os.path.expanduser("~/Downloads"),
        "documentos": os.path.expanduser("~/Documents"),
        "desktop": os.path.expanduser("~/Desktop"),
        "area de trabalho": os.path.expanduser("~/Desktop"),
        "imagens": os.path.expanduser("~/Pictures"),
        "musicas": os.path.expanduser("~/Music"),
        "videos": os.path.expanduser("~/Videos"),
    }

    alvo = pastas_conhecidas.get(caminho.lower().strip(), expanded)

    if os.path.isdir(alvo):
        os.startfile(alvo)
        return f"Abrindo a pasta..."
    return f"Não encontrei a pasta '{caminho}'."


def capturar_tela() -> str:
    try:
        import pyautogui
        screenshot_path = os.path.expanduser("~/Desktop/kuri_screenshot.png")
        pyautogui.screenshot(screenshot_path)
        return f"Print salvo na sua área de trabalho!"
    except ImportError:
        return "Preciso do pyautogui instalado para isso. Roda: pip install pyautogui"
    except Exception as e:
        return f"Erro ao tirar print: {e}"


def ajustar_volume(acao: str) -> str:
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))

        current = volume.GetMasterVolumeLevelScalar()

        if acao == "aumentar":
            volume.SetMasterVolumeLevelScalar(min(1.0, current + 0.1), None)
            return f"Volume aumentado para {int(min(1.0, current + 0.1) * 100)}%"
        elif acao == "diminuir":
            volume.SetMasterVolumeLevelScalar(max(0.0, current - 0.1), None)
            return f"Volume diminuído para {int(max(0.0, current - 0.1) * 100)}%"
        elif acao == "mutar":
            volume.SetMute(1, None)
            return "Mutei o som!"
        elif acao == "desmutar":
            volume.SetMute(0, None)
            return "Som desmutado!"
        return f"Não entendi a ação de volume: {acao}"
    except ImportError:
        return "Preciso do pycaw instalado. Roda: pip install pycaw comtypes"
    except Exception as e:
        return f"Erro no volume: {e}"


# ===== Registro de funções (usado pelo brain.py via function calling) =====
REGISTRY = {
    "abrir_aplicativo": abrir_aplicativo,
    "fechar_aplicativo": fechar_aplicativo,
    "pesquisar_web": pesquisar_web,
    "que_horas_sao": que_horas_sao,
    "criar_pasta": criar_pasta,
    "abrir_pasta": abrir_pasta,
    "capturar_tela": capturar_tela,
    "ajustar_volume": ajustar_volume,
}

# ===== Definição de Tools para Function Calling do LLM =====
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "abrir_aplicativo",
            "description": "Abre um aplicativo no computador do usuário. Use quando ele pedir para abrir algo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nome": {"type": "string", "description": "Nome do aplicativo (chrome, notepad, calculadora, etc)"}
                },
                "required": ["nome"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "fechar_aplicativo",
            "description": "Fecha um aplicativo que está rodando no computador.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nome": {"type": "string", "description": "Nome do aplicativo para fechar"}
                },
                "required": ["nome"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "pesquisar_web",
            "description": "Faz uma pesquisa no Google e abre no navegador.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "O que pesquisar"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "que_horas_sao",
            "description": "Retorna a hora e data atual. Use quando o usuário perguntar que horas são ou que dia é hoje.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "criar_pasta",
            "description": "Cria uma nova pasta na área de trabalho do usuário.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nome": {"type": "string", "description": "Nome da pasta a ser criada"}
                },
                "required": ["nome"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "abrir_pasta",
            "description": "Abre uma pasta do sistema (downloads, documentos, desktop, etc).",
            "parameters": {
                "type": "object",
                "properties": {
                    "caminho": {"type": "string", "description": "Nome da pasta (downloads, documentos, desktop, imagens, musicas, videos) ou caminho absoluto"}
                },
                "required": ["caminho"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "capturar_tela",
            "description": "Tira um screenshot da tela e salva na área de trabalho.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ajustar_volume",
            "description": "Ajusta o volume do sistema (aumentar, diminuir, mutar, desmutar).",
            "parameters": {
                "type": "object",
                "properties": {
                    "acao": {
                        "type": "string",
                        "description": "Ação de volume: aumentar, diminuir, mutar, desmutar",
                        "enum": ["aumentar", "diminuir", "mutar", "desmutar"]
                    }
                },
                "required": ["acao"]
            }
        }
    },
]
