import os
import sys
import json
import subprocess
from pathlib import Path

def run_command(cmd, cwd=None):
    print(f"Esecuzione: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd)
    if result.returncode != 0:
        print(f"Errore nell'esecuzione del comando: {cmd}")
        return False
    return True

def setup():
    print("--- Inizio Installazione Automatica Plugin External-LLMs ---")
    
    current_dir = Path(__file__).parent.absolute()
    venv_dir = current_dir / "venv"
    python_exe = venv_dir / "Scripts" / "python.exe" if os.name == "nt" else venv_dir / "bin" / "python"
    
    # 1. Creazione VENV
    if not venv_dir.exists():
        if not run_command(f"{sys.executable} -m venv venv", cwd=current_dir):
            return
    
    # 2. Installazione dipendenze
    pip_exe = venv_dir / "Scripts" / "pip.exe" if os.name == "nt" else venv_dir / "bin" / "pip"
    if not run_command(f"{pip_exe} install mcp litellm python-dotenv", cwd=current_dir):
        return

    # 3. Rilevamento mcp_config.json
    # Solitamente in ~/.gemini/antigravity/mcp_config.json
    home = Path.home()
    config_path = home / ".gemini" / "antigravity" / "mcp_config.json"
    
    if not config_path.exists():
        print(f"AVVISO: Non ho trovato il file di configurazione in {config_path}")
        print("Assicurati che Antigravity sia installato e avviato almeno una volta.")
        return

    # 4. Aggiornamento configurazione
    try:
        with open(config_path, "r") as f:
            content = f.read().strip()
            config = json.loads(content) if content else {"mcpServers": {}}
    except Exception:
        config = {"mcpServers": {}}

    if "mcpServers" not in config:
        config["mcpServers"] = {}

    # Configurazione del server con percorsi assoluti rilevati
    config["mcpServers"]["external-llms"] = {
        "command": str(python_exe).replace("\\", "/"),
        "args": [str(current_dir / "server.py").replace("\\", "/")],
        "env": {
            "PYTHONPATH": str(current_dir).replace("\\", "/")
        }
    }

    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    print(f"\n✅ Configurazione completata!")
    print(f"Plugin installato correttamente in Antigravity.")
    print(f"Percorso config aggiornato: {config_path}")
    print("\n--- Prossimi Passi ---")
    print("1. Riavvia Antigravity.")
    print("2. Aggiungi le tue chiavi API tramite chat o nel file .env.")

if __name__ == "__main__":
    setup()
