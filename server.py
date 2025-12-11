import socket
from threading import Thread, Lock
import random
from datetime import datetime
import sys
import os

# Включаем поддержку ANSI цветов в Windows CMD
if sys.platform == 'win32':
    os.system('')
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except:
        pass

# ═══════════════════════════════════════════════════════════════════
#                         КОНФИГУРАЦИЯ СЕРВЕРА
# ═══════════════════════════════════════════════════════════════════
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 5002
separator_token = "<SEP>"
color_token = "<COLOR>"
cmd_token = "<CMD>"

# ANSI цвета
COLORS = {
    'red': '\033[91m', 'green': '\033[92m', 'yellow': '\033[93m',
    'blue': '\033[94m', 'purple': '\033[95m', 'cyan': '\033[96m',
    'white': '\033[97m', 'orange': '\033[38;5;208m', 'pink': '\033[38;5;205m'
}
RESET = '\033[0m'
BOLD = '\033[1m'
DIM = '\033[2m'

# Хранилище данных
client_sockets = set()
client_info = {}
lock = Lock()

# Статистика сервера
server_stats = {
    'started_at': datetime.now(),
    'total_messages': 0,
    'total_connections': 0
}


def log(msg, level="INFO"):
    """Логгер с временем и цветами"""
    colors = {"INFO": COLORS['green'], "WARN": COLORS['yellow'],
              "ERROR": COLORS['red'], "EVENT": COLORS['purple']}
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"{DIM}[{timestamp}]{RESET} {colors.get(level, RESET)}[{level}]{RESET} {msg}")


def broadcast(message, exclude=None):
    """Рассылка сообщения всем клиентам"""
    with lock:
        dead_sockets = []
        for cs in client_sockets:
            if cs != exclude:
                try:
                    cs.send(message.encode())
                except:
                    dead_sockets.append(cs)
        for ds in dead_sockets:
            client_sockets.discard(ds)


