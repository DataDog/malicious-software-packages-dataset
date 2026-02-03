# SecureCode - Security Scanner

SecureCode helps you identify and fix security vulnerabilities in your code directly within VS Code using robust rule-based scanning.

## Features

- **Manual Security Scanning**: Trigger scans on demand to detect vulnerabilities in your currently active file.
- **Detailed Reports**: Get clear explanations of vulnerabilities including severity levels to prioritize fixes.
- **Secure Authentication**: Log in securely to access scanning features.
- **AI-Powered Analysis**: (Coming Soon) Uses advanced AI models to understand code context and find complex issues.

## How to Use

1.  **Login**: Open the Command Palette (`Ctrl+Shift+P` / `Cmd+Shift+P`) and run `SecureCode: Login / Activate`.
2.  **Open File**: Navigate to the file you want to analyze.
3.  **Scan**: Run `SecureCode: Scan Current File` from the Command Palette or click the play icon in the SecureCode sidebar.
4.  **Review**: Vulnerabilities will be highlighted in your code. hover over them for details or view the full list in the "Scan Results" sidebar.

## Requirements

- An active internet connection.
- You must log in to the SecureCode service to use the scanning features.

## Extension Settings

This extension contributes the following settings:

* `secure-code.enable`: Enable/disable the extension.
* `secure-code.apiUrl`: URL of the SecureCode API (default: production).

## Known Issues

- Large files may take longer to scan.

## Release Notes

### 0.0.2
- Updated publisher information.
- Refined security scanning description.

### 0.0.1
Initial release of SecureCode.
