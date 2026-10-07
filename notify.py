import requests
from logger import log
from config import load_config

class Notifier:
    def __init__(self):
        self.config = load_config()
        self.telegram = self.config.get('telegram', {})
        self.enabled = self.telegram.get('enabled', False)
        self.bot_token = self.telegram.get('bot_token', '')
        self.chat_id = self.telegram.get('chat_id', '')
        
    def send_telegram_message(self, message):
        if not self.enabled or not self.bot_token or not self.chat_id:
            log.info(f"Telegram Notification (Disabled or Unconfigured): {message}")
            return False
            
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                log.info("Telegram notification sent successfully.")
                return True
            else:
                log.error(f"Failed to send Telegram notification: {response.text}")
                return False
        except Exception as e:
            log.error(f"Exception sending Telegram message: {e}")
            return False

    def notify_slot_booked(self, city, date, time, allocation):
        message = (
            f"🎯 <b>US Visa Slot Booked Successfully!</b> 🎯\n\n"
            f"📍 <b>Location:</b> {city}\n"
            f"📅 <b>Date:</b> {date}\n"
            f"⏰ <b>Time:</b> {time}\n"
            f"👥 <b>Allocation:</b> {allocation}\n\n"
            f"Bot has stopped running."
        )
        return self.send_telegram_message(message)
        
    def notify_error(self, error_message):
        message = f"⚠️ <b>Visa Bot Error</b> ⚠️\n\n{error_message}"
        return self.send_telegram_message(message)

    def notify_warning(self, warning_message):
        message = f"🔴 <b>Visa Bot Alert</b> 🔴\n\n{warning_message}"
        return self.send_telegram_message(message)

    def notify_info(self, info_message):
        message = f"ℹ️ <b>Visa Bot Update</b> ℹ️\n\n{info_message}"
        return self.send_telegram_message(message)
