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
SERVER_PORT = 50000
BUFFER_SIZE = 4096
separator_token = "<SEP>"
color_token = "<COLOR>"
cmd_token = "<CMD>"
register_token = "<REGISTER>"
heartbeat_token = "<HEARTBEAT>"

# ANSI цвета
COLORS = {
    'red': '\033[91m', 'green': '\033[92m', 'yellow': '\033[93m',
    'blue': '\033[94m', 'purple': '\033[95m', 'cyan': '\033[96m',
    'white': '\033[97m', 'orange': '\033[38;5;208m', 'pink': '\033[38;5;205m'
}
RESET = '\033[0m'
BOLD = '\033[1m'
DIM = '\033[2m'

# Хранилище данных (теперь по адресам, а не по сокетам)
client_info = {}  # {address: {"name": ..., "color": ..., ...}}
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


def broadcast(message, exclude_addr=None):
    """Рассылка сообщения всем клиентам через UDP"""
    with lock:
        dead_clients = []
        for addr in client_info:
            if addr != exclude_addr:
                try:
                    server.sendto(message.encode(), addr)
                except Exception as e:
                    log(f"Ошибка отправки на {addr}: {e}", "ERROR")
                    dead_clients.append(addr)
        for addr in dead_clients:
            remove_client(addr)


def send_to_client(addr, message):
    """Отправка сообщения конкретному клиенту"""
    try:
        server.sendto(message.encode(), addr)
    except Exception as e:
        log(f"Ошибка отправки на {addr}: {e}", "ERROR")


