"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.DecorationManager = void 0;
const vscode = require("vscode");
const findingUtils_1 = require("../utils/findingUtils");
class DecorationManager {
    constructor() {
        // Error Decoration Type
        this.errorDecorationType = vscode.window.createTextEditorDecorationType({
            backgroundColor: 'rgba(255, 82, 82, 0.1)', // Light red background for the range
            border: '1px solid rgba(255, 82, 82, 0.3)',
            borderRadius: '3px',
            overviewRulerColor: '#ff5252',
            overviewRulerLane: vscode.OverviewRulerLane.Right,
            after: {
                margin: '0 0 0 1em',
                textDecoration: 'none'
            }
        });
        // Warning Decoration Type
        this.warningDecorationType = vscode.window.createTextEditorDecorationType({
            backgroundColor: 'rgba(255, 171, 64, 0.1)', // Light orange background for the range
            border: '1px solid rgba(255, 171, 64, 0.3)',
            borderRadius: '3px',
            overviewRulerColor: '#ffab40',
            overviewRulerLane: vscode.OverviewRulerLane.Right,
            after: {
                margin: '0 0 0 1em',
                textDecoration: 'none'
            }
        });
    }
    setDecorations(editor, diagnostics) {
        const errorDecorations = [];
        const warningDecorations = [];
        for (const diagnostic of diagnostics) {
            const isError = diagnostic.severity === vscode.DiagnosticSeverity.Error;
            const color = isError ? '#ff5252' : '#ffab40';
            const bgColor = isError ? 'rgba(255, 82, 82, 0.15)' : 'rgba(255, 171, 64, 0.15)';
            const borderColor = isError ? 'rgba(255, 82, 82, 0.5)' : 'rgba(255, 171, 64, 0.5)';
            const shortMsg = (0, findingUtils_1.getShortMessage)(diagnostic.message);
            const decoration = {
                range: diagnostic.range, // Highlight the actual range
                hoverMessage: new vscode.MarkdownString(`**${isError ? 'Error' : 'Warning'}**: ${diagnostic.message}`),
                renderOptions: {
                    after: {
                        contentText: ` ${shortMsg} `,
                        color: color,
                        backgroundColor: bgColor,
                        border: `1px solid ${borderColor}`,
                        fontWeight: 'bold',
                        fontStyle: 'normal'
                    }
                }
            };
            if (isError) {
                errorDecorations.push(decoration);
            }
            else {
                warningDecorations.push(decoration);
            }
        }
        editor.setDecorations(this.errorDecorationType, errorDecorations);
        editor.setDecorations(this.warningDecorationType, warningDecorations);
    }
    clear(editor) {
        editor.setDecorations(this.errorDecorationType, []);
        editor.setDecorations(this.warningDecorationType, []);
    }
}
exports.DecorationManager = DecorationManager;
//# sourceMappingURL=decorationManager.js.map