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
SERVER_PORT = 5002
separator_token = "<SEP>"
color_token = "<COLOR>"
cmd_token = "<CMD>"

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

# Флаг для остановки потока
stop_event = Event()


def clear_line():
    """Очистка текущей строки"""
    print('\r' + ' ' * 60 + '\r', end='')


def listen_for_messages():
    """Прослушивание входящих сообщений"""
    global MY_COLOR
    while not stop_event.is_set():
        try:
            s.settimeout(0.5)
            message = s.recv(1024).decode()

            if not message:
                if not stop_event.is_set():
                    print(f"\n{COLORS['red']}[!] Соединение с сервером разорвано{RESET}")
                break

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
        except (ConnectionResetError, ConnectionAbortedError, OSError):
            break
        except Exception as e:
            if not stop_event.is_set():
                print(f"\n{COLORS['red']}[!] Ошибка: {e}{RESET}")
            break


# ═══════════════════════════════════════════════════════════════════
#                         ПОДКЛЮЧЕНИЕ
# ═══════════════════════════════════════════════════════════════════
print(f"{COLORS['cyan']}=== TCP Chat Client ==={RESET}")
print(f"{DIM}ИКСИС ЛР №4 - Dylariz{RESET}\n")

s = socket.socket()
print(f"{DIM}Подключение к {SERVER_HOST}:{SERVER_PORT}...{RESET}")

try:
    s.connect((SERVER_HOST, SERVER_PORT))
except ConnectionRefusedError:
    print(f"{COLORS['red']}[!] Сервер недоступен{RESET}")
    sys.exit(1)
except socket.error as e:
    print(f"{COLORS['red']}[!] Ошибка: {e}{RESET}")
    sys.exit(1)

print(f"{COLORS['green']}[+] Подключено!{RESET}")
print(f"Ваш цвет: {MY_COLOR}████████{RESET}\n")

name = input(f"{COLORS['cyan']}Введите имя: {RESET}").strip()
if not name:
    name = f"User{random.randint(1000, 9999)}"

# Отправка информации серверу
try:
    s.send(f"{name}{color_token}{MY_COLOR}".encode())
except Exception as e:
    print(f"{COLORS['red']}[!] Ошибка: {e}{RESET}")
    sys.exit(1)

# Меню команд
print(f"""
{COLORS['cyan']}Команды: /help /users /stats /me /roll /dm /color /q{RESET}
{COLORS['cyan']}Упоминание: @имя{RESET}
""")

# Запуск потока
listener_thread = Thread(target=listen_for_messages, daemon=True)
listener_thread.start()

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
            break

        if not to_send.strip():
            clear_line()
            continue

        # Формирование сообщения
        date_now = datetime.now().strftime('%H:%M:%S')
        to_send = f"{MY_COLOR}{color_token}[{date_now}] {name}{separator_token}{to_send}"

        try:
            s.send(to_send.encode())
        except BrokenPipeError:
            print(f"{COLORS['red']}[!] Соединение потеряно{RESET}")
            break
        except Exception as e:
            print(f"{COLORS['red']}[!] Ошибка: {e}{RESET}")
            break

finally:
    stop_event.set()
    try:
        s.shutdown(socket.SHUT_RDWR)
    except:
        pass
    try:
        s.close()
    except:
        pass
    print(f"{COLORS['green']}Соединение закрыто. Пока!{RESET}")