def get_online_users():
    """Получить список онлайн пользователей"""
    with lock:
        users = []
        for addr, info in client_info.items():
            online_time = datetime.now() - info['connected_at']
            mins = int(online_time.total_seconds() // 60)
            users.append(f"{info['color']}{info['name']}{RESET} ({mins} мин, {info['messages_count']} сообщ.)")
        return users


def format_uptime(delta):
    """Форматирование времени работы сервера"""
    hours, remainder = divmod(int(delta.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}ч {minutes}м {seconds}с"


def process_command(addr, cmd, args):
    """Обработка команд от клиента"""
    info = client_info.get(addr, {})
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
            send_to_client(addr, help_text)

        elif cmd == '/users':
            users = get_online_users()
            send_to_client(addr, f"\n{COLORS['cyan']}👥 Онлайн ({len(users)}): {', '.join(users)}{RESET}\n")

        elif cmd == '/stats':
            uptime = format_uptime(datetime.now() - server_stats['started_at'])
            stats_msg = f"""
{COLORS['yellow']}════════════ СТАТИСТИКА СЕРВЕРА ════════════
  Аптайм:            {uptime}
  Онлайн:            {len(client_info)}
  Всего сообщений:   {server_stats['total_messages']}
  Всего подключений: {server_stats['total_connections']}
═════════════════════════════════════════════{RESET}"""
            send_to_client(addr, stats_msg)

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
                send_to_client(addr, f"\n{COLORS['cyan']}Доступные цвета: {colors_list}\n")
            elif args[0] in COLORS:
                new_color = COLORS[args[0]]
                with lock:
                    client_info[addr]['color'] = new_color
                send_to_client(addr, f"{cmd_token}COLOR{color_token}{new_color}")
                broadcast(f"\n{new_color}[!] {name} сменил цвет!{RESET}\n")
            else:
                send_to_client(addr, f"\n{COLORS['red']}Неизвестный цвет. /color для списка{RESET}\n")

        elif cmd == '/dm':
            if len(args) < 2:
                send_to_client(addr, f"\n{COLORS['red']}Использование: /dm @имя сообщение{RESET}\n")
            else:
                target_name = args[0].lstrip('@')
                dm_msg = ' '.join(args[1:])
                sent = False
                with lock:
                    for client_addr, inf in client_info.items():
                        if inf['name'].lower() == target_name.lower():
                            send_to_client(client_addr, f"\n{COLORS['pink']}[ЛС от {name}]: {dm_msg}{RESET}\n")
                            send_to_client(addr, f"\n{COLORS['pink']}[ЛС для {target_name}]: {dm_msg}{RESET}\n")
                            sent = True
                            break
                if not sent:
                    send_to_client(addr, f"\n{COLORS['red']}Пользователь {target_name} не найден{RESET}\n")

        elif cmd == '/q':
            remove_client(addr)
            return False
        else:
            send_to_client(addr, f"\n{COLORS['red']}Неизвестная команда. /help для справки{RESET}\n")
    except Exception as e:
        log(f"Ошибка обработки команды: {e}", "ERROR")

    return True


def highlight_mentions(msg, sender_addr):
    """Подсветка упоминаний @username в сообщении"""
    with lock:
        for addr, info in client_info.items():
            mention = f"@{info['name']}"
            if mention.lower() in msg.lower():
                msg = msg.replace(mention, f"{BOLD}{COLORS['orange']}{mention}{RESET}")
                if addr != sender_addr:
                    try:
                        send_to_client(addr, f"\n{COLORS['orange']}[!] Вас упомянули в чате!{RESET}\n")
                    except:
                        pass
    return msg


def remove_client(addr):
    """Безопасное удаление клиента"""
    with lock:
        info = client_info.pop(addr, None)
    if info:
        broadcast(f"\n{COLORS['red']}[<-] {info['name']} покинул чат{RESET}\n")
        log(f"{info['name']} отключился", "EVENT")
    return info


def register_client(addr, data):
    """Регистрация нового клиента"""
    try:
        # Формат: <REGISTER>name<COLOR>color
        if register_token in data:
            data = data.replace(register_token, "")

        if color_token in data:
            parts = data.split(color_token)
            client_name = parts[0]
            client_color = parts[1] if len(parts) > 1 else random.choice(list(COLORS.values()))
        else:
            client_name = data
            client_color = random.choice(list(COLORS.values()))

        with lock:
            client_info[addr] = {
                "name": client_name,
                "color": client_color,
                "address": addr,
                "connected_at": datetime.now(),
                "messages_count": 0,
                "last_seen": datetime.now()
            }

        server_stats['total_connections'] += 1

        broadcast(f"\n{COLORS['green']}[->] {client_name} присоединился! (Онлайн: {len(client_info)}){RESET}\n")
        log(f"{client_name} подключился с {addr}", "EVENT")

        welcome = f"\n{COLORS['cyan']}Добро пожаловать, {client_name}! Введите /help для списка команд{RESET}\n"
        send_to_client(addr, welcome)

        return True
    except Exception as e:
        log(f"Ошибка регистрации: {e}", "ERROR")
        return False


def process_message(addr, msg):
    """Обработка сообщения от клиента"""
    # Обновляем время последней активности
    with lock:
        if addr in client_info:
            client_info[addr]['last_seen'] = datetime.now()

    info = client_info.get(addr, {"name": "Unknown", "color": RESET})
    client_name = info["name"]
    client_color = info["color"]

    # Проверяем команды
    if separator_token in msg:
        content = msg.split(separator_token)[-1].strip()
        if content.startswith('/'):
            parts = content.split()
            return process_command(addr, parts[0], parts[1:])

    # Обычное сообщение
    server_stats['total_messages'] += 1
    with lock:
        if addr in client_info:
            client_info[addr]['messages_count'] += 1

    if color_token in msg:
        parts = msg.split(color_token)
        msg_color = parts[0]
        msg_content = parts[1].replace(separator_token, ": ") if len(parts) > 1 else ""
    else:
        msg_color = client_color
        msg_content = msg.replace(separator_token, ": ")

    msg_content = highlight_mentions(msg_content, addr)
    formatted_msg = f"{msg_color}{msg_content}{RESET}"
    broadcast(formatted_msg)

    return True


# ═══════════════════════════════════════════════════════════════════
#                         ЗАПУСК СЕРВЕРА
# ═══════════════════════════════════════════════════════════════════

# Создаем UDP сокет
server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind((SERVER_HOST, SERVER_PORT))

log(f"UDP Сервер запущен на {SERVER_HOST}:{SERVER_PORT}")
log("Ожидание сообщений...", "EVENT")

try:
    while True:
        try:
            # Получаем данные и адрес отправителя
            data, addr = server.recvfrom(BUFFER_SIZE)
            msg = data.decode('utf-8')

            if not msg:
                continue

            # Проверяем, это heartbeat?
            if msg == heartbeat_token:
                with lock:
                    if addr in client_info:
                        client_info[addr]['last_seen'] = datetime.now()
                continue

            # Проверяем, это регистрация нового клиента?
            if msg.startswith(register_token):
                register_client(addr, msg)
                continue

            # Проверяем, зарегистрирован ли клиент
            if addr not in client_info:
                send_to_client(addr, f"{COLORS['red']}Ошибка: вы не зарегистрированы. Перезапустите клиент.{RESET}")
                continue

            # Обрабатываем сообщение
            process_message(addr, msg)

        except Exception as e:
            log(f"Ошибка обработки: {e}", "ERROR")

except KeyboardInterrupt:
    log("Завершение работы сервера...", "WARN")
finally:
    # Уведомляем всех клиентов
    broadcast(f"\n{COLORS['red']}[!] Сервер завершает работу{RESET}\n")
    server.close()
    log("Сервер остановлен", "EVENT")