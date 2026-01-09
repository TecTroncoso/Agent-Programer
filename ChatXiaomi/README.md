# Xiaomi AI Studio Client

A reverse-engineered Python client for [Xiaomi AI Studio](https://aistudio.xiaomimimo.com/) that allows you to interact with the `mimo-v2-flash-studio` model directly from your terminal or scripts.

## Features

- **Direct API Access**: Bypasses the web interface to communicate with Xiaomi's backend.
- **Automated Authentication**: Uses a headless browser (`nodriver`) to handle Google OAuth login automatically.
- **Session Persistence**: Saves cookies and tokens to avoid repeated logins (`data/browser_profile`).
- **Streaming Chat**: Real-time response streaming in the terminal with a beautiful UI.
- **Interactive & Single Prompt Modes**: Chat interactively or send one-off commands.

## Installation

1.  **Clone the repository**:
    ```bash
    git clone <your-repo-url>
    cd ChatXiaomi
    ```

2.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure Credentials**:
    Create a `.env` file in `data/.env` (or rename the existing one) with your Google account credentials.
    > **Note**: This project uses `KIMI_EMAIL` and `KIMI_PASSWORD` variable names for legacy compatibility, but they refer to your **Google Account** used for Xiaomi AI Studio.

    `data/.env`:
    ```env
    KIMI_EMAIL=your_email@gmail.com
    KIMI_PASSWORD=your_password
    BROWSER_PATH=  # Optional: Custom path to chrome.exe if not found automatically
    ```

## Usage

### Interactive Chat
Start a conversation in your terminal:
```bash
python main.py
```

### Single Prompt
Run a single query and get the output:
```bash
python main.py "Explain quantum computing in one sentence"
```

## How It Works

1.  The script checks for a valid session in `data/browser_profile`.
2.  If the session is expired or missing, it launches a controlled Chrome browser.
3.  It automates the login process using your Google credentials.
4.  Once logged in, it extracts the `serviceToken` and other cookies.
5.  Uses these credentials to communicate with the `https://aistudio.xiaomimimo.com/open-apis/bot/chat` endpoint.

## Troubleshooting

-   **Browser Profile**: If you get stuck in a login loop, try deleting the `data/browser_profile` folder and `data/last_login.txt` to start fresh.
-   **Login Errors**: Sometimes the login page might timeout or show `ERR_INVALID_RESPONSE`. The script attempts to handle this, but you may need to run it again.
-   **Chrome**: Google Chrome must be installed on your system.

## Disclaimer

This is an unofficial client for educational and research purposes. It is not affiliated with Xiaomi. Use responsibly and respect the service's Terms of Use.
