import socket
import random
from threading import Thread, Event
from datetime import datetime
import sys
import os

# Включаем поддержку ANSI цветов в Windows cmd
if sys.platform == 'win32':
    os.system('')
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except:
        pass

# ═══════════════════════════════════════════════════════════════════
#                         КОНФИГУРАЦИЯ КЛИЕНТА
# ═══════════════════════════════════════════════════════════════════
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 50000
BUFFER_SIZE = 4096
separator_token = "<SEP>"
color_token = "<COLOR>"
cmd_token = "<CMD>"
register_token = "<REGISTER>"
heartbeat_token = "<HEARTBEAT>"

COLORS = {
    'red': '\033[91m', 'green': '\033[92m', 'yellow': '\033[93m',
    'blue': '\033[94m', 'purple': '\033[95m', 'cyan': '\033[96m',
    'white': '\033[97m', 'orange': '\033[38;5;208m', 'pink': '\033[38;5;205m'
}
RESET = '\033[0m'
BOLD = '\033[1m'
DIM = '\033[2m'

# Случайный цвет при запуске
MY_COLOR = random.choice(list(COLORS.values()))

# Флаг для остановки потоков
stop_event = Event()

# Адрес сервера
server_address = (SERVER_HOST, SERVER_PORT)


def clear_line():
    """Очистка текущей строки"""
    print('\r' + ' ' * 60 + '\r', end='')


def listen_for_messages():
    """Прослушивание входящих сообщений"""
    global MY_COLOR
    while not stop_event.is_set():
        try:
            client.settimeout(0.5)
            data, addr = client.recvfrom(BUFFER_SIZE)
            message = data.decode('utf-8')

            if not message:
                continue

            # Обработка команд от сервера
            if message.startswith(cmd_token):
                if "COLOR" in message:
                    MY_COLOR = message.split(color_token)[-1]
                    print(f"\n{COLORS['green']}Цвет изменён!{RESET}")
                    print(f"{DIM}[{name}]>{RESET} ", end='', flush=True)
                continue

            clear_line()
            print(message)
            print(f"{DIM}[{name}]>{RESET} ", end='', flush=True)

        except socket.timeout:
            continue
        except OSError as e:
            if not stop_event.is_set():
                print(f"\n{COLORS['red']}[!] Ошибка сети: {e}{RESET}")
            break
        except Exception as e:
            if not stop_event.is_set():
                print(f"\n{COLORS['red']}[!] Ошибка: {e}{RESET}")
            break


def send_heartbeat():
    """Отправка heartbeat для поддержания соединения"""
    import time
    while not stop_event.is_set():
        try:
            client.sendto(heartbeat_token.encode(), server_address)
            time.sleep(10)  # Heartbeat каждые 10 секунд
        except:
            break


# ═══════════════════════════════════════════════════════════════════
#                         ПОДКЛЮЧЕНИЕ
# ═══════════════════════════════════════════════════════════════════
print(f"{COLORS['cyan']}=== UDP Chat Client ==={RESET}")
print(f"{DIM}ИКСИС ЛР №5 - UDP версия{RESET}\n")

# Создаем UDP сокет
client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

print(f"{COLORS['green']}[+] Сокет создан!{RESET}")
print(f"Сервер: {SERVER_HOST}:{SERVER_PORT}")
print(f"Ваш цвет: {MY_COLOR}████████{RESET}\n")

name = input(f"{COLORS['cyan']}Введите имя: {RESET}").strip()
if not name:
    name = f"User{random.randint(1000, 9999)}"

# Регистрация на сервере
try:
    registration_msg = f"{register_token}{name}{color_token}{MY_COLOR}"
    client.sendto(registration_msg.encode(), server_address)
except Exception as e:
    print(f"{COLORS['red']}[!] Ошибка регистрации: {e}{RESET}")
    sys.exit(1)

# Меню команд
print(f"""
{COLORS['cyan']}Команды: /help /users /stats /me /roll /dm /color /q{RESET}
{COLORS['cyan']}Упоминание: @имя{RESET}
""")

# Запуск потока прослушивания
listener_thread = Thread(target=listen_for_messages, daemon=True)
listener_thread.start()

# Запуск потока heartbeat
heartbeat_thread = Thread(target=send_heartbeat, daemon=True)
heartbeat_thread.start()

# ═══════════════════════════════════════════════════════════════════
#                         ОСНОВНОЙ ЦИКЛ
# ═══════════════════════════════════════════════════════════════════
try:
    while True:
        try:
            print(f"{DIM}[{name}]>{RESET} ", end='', flush=True)
            to_send = input()
        except (KeyboardInterrupt, EOFError):
            print(f"\n{COLORS['yellow']}Выход...{RESET}")
            break

        # Выход по /q
        if to_send.strip().lower() == '/q':
            print(f"{COLORS['yellow']}Отключение...{RESET}")
            # Отправляем серверу команду выхода
            try:
                date_now = datetime.now().strftime('%H:%M:%S')
                quit_msg = f"{MY_COLOR}{color_token}[{date_now}] {name}{separator_token}/q"
                client.sendto(quit_msg.encode(), server_address)
            except:
                pass
            break

        if not to_send.strip():
            clear_line()
            continue

        # Формирование сообщения
        date_now = datetime.now().strftime('%H:%M:%S')
        to_send = f"{MY_COLOR}{color_token}[{date_now}] {name}{separator_token}{to_send}"

        try:
            client.sendto(to_send.encode(), server_address)
        except Exception as e:
            print(f"{COLORS['red']}[!] Ошибка отправки: {e}{RESET}")
            break

finally:
    stop_event.set()
    try:
        client.close()
    except:
        pass
    print(f"{COLORS['green']}Соединение закрыто. Пока!{RESET}")