def get_online_users():
    """Получить список онлайн пользователей"""
    with lock:
        users = []
        for cs, info in client_info.items():
            online_time = datetime.now() - info['connected_at']
            mins = int(online_time.total_seconds() // 60)
            users.append(f"{info['color']}{info['name']}{RESET} ({mins} мин, {info['messages_count']} сообщ.)")
        return users


def format_uptime(delta):
    """Форматирование времени работы сервера"""
    hours, remainder = divmod(int(delta.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}ч {minutes}м {seconds}с"


def process_command(cs, cmd, args):
    """Обработка команд от клиента"""
    info = client_info.get(cs, {})
    name = info.get('name', 'Unknown')
    color = info.get('color', RESET)

    try:
        if cmd == '/help':
            help_text = f"""
{COLORS['cyan']}════════════════ КОМАНДЫ ЧАТА ════════════════
  /help    - показать эту справку
  /users   - список пользователей онлайн
  /stats   - статистика сервера
  /me      - действие (напр: /me танцует)
  /roll    - бросить кубик (1-100)
  /dm @имя - личное сообщение
  /color   - список доступных цветов
  /color X - сменить цвет на X
  /q       - выйти из чата
═══════════════════════════════════════════════{RESET}"""
            cs.send(help_text.encode())

        elif cmd == '/users':
            users = get_online_users()
            cs.send(f"\n{COLORS['cyan']}👥 Онлайн ({len(users)}): {', '.join(users)}{RESET}\n".encode())

        elif cmd == '/stats':
            uptime = format_uptime(datetime.now() - server_stats['started_at'])
            stats_msg = f"""
{COLORS['yellow']}════════════ СТАТИСТИКА СЕРВЕРА ════════════
  Аптайм:            {uptime}
  Онлайн:            {len(client_sockets)}
  Всего сообщений:   {server_stats['total_messages']}
  Всего подключений: {server_stats['total_connections']}
═════════════════════════════════════════════{RESET}"""
            cs.send(stats_msg.encode())

        elif cmd == '/me':
            action = ' '.join(args) if args else 'молчит'
            broadcast(f"\n{COLORS['purple']}* {name} {action} *{RESET}\n")

        elif cmd == '/roll':
            roll = random.randint(1, 100)
            emoji = "[КРИТ!]" if roll > 90 else ""
            broadcast(f"\n{COLORS['yellow']}[ROLL] {name} выбросил {roll}/100 {emoji}{RESET}\n")

        elif cmd == '/color':
            if not args:
                colors_list = ', '.join(f"{v}{k}{RESET}" for k, v in COLORS.items())
                cs.send(f"\n{COLORS['cyan']}Доступные цвета: {colors_list}\n".encode())
            elif args[0] in COLORS:
                new_color = COLORS[args[0]]
                with lock:
                    client_info[cs]['color'] = new_color
                cs.send(f"{cmd_token}COLOR{color_token}{new_color}".encode())
                broadcast(f"\n{new_color}[!] {name} сменил цвет!{RESET}\n")
            else:
                cs.send(f"\n{COLORS['red']}Неизвестный цвет. /color для списка{RESET}\n".encode())

        elif cmd == '/dm':
            if len(args) < 2:
                cs.send(f"\n{COLORS['red']}Использование: /dm @имя сообщение{RESET}\n".encode())
            else:
                target_name = args[0].lstrip('@')
                dm_msg = ' '.join(args[1:])
                sent = False
                with lock:
                    for sock, inf in client_info.items():
                        if inf['name'].lower() == target_name.lower():
                            sock.send(f"\n{COLORS['pink']}[ЛС от {name}]: {dm_msg}{RESET}\n".encode())
                            cs.send(f"\n{COLORS['pink']}[ЛС для {target_name}]: {dm_msg}{RESET}\n".encode())
                            sent = True
                            break
                if not sent:
                    cs.send(f"\n{COLORS['red']}Пользователь {target_name} не найден{RESET}\n".encode())
        else:
            cs.send(f"\n{COLORS['red']}Неизвестная команда. /help для справки{RESET}\n".encode())
    except:
        pass

    return True


def highlight_mentions(msg, sender_socket):
    """Подсветка упоминаний @username в сообщении"""
    with lock:
        for sock, info in client_info.items():
            mention = f"@{info['name']}"
            if mention.lower() in msg.lower():
                msg = msg.replace(mention, f"{BOLD}{COLORS['orange']}{mention}{RESET}")
                if sock != sender_socket:
                    try:
                        sock.send(f"\n{COLORS['orange']}[!] Вас упомянули в чате!{RESET}\n".encode())
                    except:
                        pass
    return msg


def remove_client(cs):
    """Безопасное удаление клиента"""
    with lock:
        client_sockets.discard(cs)
        info = client_info.pop(cs, None)
    return info


def listen_for_client(cs, client_address):
    """Обработка сообщений от клиента"""
    info = client_info.get(cs, {"name": "Unknown", "color": RESET})
    client_name = info["name"]
    client_color = info["color"]

    while True:
        try:
            msg = cs.recv(1024).decode()
            if not msg:
                break
        except (ConnectionResetError, ConnectionAbortedError, OSError):
            break
        except Exception as e:
            log(f"Ошибка от {client_name}: {e}", "ERROR")
            break

        # Проверяем команды
        if separator_token in msg:
            content = msg.split(separator_token)[-1].strip()
            if content.startswith('/'):
                parts = content.split()
                process_command(cs, parts[0], parts[1:])
                continue

        # Обычное сообщение
        server_stats['total_messages'] += 1
        with lock:
            if cs in client_info:
                client_info[cs]['messages_count'] += 1

        if color_token in msg:
            parts = msg.split(color_token)
            msg_color = parts[0]
            msg_content = parts[1].replace(separator_token, ": ") if len(parts) > 1 else ""
        else:
            msg_color = client_color
            msg_content = msg.replace(separator_token, ": ")

        msg_content = highlight_mentions(msg_content, cs)
        formatted_msg = f"{msg_color}{msg_content}{RESET}"
        broadcast(formatted_msg)

    removed_info = remove_client(cs)
    if removed_info:
        broadcast(f"\n{COLORS['red']}[<-] {client_name} покинул чат{RESET}\n")
        log(f"{client_name} отключился", "EVENT")

    try:
        cs.close()
    except:
        pass


def receive_client_info(cs):
    """Получение имени и цвета от нового клиента"""
    try:
        data = cs.recv(1024).decode()
        if color_token in data:
            parts = data.split(color_token)
            return parts[0], parts[1] if len(parts) > 1 else random.choice(list(COLORS.values()))
        return data, random.choice(list(COLORS.values()))
    except Exception as e:
        log(f"Ошибка регистрации: {e}", "ERROR")
        return None, None


# ═══════════════════════════════════════════════════════════════════
#                         ЗАПУСК СЕРВЕРА
# ═══════════════════════════════════════════════════════════════════
s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind((SERVER_HOST, SERVER_PORT))
s.listen(5)

log(f"Сервер запущен на {SERVER_HOST}:{SERVER_PORT}")
log("Ожидание подключений...", "EVENT")

try:
    while True:
        client_socket, client_address = s.accept()
        server_stats['total_connections'] += 1

        client_name, client_color = receive_client_info(client_socket)
        if client_name is None:
            client_socket.close()
            continue

        with lock:
            client_info[client_socket] = {
                "name": client_name,
                "color": client_color,
                "address": client_address,
                "connected_at": datetime.now(),
                "messages_count": 0
            }
            client_sockets.add(client_socket)

        broadcast(f"\n{COLORS['green']}[->] {client_name} присоединился! (Онлайн: {len(client_sockets)}){RESET}\n")
        log(f"{client_name} подключился с {client_address}", "EVENT")

        welcome = f"\n{COLORS['cyan']}Добро пожаловать, {client_name}! Введите /help для списка команд{RESET}\n"
        try:
            client_socket.send(welcome.encode())
        except:
            pass

        Thread(target=listen_for_client, args=(client_socket, client_address), daemon=True).start()

except KeyboardInterrupt:
    log("Завершение работы сервера...", "WARN")
finally:
    with lock:
        for cs in list(client_sockets):
            try:
                cs.close()
            except:
                pass
    s.close()
    log("Сервер остановлен", "EVENT")