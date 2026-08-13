import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

def find_ngrok_bin():
    return shutil.which("ngrok") or ("/usr/local/bin/ngrok" if os.path.exists("/usr/local/bin/ngrok") else "ngrok")

def get_ngrok_url():
    try:
        req = urllib.request.Request("http://127.0.0.1:4040/api/tunnels")
        with urllib.request.urlopen(req, timeout=2) as response:
            data = json.loads(response.read().decode())
            for tunnel in data.get("tunnels", []):
                if tunnel.get("proto") == "https":
                    return tunnel.get("public_url")
            if data.get("tunnels"):
                return data["tunnels"][0].get("public_url")
    except Exception:
        return None

def update_env_file(public_url):
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        print("❌ .env файл не найден!")
        return

    lines = env_path.read_text().splitlines()
    new_lines = []
    
    webhook_url = f"{public_url}/bot/webhook/"
    webapp_url = f"{public_url}/miniapp/"

    has_webhook = False
    has_webapp = False

    for line in lines:
        if line.startswith("TELEGRAM_WEBHOOK_URL="):
            new_lines.append(f"TELEGRAM_WEBHOOK_URL={webhook_url}")
            has_webhook = True
        elif line.startswith("TELEGRAM_WEBAPP_URL="):
            new_lines.append(f"TELEGRAM_WEBAPP_URL={webapp_url}")
            has_webapp = True
        else:
            new_lines.append(line)

    if not has_webhook:
        new_lines.append(f"TELEGRAM_WEBHOOK_URL={webhook_url}")
    if not has_webapp:
        new_lines.append(f"TELEGRAM_WEBAPP_URL={webapp_url}")

    env_path.write_text("\n".join(new_lines) + "\n")
    print(f"✅ Автоматически обновлён .env:")
    print(f"   TELEGRAM_WEBHOOK_URL = {webhook_url}")
    print(f"   TELEGRAM_WEBAPP_URL  = {webapp_url}")

def main():
    print("🚀 Автоматический запуск локальной разработки...")

    url = get_ngrok_url()
    ngrok_proc = None

    if not url:
        ngrok_bin = find_ngrok_bin()
        print(f"🌐 Запуск туннеля ({ngrok_bin} http 8000)...")
        ngrok_proc = subprocess.Popen(
            [ngrok_bin, "http", "8000"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        # Ожидаем поднимания туннеля до 5 секунд
        for _ in range(10):
            time.sleep(0.5)
            url = get_ngrok_url()
            if url:
                break

    if not url:
        print("❌ Не удалось получить URL от ngrok.")
        print("💡 Подсказка: если ngrok запускается впервые, выполните один раз: ngrok config add-authtoken <ваш_токен>")
        if ngrok_proc:
            ngrok_proc.terminate()
        sys.exit(1)

    print(f"🔗 Ваша публичная HTTPS ссылка: {url}")

    update_env_file(url)

    print("📦 Проверка миграций базы данных...")
    subprocess.run([sys.executable, "manage.py", "migrate"], check=True)

    # Проверяем токен
    token = ""
    env_path = BASE_DIR / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("TELEGRAM_BOT_TOKEN="):
                token = line.split("=", 1)[1].strip()

    if token:
        print("🤖 Установка Telegram Webhook...")
        try:
            subprocess.run([sys.executable, "manage.py", "set_webhook", f"{url}/bot/webhook/"], check=True)
        except subprocess.CalledProcessError:
            print("⚠️ Не удалось установить вебхук (проверьте токен).")
    else:
        print("⚠️ TELEGRAM_BOT_TOKEN пока пустой в .env! Не забудьте указать токен от @BotFather.")

    print("\n" + "="*65)
    print(f"📱 Укажите этот URL в @BotFather (для WebApp):")
    print(f"👉  {url}/miniapp/")
    print("="*65 + "\n")

    print("🟢 Запуск Uvicorn сервера (http://localhost:8000)...")
    try:
        subprocess.run(["uvicorn", "config.asgi:application", "--reload", "--port", "8000"])
    except KeyboardInterrupt:
        print("\n👋 Завершение работы...")
    finally:
        if ngrok_proc:
            ngrok_proc.terminate()

if __name__ == "__main__":
    main()
