import asyncio
import os
from typing import Optional
from mcp.server.fastmcp import FastMCP
import litellm
from dotenv import load_dotenv

# Carica variabili d'ambiente da file .env se presente
ENV_FILE = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(ENV_FILE)

# Inizializza il server MCP
mcp = FastMCP("External-LLM-Proxy")

# Stato globale per monitoraggio quota
last_status = {
    "model": "Nessuno",
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
async def call_llm(prompt: str, model: str = "gpt-4o-mini", system_prompt: Optional[str] = None) -> str:
    """
    Effettua una chiamata a un LLM esterno tramite LiteLLM.
    
    Args:
        prompt: Il messaggio da inviare al modello.
        model: Il nome del modello (es. 'gpt-4o', 'groq/llama3-70b-8192', 'gemini/gemini-1.5-flash').
        system_prompt: Messaggio di sistema opzionale.
    """
    try:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await litellm.acompletion(
            model=model,
            messages=messages,
        )
        
        content = response.choices[0].message.content
        
        # Aggiornamento stato globale per la risorsa
        last_status["model"] = model
        last_status["requests_remaining"] = remaining_req
        last_status["tokens_remaining"] = remaining_tok
        
        footer = f"\n\n---\n*Modello: {model}* | *Richieste residue: {remaining_req}* | *Token residui: {remaining_tok}*"
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
