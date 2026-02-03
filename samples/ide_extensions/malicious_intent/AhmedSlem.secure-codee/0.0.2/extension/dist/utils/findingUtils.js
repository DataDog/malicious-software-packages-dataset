"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.getShortMessage = getShortMessage;
function getShortMessage(message) {
    const lines = message.split('\n');
    let summary = lines[0];
    // Map common findings to short, punchy labels
    if (summary.match(/SQL injection/i))
        return 'SQL Injection';
    if (summary.match(/XSS|cross-site scripting/i))
        return 'XSS';
    if (summary.match(/hardcoded (password|secret|key|token)/i))
        return 'Hardcoded Secret';
    if (summary.match(/insecure (random|crypto)/i))
        return 'Weak Crypto';
    if (summary.match(/path traversal/i))
        return 'Path Traversal';
    if (summary.match(/command injection/i))
        return 'Command Injection';
    if (summary.match(/CSRF|cross-site request forgery/i))
        return 'CSRF';
    if (summary.match(/eval\(/i))
        return 'Unsafe Eval';
    if (summary.match(/open redirect/i))
        return 'Open Redirect';
    return summary.length > 25 ? summary.substring(0, 22) + '...' : summary;
}
//# sourceMappingURL=findingUtils.js.map