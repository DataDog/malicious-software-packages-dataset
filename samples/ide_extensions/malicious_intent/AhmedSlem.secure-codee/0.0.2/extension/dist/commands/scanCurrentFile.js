"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.scanCommand = exports.clearDiagnostics = exports.initDiagnostics = void 0;
const vscode = require("vscode");
const apiClient_1 = require("../services/apiClient");
const tokenStore_1 = require("../auth/tokenStore");
const findingUtils_1 = require("../utils/findingUtils");
let diagnosticCollection;
const initDiagnostics = (context) => {
    diagnosticCollection = vscode.languages.createDiagnosticCollection('secure-code');
    context.subscriptions.push(diagnosticCollection);
};
exports.initDiagnostics = initDiagnostics;
const clearDiagnostics = () => {
    if (diagnosticCollection) {
        diagnosticCollection.clear();
    }
};
exports.clearDiagnostics = clearDiagnostics;
const scanningFiles = new Set();
const scanCommand = (context, provider, decorationManager) => async () => {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showErrorMessage('No active editor');
        return;
    }
    const token = (0, tokenStore_1.getToken)(context);
    if (!token) {
        vscode.window.showErrorMessage('Please login first using "SecureCode: Login"');
        return;
    }
    const document = editor.document;
    const fileUri = document.uri.toString();
    if (scanningFiles.has(fileUri)) {
        vscode.window.showInformationMessage('Scan already in progress for this file.');
        return;
    }
    scanningFiles.add(fileUri);
    const code = document.getText();
    const language = document.languageId;
    try {
        const result = await vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: "SecureCode: Scanning...",
            cancellable: false
        }, async (progress) => {
            progress.report({ message: "Analyzing code security..." });
            return await (0, apiClient_1.scanCode)(code, language, token);
        });
        const diagnostics = [];
        if (result.findings) {
            // Deduplicate findings by line and message summary
            const seen = new Set();
            const uniqueFindings = result.findings.filter((finding) => {
                const startLine = finding.start.line - 1;
                const message = finding.extra.message || finding.extra.lines;
                const shortMsg = (0, findingUtils_1.getShortMessage)(message);
                const key = `${startLine}:${shortMsg}`;
                console.log(`SecureCode: Dedupe Key: ${key}`);
                if (seen.has(key)) {
                    console.log(`SecureCode: Duplicate found for key: ${key}`);
                    return false;
                }
                seen.add(key);
                return true;
            });
            for (const finding of uniqueFindings) {
                // Semgrep output mapping
                const startLine = finding.start.line - 1;
                const startCol = finding.start.col - 1;
                const endLine = finding.end.line - 1;
                const endCol = finding.end.col - 1;
                const range = new vscode.Range(startLine, startCol, endLine, endCol);
                const message = finding.extra.message || finding.extra.lines;
                const severity = finding.extra.severity === 'ERROR' ? vscode.DiagnosticSeverity.Error : vscode.DiagnosticSeverity.Warning;
                const diagnostic = new vscode.Diagnostic(range, message, severity);
                diagnostic.source = 'SecureCode';
                diagnostics.push(diagnostic);
            }
        }
        diagnosticCollection.set(document.uri, diagnostics);
        provider.updateResults(document.uri, diagnostics);
        // Apply decorations
        console.log(`Applying decorations for ${diagnostics.length} diagnostics`);
        decorationManager.setDecorations(editor, diagnostics);
        if (result.remainingScans !== undefined) {
            vscode.window.showInformationMessage(`Scan complete. Found ${diagnostics.length} issues. Remaining scans: ${result.remainingScans}`);
        }
        else {
            vscode.window.showInformationMessage(`Scan complete. Found ${diagnostics.length} issues.`);
        }
    }
    catch (err) {
        if (err.response && err.response.status === 429) {
            vscode.window.showErrorMessage('Daily limit reached. Upgrade your plan to continue scanning.');
        }
        else if (err.response && (err.response.status === 401 || err.response.status === 403)) {
            vscode.window.showErrorMessage('Session expired. Please login again.');
        }
        else {
            vscode.window.showErrorMessage('Scan failed: ' + (err.response?.data?.error || err.message));
        }
    }
    finally {
        scanningFiles.delete(fileUri);
    }
};
exports.scanCommand = scanCommand;
//# sourceMappingURL=scanCurrentFile.js.map