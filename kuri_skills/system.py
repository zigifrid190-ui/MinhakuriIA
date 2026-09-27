import subprocess
import os
from kuri_skills.base import skill

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

@skill(
    name="abrir_aplicativo",
    description="Abre um aplicativo no computador do usuário. Use quando ele pedir para abrir algo.",
    schema={
        "type": "object",
        "properties": {
            "nome": {
                "type": "string",
                "description": "Nome do aplicativo (chrome, notepad, calculadora, etc)",
            }
        },
        "required": ["nome"],
    }
)
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


@skill(
    name="fechar_aplicativo",
    description="Fecha um aplicativo que está rodando no computador.",
    schema={
        "type": "object",
        "properties": {
            "nome": {
                "type": "string",
                "description": "Nome do aplicativo para fechar",
            }
        },
        "required": ["nome"],
    }
)
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


@skill(
    name="capturar_tela",
    description="Tira um screenshot da tela e salva na área de trabalho.",
    schema={"type": "object", "properties": {}}
)
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


@skill(
    name="ajustar_volume",
    description="Ajusta o volume do sistema (aumentar, diminuir, mutar, desmutar).",
    schema={
        "type": "object",
        "properties": {
            "acao": {
                "type": "string",
                "description": "Ação de volume: aumentar, diminuir, mutar, desmutar",
                "enum": ["aumentar", "diminuir", "mutar", "desmutar"],
            }
        },
        "required": ["acao"],
    }
)
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


@skill(
    name="listar_processos",
    description="Lista os processos rodando no PC com maior uso de CPU e RAM.",
    schema={"type": "object", "properties": {}}
)
def listar_processos() -> str:
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


@skill(
    name="informacao_sistema",
    description="Retorna informações do sistema (CPU, RAM, disco, bateria, SO).",
    schema={"type": "object", "properties": {}}
)
def informacao_sistema() -> str:
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


@skill(
    name="enviar_notificacao",
    description="Envia uma notificação toast no Windows para o usuário.",
    schema={
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
    }
)
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
            subprocess.Popen(["powershell", "-Command", ps_script])
            return f"Notificação enviada: {titulo}"
        except Exception as e:
            return f"Erro na notificação: {e}"
    except Exception as e:
        return f"Erro na notificação: {e}"


@skill(
    name="recarregar_skills",
    description="Recarrega todas as ferramentas e habilidades da Kuri a partir da pasta de skills em tempo real.",
    schema={"type": "object", "properties": {}}
)
def recarregar_skills() -> str:
    """Recarrega dinamicamente as skills."""
    import actions
    actions.load_dynamic_skills()
    return f"Sucesso, velho! Recarreguei as skills. Agora tenho {len(actions.REGISTRY)} ferramentas prontas no cérebro."


@skill(
    name="atualizar_personalidade",
    description="Atualiza a personalidade/humor da Kuri baseado em feedback do usuário via voz. Ex: 'fica mais sarcástica', 'seja mais empática'.",
    schema={
        "type": "object",
        "properties": {
            "instrucao": {
                "type": "string",
                "description": "Instrução de como ajustar a personalidade (ex: 'mais sarcástica', 'mais carinhosa', 'focada')"
            }
        },
        "required": ["instrucao"]
    }
)
def atualizar_personalidade(instrucao: str) -> str:
    """Grava traço de identidade + humor, se der para mapear. Não é só um enum."""
    from memory import adicionar_clausula_identidade, atualizar_perfil

    instrucao = (instrucao or "").strip()
    if not instrucao:
        return "Me diz como você quer que eu fique, velho."

    instrucao_lower = instrucao.lower()
    humor_map = {
        "sarcástica": "sarcastica",
        "sarcasmo": "sarcastica",
        "carinhosa": "carinhosa",
        "empática": "empatica",
        "empatica": "empatica",
        "focada": "focada",
        "séria": "seria",
        "seria": "seria",
        "caótica": "caotica",
        "caotica": "caotica",
        "animada": "animada",
        "hiperativa": "hiperativa",
    }
    novo_humor = None
    for key, val in humor_map.items():
        if key in instrucao_lower:
            novo_humor = val
            break

    if novo_humor:
        atualizar_perfil("humor_atual", novo_humor)
    atualizar_perfil("personalidade_ajuste", instrucao)
    adicionar_clausula_identidade(instrucao, origem="usuario")

    if novo_humor:
        return f"Beleza. Humor '{novo_humor}' e anotei na identidade: {instrucao}"
    return f"Anotei na identidade: {instrucao}"


@skill(
    name="diagnosticar_sistema",
    description="Realiza um diagnóstico completo do sistema Kuri: skills carregadas, saúde, dependências, e status geral. Use para depurar ou verificar o estado da assistente.",
    schema={"type": "object", "properties": {}}
)
def diagnosticar_sistema() -> str:
    """Skill de diagnóstico do sistema (Fase 3 - Evolução de Skills, aprofundado)."""
    import actions
    from kuri_skills.base import skill_registry
    from health_check import check_environment

    try:
        health = check_environment()
        skills_meta = skill_registry.get_all_skills_with_meta()
        total_skills = len(skills_meta)

        # Verifica dependências (melhorado)
        dep_warnings = []
        for s in skills_meta:
            for dep in s.get("dependencies", []):
                if not any(x["name"] == dep for x in skills_meta):
                    dep_warnings.append(f"Skill '{s['name']}' depende de '{dep}' que não está carregada.")

        # Fase 4 + memória + perfil
        try:
            from memory import memory as mem
            perfil = mem.carregar_perfil()
            humor = perfil.get("humor_atual", "neutra")
            fatos_count = len(mem.buscar_fatos_relevantes("", limit=1000)) if hasattr(mem, "buscar_fatos_relevantes") else "N/A"
        except Exception:
            humor = "desconhecido"
            fatos_count = "erro"

        # Whisper model (do config se disponível)
        try:
            import config
            whisper_model = getattr(config, "WHISPER_MODEL", "desconhecido")
        except Exception:
            whisper_model = "desconhecido"

        report = [
            "=== Diagnóstico Kuri IA ===",
            f"Skills carregadas: {total_skills}",
            f"Health OK: {health.get('ok', False)}",
            f"Avisos de health: {len(health.get('warnings', []))}",
            f"Personalidade/Humor atual: {humor}",
            f"Modelo Whisper: {whisper_model}",
            f"Fatos relevantes aproximados: {fatos_count}",
        ]
        if dep_warnings:
            report.append("Avisos de dependências:")
            report.extend(f"  - {w}" for w in dep_warnings)
        else:
            report.append("Dependências: todas resolvidas.")

        # Lista top skills
        report.append("\nPrincipais skills:")
        for s in skills_meta[:6]:
            deps_str = f" (deps: {', '.join(s['dependencies'])})" if s.get('dependencies') else ""
            report.append(f"  - {s['name']}: {s['description'][:55]}...{deps_str}")

        report.append("\nUse 'recarregar_skills' ou 'diagnosticar_sistema' novamente se necessário.")
        return "\n".join(report)
    except Exception as e:
        return f"Erro no diagnóstico: {e}"

