import subprocess
import os
import webbrowser
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
            capture_output=True,
            text=True,
            timeout=5,
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
        return "Abrindo a pasta..."
    return f"Não encontrei a pasta '{caminho}'."


def capturar_tela() -> str:
    try:
        import pyautogui

        screenshot_path = os.path.expanduser("~/Desktop/kuri_screenshot.png")
        pyautogui.screenshot(screenshot_path)
        return "Print salvo na sua área de trabalho!"
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


def salvar_fato_usuario(fato: str) -> str:
    """Salva uma informação importante sobre o usuário na memória de longo prazo."""
    from memory import adicionar_fato

    adicionar_fato(fato)
    return f"Fato memorizado: {fato}"


def atualizar_perfil_usuario(campo: str, valor: str) -> str:
    """Atualiza informações básicas do perfil (nome_usuario, humor_atual, etc)."""
    from memory import atualizar_perfil

    # Converte strings de lista para lista real se necessário
    if campo == "apelidos" and "," in valor:
        valor = [v.strip() for v in valor.split(",")]
    atualizar_perfil(campo, valor)
    return f"Perfil atualizado: {campo} = {valor}"


def gerenciar_tarefa(
    acao: str, titulo: str = None, task_id: int = None, prioridade: int = 1
) -> str:
    """Cria, conclui ou remove tarefas da lista do usuário."""
    from memory import adicionar_tarefa, concluir_tarefa, remover_tarefa

    if acao == "criar":
        if not titulo:
            return "Preciso de um título para criar a tarefa, velho."
        adicionar_tarefa(titulo, prioridade)
        return f"Beleza, anotei aqui: '{titulo}'."

    elif acao == "concluir":
        if task_id is None:
            return "Qual o ID da tarefa que tu terminou?"
        if concluir_tarefa(task_id):
            return f"Boa! Marquei a tarefa {task_id} como feita."
        return f"Não achei nenhuma tarefa com o ID {task_id}."

    elif acao == "remover":
        if task_id is None:
            return "Qual o ID da tarefa para deletar?"
        if remover_tarefa(task_id):
            return f"Tarefa {task_id} removida do seu histórico."
        return f"ID {task_id} não encontrado."

    return f"Ação de tarefa desconhecida: {acao}"


def listar_minhas_tarefas() -> str:
    """Retorna uma lista formatada das tarefas pendentes."""
    from memory import listar_tarefas

    tasks = listar_tarefas(apenas_pendentes=True)
    if not tasks:
        return "Tu tá livre, velho! Nenhuma tarefa pendente."

    output = "Aqui o que tu tem pra fazer:\n"
    for t in tasks:
        prio = "🔥" if t["prioridade"] >= 3 else "⚡" if t["prioridade"] == 2 else "📝"
        output += f"- [{t['id']}] {prio} {t['titulo']}\n"
    return output


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


