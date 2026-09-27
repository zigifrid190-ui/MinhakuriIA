import os
import sys
import time
import subprocess

# Pastas para ignorar no monitoramento
EXCLUDE_DIRS = {'.git', '.venv', '__pycache__', 'dist', 'build', '.pytest_cache', '.ruff_cache', 'tts_cache'}

def get_last_modified_time(path):
    """Retorna o timestamp da última modificação de qualquer arquivo .py no projeto."""
    max_time = 0
    for root, dirs, files in os.walk(path):
        # Filtra pastas excluídas
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    mtime = os.path.getmtime(file_path)
                    if mtime > max_time:
                        max_time = mtime
                except OSError:
                    pass
    return max_time

def main():
    workspace = os.path.dirname(os.path.abspath(__file__))
    print("=" * 60)
    print(" KURI IA — MODO DESENVOLVEDOR (HOT-RELOAD)")
    print(" Monitorando alterações em arquivos .py...")
    print("=" * 60)

    # Encontra o executável do Python correto (da .venv se estiver ativa, ou o global)
    python_exe = sys.executable
    script_path = os.path.join(workspace, "kuri_desktop.py")
    
    current_process = None
    last_mtime = get_last_modified_time(workspace)

    try:
        # Inicializa o processo pela primeira vez
        print("\n[HOT-RELOAD] Iniciando Kuri...")
        current_process = subprocess.Popen([python_exe, script_path])

        while True:
            time.sleep(1.0)
            
            # Verifica se o processo terminou sozinho
            if current_process.poll() is not None:
                # Se terminou com erro ou sucesso, aguarda alterações para reiniciar
                # Para evitar loops infinitos de crash, apenas aguardamos alteração no código
                pass

            # Checa se houve mudanças nos arquivos
            mtime = get_last_modified_time(workspace)
            if mtime > last_mtime:
                print(f"\n[HOT-RELOAD] Alteração detectada! Reiniciando Kuri...")
                last_mtime = mtime
                
                # Encerra o processo anterior
                if current_process and current_process.poll() is None:
                    current_process.terminate()
                    try:
                        current_process.wait(timeout=2.0)
                    except subprocess.TimeoutExpired:
                        current_process.kill()
                
                # Inicia novamente
                current_process = subprocess.Popen([python_exe, script_path])

    except KeyboardInterrupt:
        print("\n[HOT-RELOAD] Encerrando monitoramento...")
        if current_process and current_process.poll() is None:
            current_process.terminate()
            try:
                current_process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                current_process.kill()
        print("[HOT-RELOAD] Feito!")

if __name__ == "__main__":
    main()
