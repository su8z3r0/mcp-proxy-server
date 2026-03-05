import asyncio
import os
from typing import Optional
from mcp.server.fastmcp import FastMCP
import litellm
from dotenv import load_dotenv

# Carica variabili d'ambiente da file .env se presente
ENV_FILE = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(ENV_FILE)

import json
import time
from pathlib import Path

# Inizializza il server MCP
mcp = FastMCP("External-LLM-Proxy")

# Percorso Cockpit per Status Bar
COCKPIT_DIR = Path.home() / ".antigravity_cockpit" / "cache" / "quota_api_v1_plugin" / "authorized"

def update_antigravity_cockpit(model: str, remaining_fraction: float):
    """Inietta i dati di quota nel file JSON di Antigravity Cockpit per vederli nella Status Bar."""
    try:
        if not COCKPIT_DIR.exists():
            return
        
        # Cerca il primo file JSON nella cartella authorized
        files = list(COCKPIT_DIR.glob("*.json"))
        if not files:
            return
        
        file_path = files[0]
        with open(file_path, "r") as f:
            data = json.load(f)
        
        # Inietta o aggiorna il nostro modello custom
        custom_model_id = "custom-mcp-llm"
        if "models" not in data["payload"]:
            data["payload"]["models"] = {}
            
        data["payload"]["models"][custom_model_id] = {
            "displayName": f"MCP: {model}",
            "quotaInfo": {
                "remainingFraction": remaining_fraction,
                "resetTime": "2026-12-31T23:59:59Z"
            },
            "model": "MODEL_CUSTOM_MCP",
            "apiProvider": "API_PROVIDER_INTERNAL",
            "modelProvider": "MODEL_PROVIDER_CUSTOM",
            "supportsCumulativeContext": True
        }
        
        data["updatedAt"] = int(time.time() * 1000)
        
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)
            
    except Exception as e:
        print(f"Errore aggiornamento Cockpit: {e}")

# Carica modello di default da env o usa un fallback
DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL", "groq/llama-3.3-70b-versatile")

# Stato globale per monitoraggio quota
last_status = {
    "model": DEFAULT_MODEL,
    "requests_remaining": "N/A",
    "tokens_remaining": "N/A"
}

@mcp.resource("mcp://quota/status")
def get_quota_status() -> str:
    """Ritorna lo stato dell'ultima quota rilevata."""
    return (
        f"Ultimo Modello: {last_status['model']}\n"
        f"Richieste Residue: {last_status['requests_remaining']}\n"
        f"Token Residui: {last_status['tokens_remaining']}"
    )

@mcp.tool()
async def add_api_key(provider_env_name: str, api_key: str) -> str:
    """
    Aggiunge o aggiorna una chiave API nel file .env.
    
    Args:
        provider_env_name: Il nome della variabile d'ambiente (es. 'GROQ_API_KEY', 'OPENAI_API_KEY').
        api_key: La chiave API da salvare.
    """
    try:
        lines = []
        if os.path.exists(ENV_FILE):
            with open(ENV_FILE, "r") as f:
                lines = f.readlines()
        
        found = False
        new_lines = []
        for line in lines:
            if line.strip().startswith(f"{provider_env_name}="):
                new_lines.append(f"{provider_env_name}={api_key}\n")
                found = True
            else:
                new_lines.append(line)
        
        if not found:
            new_lines.append(f"{provider_env_name}={api_key}\n")
            
        with open(ENV_FILE, "w") as f:
            f.writelines(new_lines)
            
        # Ricarica l'ambiente per la sessione corrente
        os.environ[provider_env_name] = api_key
        return f"Chiave API per {provider_env_name} salvata correttamente."
    except Exception as e:
        return f"Errore durante il salvataggio: {str(e)}"

@mcp.tool()
async def get_config_status() -> str:
    """Mostra quali chiavi API sono attualmente configurate (senza mostrare il valore)."""
    providers = ["OPENAI_API_KEY", "GROQ_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY"]
    status = "Stato Configurazione:\n"
    for p in providers:
        exists = "Configurata ✅" if os.environ.get(p) else "Mancante ❌"
        status += f"- {p}: {exists}\n"
    return status

