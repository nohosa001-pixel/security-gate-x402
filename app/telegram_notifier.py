import os
import json
import logging
import urllib.request

logger = logging.getLogger("telegram_notifier")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8776757422:AAEYnvFNHI33YSObQbUEf8FMa8NqaTUuBNc")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "8884575098")
TELEGRAM_NOTIFICATIONS_ENABLED = os.getenv("TELEGRAM_NOTIFICATIONS_ENABLED", "true").lower() in ("true", "1", "yes")

def send_telegram_alert(message: str, parse_mode: str = "Markdown") -> bool:
    """Non-blocking Telegram alert dispatcher for Security Gate events."""
    if not TELEGRAM_NOTIFICATIONS_ENABLED or not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False
        
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = json.dumps({
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": parse_mode
        }).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            return resp.status == 200
    except Exception as e:
        logger.debug(f"[Telegram Alert Error] {e}")
        return False

def notify_gate_inspection_cleared(chain: str, amount_usdc: float, payer: str, score: float = 1.0):
    """Sends notification when an agent output passes security gate audit."""
    msg = (
        f"🛡️ *[Security Gate] 보안 검사 완료 & 결제 정산*\n\n"
        f"• **체인**: `{chain.upper()}`\n"
        f"• **수수료 정산**: `+{amount_usdc:.4f} USDC`\n"
        f"• **요청자**: `{payer[:8]}...{payer[-6:]}`\n"
        f"• **보안 점수**: `{score:.2f} / 1.0`\n"
        f"• **수취 금고**: D'CENT 지문인증 지갑\n"
    )
    return send_telegram_alert(msg)

