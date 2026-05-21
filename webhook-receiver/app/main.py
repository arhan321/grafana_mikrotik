import os
import html
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Request, HTTPException

app = FastAPI(title="MikroTik Alert Webhook Receiver")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TIMEZONE = os.getenv("TZ", "Asia/Jakarta")


def esc(value) -> str:
    return html.escape(str(value)) if value is not None else "-"


def format_time(value: str) -> str:
    if not value:
        return "-"
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.astimezone(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d %H:%M:%S WIB")
    except Exception:
        return value


def send_telegram(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    response = requests.post(
        url,
        json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        },
        timeout=15,
    )

    if response.status_code >= 400:
        raise RuntimeError(response.text)


def build_message(alert: dict) -> str:
    status = alert.get("status", "unknown").upper()
    labels = alert.get("labels", {})
    annotations = alert.get("annotations", {})

    icon = "🚨" if status == "FIRING" else "✅" if status == "RESOLVED" else "ℹ️"
    title = "MIKROTIK ALERT" if status == "FIRING" else "MIKROTIK RECOVERY"

    return f"""
<b>{icon} {title}</b>

<b>Status</b>   : {esc(status)}
<b>Alert</b>    : {esc(labels.get("alertname"))}
<b>Severity</b> : {esc(labels.get("severity"))}
<b>Instance</b> : {esc(labels.get("instance"))}
<b>Router</b>   : {esc(labels.get("router"))}
<b>Interface</b>: {esc(labels.get("ifName", "-"))}

<b>Mulai</b>    : {esc(format_time(alert.get("startsAt", "")))}
<b>Selesai</b>  : {esc(format_time(alert.get("endsAt", "")))}

<b>Summary</b>
{esc(annotations.get("summary"))}

<b>Description</b>
{esc(annotations.get("description"))}
""".strip()


@app.get("/")
def index():
    return {"status": "ok", "service": "mikrotik-webhook-receiver"}


@app.post("/webhook/alert")
async def webhook_alert(request: Request):
    try:
        payload = await request.json()
        alerts = payload.get("alerts", [])

        for alert in alerts:
            send_telegram(build_message(alert))

        return {"status": "ok", "sent": len(alerts)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