@mcp.tool()
async def set_default_model(model_name: str) -> str:
    """Imposta il modello di default da usare quando non ne viene specificato uno."""
    global DEFAULT_MODEL
    try:
        # Aggiorna il file .env
        lines = []
        if os.path.exists(ENV_FILE):
            with open(ENV_FILE, "r") as f:
                lines = f.readlines()
        
        found = False
        new_lines = []
        for line in lines:
            if line.strip().startswith("DEFAULT_MODEL="):
                new_lines.append(f"DEFAULT_MODEL={model_name}\n")
                found = True
            else:
                new_lines.append(line)
        
        if not found:
            new_lines.append(f"DEFAULT_MODEL={model_name}\n")
            
        with open(ENV_FILE, "w") as f:
            f.writelines(new_lines)
            
        DEFAULT_MODEL = model_name
        return f"Modello di default impostato su: {model_name}"
    except Exception as e:
        return f"Errore nell'impostazione del modello: {str(e)}"

@mcp.tool()
async def call_llm(prompt: str, model: Optional[str] = None, system_prompt: Optional[str] = None) -> str:
    """
    Effettua una chiamata a un LLM esterno tramite LiteLLM.
    
    Args:
        prompt: Il messaggio da inviare al modello.
        model: Opzionale. Il nome del modello. Se omesso, usa quello di default.
        system_prompt: Messaggio di sistema opzionale.
    """
    selected_model = model or DEFAULT_MODEL
    try:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await litellm.acompletion(
            model=selected_model,
            messages=messages,
        )
        
        content = response.choices[0].message.content
        
        # Estrazione info rate limit se disponibili (es. Groq)
        headers = getattr(response, "_response_headers", {})
        remaining_req = headers.get("x-ratelimit-remaining-requests", "N/A")
        remaining_tok = headers.get("x-ratelimit-remaining-tokens", "N/A")

        # Calcola una frazione approssimativa per la barra di stato (0.0 a 1.0)
        # Se non disponibile, mostriamo 1.0 (pieno)
        fraction = 1.0
        try:
            if remaining_req != "N/A" and "/" in str(headers.get("x-ratelimit-limit-requests", "")):
                # Alcuni header sono "100/1000", altri solo numeri
                limit = float(str(headers.get("x-ratelimit-limit-requests")).split("/")[0])
                fraction = min(1.0, float(remaining_req) / limit)
            elif remaining_req != "N/A":
                # Fallback arbitrario se non sappiamo il totale (es. assumiamo 1000)
                fraction = min(1.0, float(remaining_req) / 1000.0)
        except:
            pass

        # Aggiornamento stato globale per la risorsa e Cockpit
        last_status["model"] = selected_model
        last_status["requests_remaining"] = remaining_req
        last_status["tokens_remaining"] = remaining_tok
        
        update_antigravity_cockpit(selected_model, fraction)
        
        footer = f"\n\n---\n*Modello: {selected_model}* | *Richieste residue: {remaining_req}* | *Token residui: {remaining_tok}*"
        return content + footer

    except litellm.exceptions.RateLimitError as e:
        return (
            f"⚠️ **Rate Limit Raggiunto** per il modello `{model}`.\n\n"
            f"Dettagli: {str(e)}\n\n"
            "Consiglio: Attendi qualche secondo o prova a usare un altro provider (es. Gemini o OpenAI) "
            "tramite il comando `call_llm` con un altro prefisso."
        )
    except Exception as e:
        return f"Errore durante la chiamata al modello {model}: {str(e)}"

@mcp.tool()
async def list_available_models() -> str:
    """Ritorna una nota su come configurare i modelli."""
    return (
        "Puoi usare qualsiasi modello supportato da LiteLLM. "
        "Assicurati di aver impostato le chiavi API nel file .env (es. OPENAI_API_KEY, GROQ_API_KEY)."
    )

if __name__ == "__main__":
    mcp.run()
