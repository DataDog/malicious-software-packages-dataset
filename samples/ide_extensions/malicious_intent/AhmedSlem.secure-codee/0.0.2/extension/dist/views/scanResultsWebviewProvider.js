"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.ScanResultsWebviewProvider = void 0;
const vscode = require("vscode");
class ScanResultsWebviewProvider {
    constructor(_extensionUri, _state) {
        this._extensionUri = _extensionUri;
        this._state = _state;
        this._currentResults = [];
        this._onDidUpdateResults = new vscode.EventEmitter();
        this.onDidUpdateResults = this._onDidUpdateResults.event;
        this._loadState();
    }
    get currentResults() {
        return this._currentResults;
    }
    resolveWebviewView(webviewView, context, _token) {
        this._view = webviewView;
        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [
                this._extensionUri
            ]
        };
        webviewView.webview.html = this._getHtmlForWebview(webviewView.webview);
        webviewView.webview.onDidReceiveMessage(data => {
            switch (data.type) {
                case 'openFile':
                    {
                        const uri = vscode.Uri.parse(data.uri);
                        const range = new vscode.Range(data.startLine, data.startCol, data.endLine, data.endCol);
                        vscode.window.showTextDocument(uri, { selection: range });
                        break;
                    }
                case 'scan':
                    {
                        const editor = vscode.window.activeTextEditor;
                        if (!editor) {
                            vscode.window.showWarningMessage('Please open a file first to scan it.');
                            return;
                        }
                        vscode.commands.executeCommand('secure-code.scan');
                        break;
                    }
                case 'login':
                    {
                        vscode.commands.executeCommand('secure-code.login');
                        break;
                    }
                case 'logout':
                    {
                        vscode.commands.executeCommand('secure-code.logout');
                        break;
                    }
                case 'ready':
                    {
                        if (this._currentResults.length > 0) {
                            webviewView.webview.postMessage({ type: 'updateResults', results: this._currentResults });
                        }
                        break;
                    }
                case 'syncState':
                    {
                        // Webview has state that extension doesn't (e.g. after reload)
                        if (data.results && this._currentResults.length === 0) {
                            this._currentResults = data.results;
                            this._saveState();
                            this._onDidUpdateResults.fire();
                        }
                        break;
                    }
            }
        });
    }
    updateResults(uri, diagnostics) {
        const seen = new Set();
        const uniqueDiagnostics = diagnostics.filter(d => {
            const key = `${d.range.start.line}:${d.message}`;
            if (seen.has(key)) {
                return false;
            }
            seen.add(key);
            return true;
        });
        const simpleDiagnostics = uniqueDiagnostics.map(d => ({
            message: d.message,
            severity: d.severity,
            startLine: d.range.start.line,
            startCol: d.range.start.character,
            endLine: d.range.end.line,
            endCol: d.range.end.character
        }));
        const existingIndex = this._currentResults.findIndex(r => r.uri === uri.toString());
        if (existingIndex >= 0) {
            this._currentResults[existingIndex] = { uri: uri.toString(), diagnostics: simpleDiagnostics };
        }
        else {
            this._currentResults.push({ uri: uri.toString(), diagnostics: simpleDiagnostics });
        }
        this._saveState();
        this._onDidUpdateResults.fire();
        if (this._view) {
            this._view.webview.postMessage({ type: 'updateResults', results: this._currentResults });
        }
    }
    clear() {
        this._currentResults = [];
        this._saveState();
        this._onDidUpdateResults.fire();
        if (this._view) {
            this._view.webview.postMessage({ type: 'updateResults', results: [] });
        }
    }
    _saveState() {
        this._state.update('scanResults', this._currentResults);
    }
    _loadState() {
        const saved = this._state.get('scanResults');
        if (saved) {
            this._currentResults = saved;
        }
    }
    _getHtmlForWebview(webview) {
        return `<!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; img-src 'self' https://raw.githubusercontent.com;">
            <title>Scan Results</title>
            <style>
                :root {
                    --container-paddding: 20px;
                    --input-padding-vertical: 6px;
                    --input-padding-horizontal: 4px;
                    --input-margin-vertical: 4px;
                    --input-margin-horizontal: 0;
                }

                body {
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
                    padding: 0;
                    margin: 0;
                    color: var(--vscode-foreground);
                    background-color: var(--vscode-editor-background);
                    overflow-x: hidden;
                }

                /* Scrollbar Styling */
                ::-webkit-scrollbar {
                    width: 8px;
                    height: 8px;
                }
                ::-webkit-scrollbar-thumb {
                    background: var(--vscode-scrollbarSlider-background);
                    border-radius: 4px;
                }
                ::-webkit-scrollbar-thumb:hover {
                    background: var(--vscode-scrollbarSlider-hoverBackground);
                }

                /* Animations */
                @keyframes fadeIn {
                    from { opacity: 0; transform: translateY(10px); }
                    to { opacity: 1; transform: translateY(0); }
                }

                @keyframes slideIn {
                    from { transform: translateX(20px); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }

                .fade-in {
                    animation: fadeIn 0.4s ease-out forwards;
                }

                /* Layout Containers */
                #dashboard-view, #details-view {
                    padding: 16px;
                    box-sizing: border-box;
                    width: 100%;
                }

                /* File Cards (Glassmorphism) */
                .file-card {
                    background: var(--vscode-editor-background);
                    border: 1px solid var(--vscode-widget-border);
                    border-radius: 12px;
                    padding: 16px;
                    margin-bottom: 12px;
                    cursor: pointer;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    transition: all 0.2s ease;
                    position: relative;
                    overflow: hidden;
                }

                .file-card:hover {
                    background: var(--vscode-list-hoverBackground);
                    border-color: var(--vscode-focusBorder);
                    transform: translateY(-2px);
                    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                }

                .file-info {
                    display: flex;
                    align-items: center;
                    gap: 12px;
                    overflow: hidden;
                }

                .file-icon img {
                    width: 20px;
                    height: 20px;
                    filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1));
                }

                .file-name {
                    font-weight: 600;
                    font-size: 14px;
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                    color: var(--vscode-foreground);
                }

                .file-counts {
                    display: flex;
                    gap: 6px;
                }

                /* Badges */
                .count-badge {
                    font-size: 11px;
                    padding: 2px 8px;
                    border-radius: 12px;
                    font-weight: 600;
                    min-width: 20px;
                    text-align: center;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }

                .count-badge.error {
                    background: linear-gradient(135deg, var(--vscode-editorError-foreground), #d32f2f);
                    color: white;
                }

                .count-badge.warning {
                    background: linear-gradient(135deg, var(--vscode-editorWarning-foreground), #f57c00);
                    color: white; /* Ensure readability */
                }

                /* Finding Cards */
                .card {
                    background: var(--vscode-editor-background);
                    border: 1px solid var(--vscode-widget-border);
                    border-radius: 10px;
                    padding: 16px;
                    margin-bottom: 16px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
                    transition: all 0.2s ease;
                    cursor: pointer;
                    position: relative;
                }

                .card:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 6px 16px rgba(0,0,0,0.1);
                    border-color: var(--vscode-focusBorder);
                }

                .card.error {
                    border-left: 4px solid var(--vscode-editorError-foreground);
                }

                .card.warning {
                    border-left: 4px solid var(--vscode-editorWarning-foreground);
                }

                .card-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 10px;
                }

                .severity-badge {
                    font-size: 10px;
                    padding: 3px 8px;
                    border-radius: 6px;
                    font-weight: 700;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }

                .severity-badge.error {
                    background-color: rgba(255, 82, 82, 0.15);
                    color: var(--vscode-editorError-foreground);
                    border: 1px solid rgba(255, 82, 82, 0.3);
                }

                .severity-badge.warning {
                    background-color: rgba(255, 171, 64, 0.15);
                    color: var(--vscode-editorWarning-foreground);
                    border: 1px solid rgba(255, 171, 64, 0.3);
                }

                .message {
                    font-size: 13px;
                    margin-bottom: 12px;
                    line-height: 1.5;
                    color: var(--vscode-foreground);
                }

                .line-info {
                    font-size: 11px;
                    color: var(--vscode-descriptionForeground);
                    display: flex;
                    align-items: center;
                    gap: 4px;
                }
                
                .line-info::before {
                    content: '';
                    display: inline-block;
                    width: 4px;
                    height: 4px;
                    border-radius: 50%;
                    background-color: var(--vscode-descriptionForeground);
                }

                /* Navigation Header */
                .nav-header {
                    display: flex;
                    align-items: center;
                    margin-bottom: 20px;
                    gap: 12px;
                    padding-bottom: 16px;
                    border-bottom: 1px solid var(--vscode-widget-border);
                    position: sticky;
                    top: 0;
                    background: var(--vscode-editor-background);
                    z-index: 10;
                    backdrop-filter: blur(8px); /* Glass effect */
                }

                .back-btn {
                    background: transparent;
                    border: none;
                    color: var(--vscode-textLink-foreground);
                    cursor: pointer;
                    font-size: 14px;
                    padding: 6px 12px;
                    border-radius: 6px;
                    display: flex;
                    align-items: center;
                    gap: 6px;
                    transition: background 0.2s;
                    font-weight: 500;
                }

                .back-btn:hover {
                    background: rgba(128, 128, 128, 0.1);
                    text-decoration: none;
                }

                .current-file-title {
                    font-weight: 700;
                    font-size: 16px;
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                }

                /* Empty State */
                .empty-state {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    text-align: center;
                    margin-top: 60px;
                    padding: 20px;
                    animation: fadeIn 0.6s ease-out;
                }
                
                .empty-icon {
                    font-size: 48px;
                    margin-bottom: 16px;
                    opacity: 0.8;
                }

                .empty-state h3 {
                    font-size: 18px;
                    font-weight: 600;
                    margin: 0 0 8px 0;
                    color: var(--vscode-foreground);
                }

                .empty-state p {
                    font-size: 13px;
                    color: var(--vscode-descriptionForeground);
                    margin: 0 0 24px 0;
                    max-width: 240px;
                    line-height: 1.5;
                }

                /* Buttons */
                .btn {
                    background: var(--vscode-button-background);
                    color: var(--vscode-button-foreground);
                    border: none;
                    padding: 10px 20px;
                    border-radius: 6px;
                    cursor: pointer;
                    font-size: 13px;
                    font-weight: 500;
                    margin-top: 12px;
                    width: 100%;
                    transition: all 0.2s;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }

                .btn:hover {
                    background: var(--vscode-button-hoverBackground);
                    transform: translateY(-1px);
                    box-shadow: 0 4px 8px rgba(0,0,0,0.2);
                }

                .btn:active {
                    transform: translateY(0);
                }

                .btn-secondary {
                    background: transparent;
                    color: var(--vscode-foreground);
                    border: 1px solid var(--vscode-button-border, rgba(128,128,128,0.3));
                    margin-top: 12px;
                }

                .btn-secondary:hover {
                    background: var(--vscode-list-hoverBackground);
                    border-color: var(--vscode-focusBorder);
                }

            </style>
        </head>
        <body>
            <div id="dashboard-view">
                <div id="file-list"></div>
            </div>

            <div id="details-view" style="display: none;">
                <div class="nav-header">
                    <button class="back-btn" id="back-btn">
                        <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
                            <path fill-rule="evenodd" clip-rule="evenodd" d="M10.5303 3.46967C10.8232 3.76256 10.8232 4.23744 10.5303 4.53033L7.06066 8L10.5303 11.4697C10.8232 11.7626 10.8232 12.2374 10.5303 12.5303C10.2374 12.8232 9.76256 12.8232 9.46967 12.5303L5.46967 8.53033C5.17678 8.23744 5.17678 7.76256 5.46967 7.46967L9.46967 3.46967C9.76256 3.17678 10.2374 3.17678 10.5303 3.46967Z"/>
                        </svg>
                        Back
                    </button>
                    <span class="current-file-title" id="details-title"></span>
                </div>
                <div id="findings-list"></div>
            </div>
            
            <div id="empty-state" class="empty-state">
                <div class="empty-icon">🛡️</div>
                <h3>Secure Your Code</h3>
                <p>No vulnerabilities found yet. Scan your current file to get started.</p>
                <button class="btn" id="scan-btn">Scan Current File</button>
                <button class="btn btn-secondary" id="login-btn">Login / Activate</button>
            </div>

            <script>
                const vscode = acquireVsCodeApi();
                
                const dashboardView = document.getElementById('dashboard-view');
                const fileList = document.getElementById('file-list');
                const detailsView = document.getElementById('details-view');
                const findingsList = document.getElementById('findings-list');
                const detailsTitle = document.getElementById('details-title');
                const emptyState = document.getElementById('empty-state');

                let currentResults = [];
                let activeFileUri = null;

                vscode.postMessage({ type: 'ready' });

                document.getElementById('scan-btn').onclick = function() {
                    vscode.postMessage({ type: 'scan' });
                };

                document.getElementById('login-btn').onclick = function() {
                    vscode.postMessage({ type: 'login' });
                };

                document.getElementById('back-btn').onclick = function() {
                    showDashboard();
                };

                const previousState = vscode.getState();
                if (previousState && previousState.results) {
                    currentResults = previousState.results;
                    renderDashboard();
                    // Sync state back to extension host
                    vscode.postMessage({ type: 'syncState', results: currentResults });
                }

                window.addEventListener('message', function(event) {
                    const message = event.data;
                    if (message.type === 'updateResults') {
                        currentResults = message.results;
                        vscode.setState({ results: currentResults });
                        renderDashboard();
                        
                        if (activeFileUri) {
                            const fileResult = currentResults.find(function(r) { return r.uri === activeFileUri; });
                            if (fileResult && fileResult.diagnostics.length > 0) {
                                showDetails(fileResult, false);
                            } else {
                                showDashboard();
                            }
                        }
                    }
                });

                function summarizeMessage(fullMessage) {
                    const lines = fullMessage.split('\\n');
                    const firstLine = lines[0].trim();
                    const patterns = [
                        { regex: /SQL injection/i, summary: 'Potential SQL Injection' },
                        { regex: /XSS|cross-site scripting/i, summary: 'Cross-Site Scripting (XSS)' },
                        { regex: /hardcoded (password|secret|key|token)/i, summary: 'Hardcoded Secret' },
                        { regex: /insecure (random|crypto)/i, summary: 'Weak Cryptography' },
                        { regex: /path traversal/i, summary: 'Path Traversal' },
                        { regex: /command injection/i, summary: 'Command Injection' },
                        { regex: /CSRF|cross-site request forgery/i, summary: 'CSRF Vulnerability' },
                        { regex: /eval\\(/i, summary: 'Unsafe Eval Usage' },
                        { regex: /open redirect/i, summary: 'Open Redirect' }
                    ];
                    for (let i = 0; i < patterns.length; i++) {
                        if (patterns[i].regex.test(fullMessage)) return patterns[i].summary;
                    }
                    return firstLine.length > 60 ? firstLine.substring(0, 57) + '...' : firstLine;
                }

                function showDashboard() {
                    activeFileUri = null;
                    detailsView.style.display = 'none';
                    dashboardView.style.display = 'block';
                    if (currentResults.length === 0) {
                        emptyState.style.display = 'flex';
                        dashboardView.style.display = 'none';
                    } else {
                        emptyState.style.display = 'none';
                    }
                }

                function showDetails(fileResult, switchView) {
                    if (switchView === undefined) switchView = true;
                    activeFileUri = fileResult.uri;
                    
                    if (switchView) {
                        dashboardView.style.display = 'none';
                        emptyState.style.display = 'none';
                        detailsView.style.display = 'block';
                    }
                    
                    const filename = fileResult.uri.split('/').pop();
                    detailsTitle.textContent = filename;
                    
                    findingsList.innerHTML = '';
                    let delay = 0;
                    fileResult.diagnostics.forEach(function(diag) {
                        const card = document.createElement('div');
                        const severityClass = diag.severity === 0 ? 'error' : 'warning';
                        const severityLabel = diag.severity === 0 ? 'Critical' : 'Warning';
                        const summary = summarizeMessage(diag.message);
                        
                        card.className = 'card ' + severityClass + ' fade-in';
                        card.style.animationDelay = delay + 'ms';
                        delay += 50;
                        
                        card.onclick = function() {
                            vscode.postMessage({
                                type: 'openFile',
                                uri: fileResult.uri,
                                startLine: diag.startLine,
                                startCol: diag.startCol,
                                endLine: diag.endLine,
                                endCol: diag.endCol
                            });
                        };

                        card.innerHTML = 
                            '<div class="card-header">' +
                                '<span class="severity-badge ' + severityClass + '">' + severityLabel + '</span>' +
                            '</div>' +
                            '<div class="message">' + summary + '</div>' +
                            '<div class="line-info">Line ' + (diag.startLine + 1) + '</div>';
                        findingsList.appendChild(card);
                    });
                }

                function renderDashboard() {
                    fileList.innerHTML = '';
                    let hasAnyIssues = false;
                    let delay = 0;

                    currentResults.forEach(function(fileResult) {
                        if (fileResult.diagnostics.length === 0) return;
                        hasAnyIssues = true;

                        const uri = fileResult.uri;
                        const filename = uri.split('/').pop();
                        
                        let errorCount = 0;
                        let warningCount = 0;
                        fileResult.diagnostics.forEach(function(d) {
                            if (d.severity === 0) errorCount++;
                            else warningCount++;
                        });

                        function getFileIcon(filename) {
                            const ext = filename.split('.').pop().toLowerCase();
                            const baseUrl = 'https://raw.githubusercontent.com/PKief/vscode-material-icon-theme/main/icons/';
                            const iconMap = {
                                'js': 'javascript.svg', 'ts': 'typescript.svg', 'py': 'python.svg',
                                'java': 'java.svg', 'html': 'html.svg', 'css': 'css.svg',
                                'json': 'json.svg', 'md': 'markdown.svg', 'go': 'go.svg',
                                'rs': 'rust.svg', 'php': 'php.svg', 'rb': 'ruby.svg',
                                'c': 'c.svg', 'cpp': 'cpp.svg', 'h': 'cpp.svg'
                            };
                            const iconName = iconMap[ext] || 'file.svg';
                            return '<img src="' + baseUrl + iconName + '" alt="' + ext + '" />';
                        }

                        const fileIcon = getFileIcon(filename);
                        const fileCard = document.createElement('div');
                        fileCard.className = 'file-card fade-in';
                        fileCard.style.animationDelay = delay + 'ms';
                        delay += 50;
                        
                        fileCard.onclick = function() { showDetails(fileResult); };

                        let badgesHtml = '';
                        if (errorCount > 0) {
                            badgesHtml += '<span class="count-badge error">' + errorCount + '</span>';
                        }
                        if (warningCount > 0) {
                            badgesHtml += '<span class="count-badge warning">' + warningCount + '</span>';
                        }

                        fileCard.innerHTML = 
                            '<div class="file-info">' +
                                '<span class="file-icon">' + fileIcon + '</span>' +
                                '<span class="file-name">' + filename + '</span>' +
                            '</div>' +
                            '<div class="file-counts">' + badgesHtml + '</div>';
                        fileList.appendChild(fileCard);
                    });

                    if (!hasAnyIssues) {
                        emptyState.style.display = 'flex';
                        dashboardView.style.display = 'none';
                        detailsView.style.display = 'none';
                    } else {
                        emptyState.style.display = 'none';
                        dashboardView.style.display = 'block';
                        detailsView.style.display = 'none';
                    }
                }
            </script>
        </body>
        </html>`;
    }
}
exports.ScanResultsWebviewProvider = ScanResultsWebviewProvider;
ScanResultsWebviewProvider.viewType = 'secure-code.scanResultsWebview';
//# sourceMappingURL=scanResultsWebviewProvider.js.map