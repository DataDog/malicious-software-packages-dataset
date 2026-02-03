"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = require("vscode");
const login_1 = require("./commands/login");
const logout_1 = require("./commands/logout");
const scanCurrentFile_1 = require("./commands/scanCurrentFile");
const scanResultsWebviewProvider_1 = require("./views/scanResultsWebviewProvider");
const decorationManager_1 = require("./views/decorationManager");
function activate(context) {
    console.log('Congratulations, your extension "SecureCode" is now active!');
    (0, scanCurrentFile_1.initDiagnostics)(context);
    // 1. Instantiate DecorationManager
    const decorationManager = new decorationManager_1.DecorationManager();
    // 2. Create and Register Webview View Provider
    const scanResultsProvider = new scanResultsWebviewProvider_1.ScanResultsWebviewProvider(context.extensionUri, context.workspaceState);
    context.subscriptions.push(vscode.window.registerWebviewViewProvider(scanResultsWebviewProvider_1.ScanResultsWebviewProvider.viewType, scanResultsProvider));
    // 3. Restore Decorations on Activation
    const restoreDecorations = () => {
        const editor = vscode.window.activeTextEditor;
        console.log('SecureCode: restoreDecorations called. Editor:', editor ? 'Found' : 'None');
        if (editor) {
            const currentUri = editor.document.uri.toString();
            const results = scanResultsProvider.currentResults;
            console.log('SecureCode: Current URI:', currentUri);
            console.log('SecureCode: Stored Results:', JSON.stringify(results.map(r => r.uri)));
            const fileResult = results.find(r => r.uri === currentUri);
            if (fileResult) {
                console.log(`SecureCode: Found ${fileResult.diagnostics.length} diagnostics for current file. Restoring...`);
                // Re-construct diagnostics from saved state
                const diagnostics = fileResult.diagnostics.map((d) => {
                    const range = new vscode.Range(d.startLine, d.startCol, d.endLine, d.endCol);
                    const severity = d.severity === 0 ? vscode.DiagnosticSeverity.Error : vscode.DiagnosticSeverity.Warning;
                    return new vscode.Diagnostic(range, d.message, severity);
                });
                decorationManager.setDecorations(editor, diagnostics);
            }
            else {
                console.log('SecureCode: No saved results for this file.');
                decorationManager.clear(editor);
            }
        }
    };
    // Initial restore
    setTimeout(restoreDecorations, 1000); // Keep timeout as fallback
    // Restore when provider updates results (e.g. after sync)
    context.subscriptions.push(scanResultsProvider.onDidUpdateResults(() => {
        console.log('SecureCode: Received update from provider. Restoring decorations...');
        restoreDecorations();
    }));
    // Restore on editor change
    context.subscriptions.push(vscode.window.onDidChangeActiveTextEditor(() => {
        restoreDecorations();
    }));
    // 6. Register Commands
    let loginDisposable = vscode.commands.registerCommand('secure-code.login', (0, login_1.loginCommand)(context));
    let logoutDisposable = vscode.commands.registerCommand('secure-code.logout', (0, logout_1.logoutCommand)(context));
    let scanDisposable = vscode.commands.registerCommand('secure-code.scan', (0, scanCurrentFile_1.scanCommand)(context, scanResultsProvider, decorationManager));
    let clearDisposable = vscode.commands.registerCommand('secure-code.clearResults', () => {
        scanResultsProvider.clear();
        (0, scanCurrentFile_1.clearDiagnostics)(); // Clear VS Code Problems
        const editor = vscode.window.activeTextEditor;
        if (editor) {
            decorationManager.clear(editor);
        }
        vscode.window.showInformationMessage('Scan results cleared');
    });
    context.subscriptions.push(loginDisposable);
    context.subscriptions.push(logoutDisposable);
    context.subscriptions.push(scanDisposable);
    context.subscriptions.push(clearDisposable);
}
function deactivate() { }
//# sourceMappingURL=extension.js.map