"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.clearToken = exports.getPlan = exports.getToken = exports.setToken = void 0;
const TOKEN_KEY = 'secure_code_token';
const PLAN_KEY = 'secure_code_plan';
const setToken = (context, token, plan) => {
    context.globalState.update(TOKEN_KEY, token);
    context.globalState.update(PLAN_KEY, plan);
};
exports.setToken = setToken;
const getToken = (context) => {
    return context.globalState.get(TOKEN_KEY);
};
exports.getToken = getToken;
const getPlan = (context) => {
    return context.globalState.get(PLAN_KEY);
};
exports.getPlan = getPlan;
const clearToken = (context) => {
    context.globalState.update(TOKEN_KEY, undefined);
    context.globalState.update(PLAN_KEY, undefined);
};
exports.clearToken = clearToken;
//# sourceMappingURL=tokenStore.js.map