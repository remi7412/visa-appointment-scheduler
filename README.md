# visa-appointment-scheduler 🤖

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)

An advanced, fully-unattended automation framework designed to autonomously monitor and secure earlier US Visa interview slots. Built with enterprise-grade resilience, it bypasses complex security measures, continuously monitors availability, and books appointments with zero human intervention.

---

## 🌟 Key Features

- **100% Autonomous Operation**: Once launched, the bot handles everything. It logs in, bypasses waiting rooms, answers security questions, and begins monitoring.
- **Advanced Security Evasion**:
  - Automatically bypasses **Cloudflare** waiting queues.
  - Dynamically solves Microsoft B2C randomized **Security Questions**.
  - Evades hidden honeypot traps designed to catch bots.
- **Intelligent Recovery System**: Never crashes due to session timeouts. If the server kicks the session or throws an error, the bot gracefully restarts the browser, re-authenticates, and resumes monitoring.
- **Smart Date Matching**: Configurable target date ranges ensure the bot *only* books appointments that perfectly match your desired schedule.
- **Rate Limit Protection**: Employs randomized, human-like delays and automatically pauses when the US Visa server enforces "Too Many Requests" limits.
- **Real-Time Telegram Alerts**: Instantly sends a push notification directly to your phone the exact second an appointment is secured.

---

## ⚙️ Configuration (`config.json`)

All operational parameters are controlled via the `config.json` file. Please ensure this is correctly filled out before starting the system.

### 1. Credentials & Security Answers
Provide your login details and the exact, lowercase answers to your account's security questions.
```json
"credentials": {
  "username": "your.email@example.com",
  "password": "YourPassword123",
  "security_answers": {
    "pet": "cat",
    "road": "rat",
    "street": "sat",
    "work": "rain"
  }
}
```

### 2. Target Locations
List the specific VAC cities you want the bot to monitor, in order of priority.
```json
"cities": [
  "CHENNAI VAC",
  "HYDERABAD VAC",
  "KOLKATA VAC",
  "MUMBAI VAC",
  "NEW DELHI VAC"
]
```

### 3. Target Date Ranges
Specify the exact month and date ranges acceptable for your appointment.
```json
"dates": [
  {
    "year": "2026",
    "month": "6",
    "range": "10-30"
  }
]
```

### 4. Advanced Settings (`wait_times`)
You can control how fast the bot runs and how it reacts to Cloudflare bans.
```json
"wait_times": {
  "rate_limit_wait_time": 30.0
}
```
*Tip: Set `rate_limit_wait_time` to 15-30 seconds if you are using WebShare proxies. The bot will instantly rotate proxies when blocked. If using a single home IP, set it to 600 (10 minutes).*

### 5. Telegram Integration (Optional)
To receive instant booking alerts to your phone:
1. Send a message to `@BotFather` on Telegram to generate a `bot_token`.
2. Send a message to `@userinfobot` on Telegram to get your 9-digit `chat_id`.
```json
"telegram": {
  "enabled": true,
  "bot_token": "YOUR_BOT_TOKEN",
  "chat_id": "YOUR_CHAT_ID"
}
```

---

## 🚀 How to Run

### Step 1: Install Python
Ensure that you have Python 3.10 or newer installed on your computer. During the Python installation, **make sure you check the box that says "Add Python to PATH"**.

### Step 2: Run the Bot
Simply double-click the **`run_bot.bat`** file located in this folder. 
This script will automatically:
1. Setup the Python environment.
2. Install all required dependencies from `requirements.txt`.
3. Launch the local server and open the Web Dashboard in your browser (`http://127.0.0.1:5000`).

### Step 3: Configure and Start
1. Enter your credentials, select your Target Cities, and add your desired Date ranges using the intuitive interface.
2. If you want to use proxies, add them to the Proxies field (format: `http://user:pass@ip:port`).
3. Click **Save Configuration**.
4. Click **Start Bot**.

### What to Expect:
- You will see the bot's live logs streaming directly into your web browser dashboard.
- The bot runs completely in the background. If you are using proxies, it will automatically handle Cloudflare, login, and monitoring invisibly.
- **Troubleshooting Proxies**: If the logs show the bot is trapped in a Cloudflare loop, your proxy IPs are likely blocked. Try clearing the Proxies field and running on your local internet to test. Use high-quality residential proxies for production.

---

## 🛠️ Troubleshooting

- **Browser Closes Immediately**: Ensure you have not forcefully stopped the script while it was updating the background driver. If it hangs, run `run_bot.bat` again.
- **Log Files**: All activity is meticulously recorded in the `logs/` directory. Check here first if you want to see exactly what decisions the bot is making behind the scenes.
- **Visual Evidence**: If the bot encounters a fatal error or is kicked by the server, it takes a screenshot and saves it to the `screenshots/` directory for debugging purposes.

---

### Disclaimer
*This automation software is provided for educational purposes. Users are solely responsible for ensuring their use of this software complies with the Terms of Service of the target website. The developers assume no liability for account suspensions or bans.*
