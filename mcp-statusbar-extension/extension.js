const vscode = require('vscode');
const fs = require('fs');
const path = require('path');

let statusBarItem;

function activate(context) {
    statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
    statusBarItem.command = 'mcp-quota-monitor.refresh';
    context.subscriptions.push(statusBarItem);

    // Placeholder per il percorso del file di stato (verrà iniettato dal setup.py)
    const statusFilePath = path.join(__dirname, '..', 'status.json');

    function updateStatusBar() {
        if (!fs.existsSync(statusFilePath)) {
            statusBarItem.text = "$(cloud-download) MCP: Inattivo";
            statusBarItem.tooltip = "Server MCP non ancora utilizzato o file status.json mancante";
            statusBarItem.show();
            return;
        }

        try {
            const data = JSON.parse(fs.readFileSync(statusFilePath, 'utf8'));
            const model = data.model || 'N/A';
            const fraction = (data.fraction * 100).toFixed(0);
            const req = data.requests || 'N/A';

            statusBarItem.text = `$(zap) ${model} (${fraction}%)`;
            statusBarItem.tooltip = `Richieste residue: ${req}\nModello: ${model}\nQuota: ${fraction}%`;

            // Cambia colore in base alla quota
            if (data.fraction < 0.2) {
                statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.errorBackground');
            } else if (data.fraction < 0.5) {
                statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.warningBackground');
            } else {
                statusBarItem.backgroundColor = undefined;
            }

            statusBarItem.show();
        } catch (e) {
            console.error("Errore lettura status.json:", e);
        }
    }

    // Aggiorna ogni 30 secondi e osserva il file
    const timer = setInterval(updateStatusBar, 30000);
    const watcher = fs.watch(path.dirname(statusFilePath), (eventType, filename) => {
        if (filename === 'status.json') {
            updateStatusBar();
        }
    });

    context.subscriptions.push({ dispose: () => clearInterval(timer) });
    context.subscriptions.push({ dispose: () => watcher.close() });

    updateStatusBar();

    let disposable = vscode.commands.registerCommand('mcp-quota-monitor.refresh', () => {
        updateStatusBar();
        vscode.window.showInformationMessage('Stato Quota MCP Aggiornato!');
    });

    context.subscriptions.push(disposable);
}

function deactivate() { }

module.exports = {
    activate,
    deactivate
}
