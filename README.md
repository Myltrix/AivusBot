<table>
  <tr>
    <td width="35%">
      <img src="AivusBot.png" alt="AIBot" width="100%" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.2);">
    </td>
    <td style="padding-left: 30px;">
      <h1 style="color: #d4a574; margin-top: 0;">AivusBot</h1>
      <p style="font-size: 16px; line-height: 1.6; color: #333;">
        AivusBot is a simple Telegram bot that allows users to communicate with AI. It responds to messages, maintains conversations, and can be used as a personal assistant.
      </p>
      <p style="font-size: 16px;">
        <strong style="color: #2a7de1;">Bot:</strong><br>
        <a href="https://t.me/AivusBot" target="_blank" style="color: #2a7de1; font-weight: bold; text-decoration: none; font-size: 18px;">
          https://t.me/AivusBot
        </a>
      </p>
      <p style="font-size: 16px;">
        <strong style="color: #d4a574;">Built with:</strong><br>
        <div style="margin-top: 10px;">
          <img src="https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/python/python-original.svg" alt="Python" title="Python" width="56" height="56" style="margin-right: 15px; vertical-align: middle; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1));">
          <img src="https://raw.githubusercontent.com/lobehub/lobe-icons/refs/heads/master/packages/static-png/dark/gemini-color.png" alt="Gemini AI" title="Gemini AI" width="56" height="56" style="vertical-align: middle; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1));">
          <img src="https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/sqlite/sqlite-original.svg" alt="SQLite" title="SQLite" width="56" height="56" style="vertical-align: middle; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1));">
          <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/8/83/Telegram_2019_Logo.svg/3840px-Telegram_2019_Logo.svg.png" alt="Telegram" title="Telegram" width="56" height="56" style="margin-right: 15px; vertical-align: middle; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1));">
        </div>
      </p>
    </td>
  </tr>
</table>

# ⚙️ Installation

## 1. Clone the repository

```bash
git clone https://github.com/Myltrix/AivusBot.git
cd AivusBot
```

## 2. Install dependencies

```bash
pip install -r requirements.txt
```

---

# 🔑 How to Add Your Telegram Bot Token

1. Open Telegram and go to **BotFather**: [https://t.me/BotFather](https://t.me/BotFather)
2. Send `/start`
3. Create a new bot:

   ```
   /newbot
   ```
4. Choose a name and username
5. BotFather will give you a token like:

   ```
   1234567890:ABCDEFGH12345_example_token
   ```

Add this token to your environment file (`config.py` or `.env`):

```env
bot = telebot.TeleBot('YOUR_TELEGRAM_BOT_TOKEN')
```

---

# 🔐 How to Add Your Gemini API Key

1. Go to Google AI Studio API Key page: [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)

2. Click **Create API key**

3. You will receive a key like:

   ```
   AIzaSyExampleKey_12345
   ```

Add it to your environment file:

```env
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"
```

---

# ▶️ Run the Bot

```bash
python AivusBot.py
```

Your Telegram bot is now ready to use.
