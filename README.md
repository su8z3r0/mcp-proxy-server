# External LLM Proxy Server for Antigravity

Questo repository contiene un server MCP (Model Context Protocol) che funge da proxy per integrare diversi Large Language Models (LLM) tramite i loro piani gratuiti in Antigravity.

## Funzionalità
- **LiteLLM Integration**: Supporta centinaia di modelli (OpenAI, Groq, Gemini, Anthropic, ecc.).
- **Gestione Dinamica API Keys**: Strumenti integrati per aggiungere chiavi API direttamente dalla conversazione.
- **Integrazione Nativa**: Configurato per essere eseguito come server MCP in Antigravity.

## Installazione Automatica (Consigliata)
Su un nuovo PC, basta clonare il repo ed eseguire lo script di setup:
1. `git clone https://github.com/su8z3r0/mcp-proxy-server.git`
2. `cd mcp-proxy-server`
3. `python setup.py`

Lo script creerà il `venv`, installerà le dipendenze e configurerà automaticamente Antigravity per te!

## Installazione Manuale
1. Assicurati di avere Python 3.10+ installato.
2. Crea un ambiente virtuale: `python -m venv venv`
3. Attiva l'ambiente e installa le dipendenze: `pip install mcp litellm python-dotenv`
4. Crea un file `.env` con le tue chiavi API.

## Uso in Antigravity
Il server è configurato in `mcp_config.json` per puntare a questo percorso.

### Tool Disponibili:
- `add_api_key`: Salva una nuova chiave API.
- `get_config_status`: Mostra i provider pronti.
- `call_llm`: Effettua una chiamata a un modello specifico.