def listar_processos() -> str:
    """Lista os processos com maior uso de CPU."""
    try:
        import psutil

        procs = []
        for p in psutil.process_iter(["name", "cpu_percent", "memory_percent"]):
            try:
                info = p.info
                if info["cpu_percent"] and info["cpu_percent"] > 0:
                    procs.append(info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        procs.sort(key=lambda x: x.get("cpu_percent", 0), reverse=True)
        top = procs[:10]
        if not top:
            return "Nenhum processo consumindo CPU significativamente."
        lines = [
            f"- {p['name']}: CPU {p['cpu_percent']:.1f}%, RAM {p.get('memory_percent', 0):.1f}%"
            for p in top
        ]
        return "Top processos:\n" + "\n".join(lines)
    except ImportError:
        return "Preciso do psutil instalado para isso."
    except Exception as e:
        return f"Erro ao listar processos: {e}"


def informacao_sistema() -> str:
    """Retorna informações básicas do sistema."""
    try:
        import psutil
        import platform

        cpu = psutil.cpu_percent(interval=0.5)
        ram = psutil.virtual_memory()
        disco = psutil.disk_usage("C:\\")
        bateria = psutil.sensors_battery()
        bat_info = (
            f", Bateria: {bateria.percent}%{'(carregando)' if bateria.power_plugged else ''}"
            if bateria
            else ""
        )
        return (
            f"SO: {platform.system()} {platform.release()}, "
            f"CPU: {cpu}%, "
            f"RAM: {ram.percent}% ({ram.used // (1024**3)}/{ram.total // (1024**3)} GB), "
            f"Disco C: {disco.percent}% usado{bat_info}"
        )
    except Exception as e:
        return f"Erro ao buscar info do sistema: {e}"


def enviar_notificacao(titulo: str, mensagem: str) -> str:
    """Envia uma notificação toast no Windows."""
    try:
        from plyer import notification

        notification.notify(
            title=titulo, message=mensagem, app_name="Kuri IA", timeout=10
        )
        return f"Notificação enviada: {titulo}"
    except ImportError:
        # Fallback via PowerShell
        try:
            ps_script = f'[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null; $xml = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent(0); $xml.GetElementsByTagName("text")[0].AppendChild($xml.CreateTextNode("{titulo}: {mensagem}")) > $null; [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Kuri IA").Show([Windows.UI.Notifications.ToastNotification]::new($xml))'
            # Bandit B602 fix: remove shell=True
            subprocess.Popen(["powershell", "-Command", ps_script])
            return f"Notificação enviada: {titulo}"
        except Exception as e:
            return f"Erro na notificação: {e}"
    except Exception as e:
        return f"Erro na notificação: {e}"


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
    "salvar_fato_usuario": salvar_fato_usuario,
    "atualizar_perfil_usuario": atualizar_perfil_usuario,
    "gerenciar_tarefa": gerenciar_tarefa,
    "listar_minhas_tarefas": listar_minhas_tarefas,
    "ler_clipboard": ler_clipboard,
    "listar_processos": listar_processos,
    "informacao_sistema": informacao_sistema,
    "enviar_notificacao": enviar_notificacao,
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
                    "nome": {
                        "type": "string",
                        "description": "Nome do aplicativo (chrome, notepad, calculadora, etc)",
                    }
                },
                "required": ["nome"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fechar_aplicativo",
            "description": "Fecha um aplicativo que está rodando no computador.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nome": {
                        "type": "string",
                        "description": "Nome do aplicativo para fechar",
                    }
                },
                "required": ["nome"],
            },
        },
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
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "que_horas_sao",
            "description": "Retorna a hora e data atual. Use quando o usuário perguntar que horas são ou que dia é hoje.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "criar_pasta",
            "description": "Cria uma nova pasta na área de trabalho do usuário.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nome": {
                        "type": "string",
                        "description": "Nome da pasta a ser criada",
                    }
                },
                "required": ["nome"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "abrir_pasta",
            "description": "Abre uma pasta do sistema (downloads, documentos, desktop, etc).",
            "parameters": {
                "type": "object",
                "properties": {
                    "caminho": {
                        "type": "string",
                        "description": "Nome da pasta (downloads, documentos, desktop, imagens, musicas, videos) ou caminho absoluto",
                    }
                },
                "required": ["caminho"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "capturar_tela",
            "description": "Tira um screenshot da tela e salva na área de trabalho.",
            "parameters": {"type": "object", "properties": {}},
        },
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
                        "enum": ["aumentar", "diminuir", "mutar", "desmutar"],
                    }
                },
                "required": ["acao"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "salvar_fato_usuario",
            "description": "Salva um fato importante sobre o usuário (ex: 'ele gosta de café amargo', 'ele é programador').",
            "parameters": {
                "type": "object",
                "properties": {
                    "fato": {"type": "string", "description": "O fato a ser lembrado"}
                },
                "required": ["fato"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "atualizar_perfil_usuario",
            "description": "Atualiza campos do perfil do usuário (nome_usuario, apelidos, humor_atual).",
            "parameters": {
                "type": "object",
                "properties": {
                    "campo": {
                        "type": "string",
                        "description": "Campo a atualizar",
                        "enum": ["nome_usuario", "apelidos", "humor_atual"],
                    },
                    "valor": {"type": "string", "description": "Novo valor"},
                },
                "required": ["campo", "valor"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "gerenciar_tarefa",
            "description": "Gerencia a lista de tarefas (To-Do) do usuário. Use para criar, concluir ou remover itens.",
            "parameters": {
                "type": "object",
                "properties": {
                    "acao": {
                        "type": "string",
                        "description": "Ação a realizar",
                        "enum": ["criar", "concluir", "remover"],
                    },
                    "titulo": {
                        "type": "string",
                        "description": "Título da tarefa (apenas para 'criar')",
                    },
                    "task_id": {
                        "type": "integer",
                        "description": "ID da tarefa (para 'concluir' ou 'remover')",
                    },
                    "prioridade": {
                        "type": "integer",
                        "description": "Prioridade de 1 a 3 (3 é urgente)",
                        "default": 1,
                    },
                },
                "required": ["acao"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "listar_minhas_tarefas",
            "description": "Retorna a lista de todas as tarefas pendentes do usuário.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ler_clipboard",
            "description": "Lê o conteúdo atual da área de transferência (clipboard) do usuário.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "listar_processos",
            "description": "Lista os processos rodando no PC com maior uso de CPU e RAM.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "informacao_sistema",
            "description": "Retorna informações do sistema (CPU, RAM, disco, bateria, SO).",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "enviar_notificacao",
            "description": "Envia uma notificação toast no Windows para o usuário.",
            "parameters": {
                "type": "object",
                "properties": {
                    "titulo": {
                        "type": "string",
                        "description": "Título da notificação",
                    },
                    "mensagem": {
                        "type": "string",
                        "description": "Texto da notificação",
                    },
                },
                "required": ["titulo", "mensagem"],
            },
        },
    },
]
