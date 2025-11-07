## Telegram reminder bot

Bot vazifasi: serverlar uchun oylik to'lov eslatmalarini yuborish. Loyihalarni bot orqali qo'shasiz, ma'lumotlar SQLite bazada saqlanadi, har kuni 09:00 da tekshiriladi.

### Funksiyalar
- /addproject: Loyiha qo'shish (project nomi, server, egasi, telefon)
- /list: Loyihalar ro'yxati va keyingi muddat
- /delete <ID>: ID bo'yicha o'chirish
- /editdue: Keyingi muddatni (due date) tahrirlash

### O'rnatish
1) Talablar:
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2) Sozlamalar:
`config/settings.example.env` ni ko'chirib, `.env` nomi bilan saqlang va qiymatlarni to'ldiring:
```
cp config/settings.example.env .env
```

3) Ishga tushirish:
```
python -m app.bot
```

### Muhim sozlamalar
- TELEGRAM_BOT_TOKEN: Bot token
- ADMIN_CHAT_ID: Eslatmalar yuboriladigan chat ID (o'zingiz yoki guruh)
- DATABASE_PATH: SQLite fayl yo'li (masalan, ./data/reminder.db)
- TIMEZONE: Jadval vaqt zonasi (masalan, Asia/Tashkent)

### systemd bilan servis sifatida ishga tushirish (ixtiyoriy)
`/etc/systemd/system/telegram-reminder-bot.service`:
```
[Unit]
Description=Telegram Reminder Bot
After=network.target

[Service]
Type=simple
User=shahzod
WorkingDirectory=/home/shahzod/Projects/ArdentSoft/telegram-reminder-bot
Environment=PYTHONUNBUFFERED=1
EnvironmentFile=/home/shahzod/Projects/ArdentSoft/telegram-reminder-bot/.env
ExecStart=/home/shahzod/Projects/ArdentSoft/telegram-reminder-bot/.venv/bin/python -m app.bot
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```
```
sudo systemctl daemon-reload
sudo systemctl enable --now telegram-reminder-bot
```

### Eslatma
- Bot har kuni 09:00 da ko'rib chiqadi va muddati yetgan loyihalar uchun xabar yuboradi.
- Har yuborilgandan so'ng keyingi muddat 30 kunga suriladi.
