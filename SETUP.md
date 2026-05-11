# 🎀 Mahiro Bot - Setup Guide

## Quick Start (Recommended)

### 1. **Switch to Python 3.13** (⭐ EASIEST)

Python 3.14 is too new and doesn't have precompiled wheels for required packages.

**Steps:**

1. Download Python 3.13 from https://www.python.org/downloads/
2. Run installer → **CHECK "Add to PATH"** → Install
3. Verify: `python --version` (should show 3.13.x)
4. Then run:

```bash
python -m pip install -r requirements.txt
```

### 2. **Create .env File**

Create a `.env` file in the project root:

```
TELEGRAM_TOKEN=your_bot_token_here
MISTRAL_API_KEY=your_mistral_key_here
ADMIN_USER_IDS=123456789
```

**Get these from:**

- **Telegram Token**: Message [@BotFather](https://t.me/botfather)
- **Mistral API Key**: https://console.mistral.ai
- **Your User ID**: Message [@userinfobot](https://t.me/userinfobot)

### 3. **Run the Bot**

```bash
python main.py
```

**Expected output:**

```
==================================================
🎀 Бот Махиро запущен!
🎛 Админ-панель: /admin
==================================================
```

---

## Alternative: Stay on Python 3.14 (⚠️ REQUIRES BUILD TOOLS)

If you want to keep Python 3.14, install **Microsoft Visual C++ Build Tools**:

1. Download: https://visualstudio.microsoft.com/visual-cpp-build-tools/
2. Run installer
3. Select **"Desktop development with C++"**
4. Click **Install** (~2GB, ~30 mins)
5. Then run:

```bash
python -m pip install -r requirements.txt
```

---

## Troubleshooting

### "pip is not recognized"

Use: `python -m pip install -r requirements.txt` instead

### Still getting build errors?

- Clear pip cache: `python -m pip cache purge`
- Try: `python -m pip install --no-cache-dir -r requirements.txt`

### Port 8000 already in use?

Edit [admin_panel_web.py](admin_panel_web.py) and change port to 8001:

```python
uvicorn.run(app, host="127.0.0.1", port=8001)
```

---

## Project Structure

```
bot_mahiro/
├── main.py                 # Main bot entry point
├── config.py              # Configuration
├── .env                   # Your tokens (create this!)
├── admin_panel_web.py     # Web admin panel
├── requirements.txt       # Dependencies
├── bot/
│   ├── handlers.py        # Message handlers
│   ├── admin_panel.py     # Admin commands
│   └── minigames.py       # Mini-games
├── ai/
│   ├── mistral_client.py  # AI integration
│   └── prompts.py         # AI prompts
├── memory/                # User memory & mood system
└── data/                  # User data (auto-created)
```

---

## Running with Admin Panel (Optional)

The bot automatically starts a web admin panel at `http://127.0.0.1:8000`

Open in browser after starting the bot!

---

## Need Help?

- 📖 Aiogram docs: https://docs.aiogram.dev
- 🤖 Mistral AI: https://docs.mistral.ai
- 🐍 Python 3.13: https://www.python.org/downloads
