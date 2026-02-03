"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.scanCode = exports.verifyOtp = exports.sendOtp = exports.checkEmail = void 0;
const axios_1 = require("axios");
// Assume running locally for MVP, user might need to configure this
const API_URL = 'https://ca458c98fbe7.ngrok-free.app';
const checkEmail = async (email) => {
    const response = await axios_1.default.post(`${API_URL}/auth/check-email`, { email });
    return response.data;
};
exports.checkEmail = checkEmail;
const sendOtp = async (email) => {
    const response = await axios_1.default.post(`${API_URL}/auth/send-otp`, { email });
    return response.data;
};
exports.sendOtp = sendOtp;
const verifyOtp = async (email, otp) => {
    const response = await axios_1.default.post(`${API_URL}/auth/verify-otp`, { email, otp });
    return response.data;
};
exports.verifyOtp = verifyOtp;
const scanCode = async (code, language, token) => {
    const response = await axios_1.default.post(`${API_URL}/scan`, { code, language }, { headers: { Authorization: `Bearer ${token}` } });
    return response.data;
};
exports.scanCode = scanCode;
//# sourceMappingURL=apiClient.js.map