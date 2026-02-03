"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.loginCommand = void 0;
const vscode = require("vscode");
const apiClient_1 = require("../services/apiClient");
const tokenStore_1 = require("../auth/tokenStore");
const axios_1 = require("axios");
const loginCommand = (context) => async () => {
    const existingToken = (0, tokenStore_1.getToken)(context);
    if (existingToken) {
        const selection = await vscode.window.showInformationMessage('You are already logged in.', 'Logout', 'Cancel');
        if (selection === 'Logout') {
            vscode.commands.executeCommand('secure-code.logout');
        }
        return;
    }
    const email = await vscode.window.showInputBox({
        placeHolder: 'Enter your email',
        prompt: 'Login to SecureCode',
        ignoreFocusOut: true
    });
    if (!email)
        return;
    try {
        vscode.window.showInformationMessage(`Checking account for ${email}...`);
        // 1. Check if user exists
        try {
            await (0, apiClient_1.checkEmail)(email);
        }
        catch (err) {
            if (axios_1.default.isAxiosError(err) && err.response) {
                if (err.response.status === 404 || (err.response.data.error && err.response.data.error.includes('Account not found'))) {
                    const selection = await vscode.window.showErrorMessage('Account not found.', 'Create Account');
                    if (selection === 'Create Account') {
                        vscode.env.openExternal(vscode.Uri.parse('https://securecode.contentkit.studio'));
                    }
                    return;
                }
            }
            throw err;
        }
        // 2. If exists, send OTP
        vscode.window.showInformationMessage(`Account found. Sending OTP to ${email}...`);
        await (0, apiClient_1.sendOtp)(email);
        const otp = await vscode.window.showInputBox({
            placeHolder: 'Enter OTP sent to your email',
            prompt: 'Verify OTP',
            ignoreFocusOut: true
        });
        if (!otp)
            return;
        vscode.window.showInformationMessage('Verifying OTP...');
        const { token, plan } = await (0, apiClient_1.verifyOtp)(email, otp);
        (0, tokenStore_1.setToken)(context, token, plan);
        vscode.window.showInformationMessage(`Logged in successfully as ${email} (${plan} plan)`);
    }
    catch (err) {
        if (axios_1.default.isAxiosError(err) && err.response) {
            const errorMessage = err.response.data.error || err.message;
            vscode.window.showErrorMessage(`Login failed: ${errorMessage}`);
        }
        else {
            vscode.window.showErrorMessage(`Login failed: ${err.message}`);
        }
    }
};
exports.loginCommand = loginCommand;
//# sourceMappingURL=login.js.map