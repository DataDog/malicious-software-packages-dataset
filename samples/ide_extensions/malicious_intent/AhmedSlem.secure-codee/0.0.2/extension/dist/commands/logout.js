"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.logoutCommand = void 0;
const vscode = require("vscode");
const tokenStore_1 = require("../auth/tokenStore");
const logoutCommand = (context) => async () => {
    (0, tokenStore_1.clearToken)(context);
    vscode.window.showInformationMessage('Logged out successfully.');
};
exports.logoutCommand = logoutCommand;
//# sourceMappingURL=logout.js.map