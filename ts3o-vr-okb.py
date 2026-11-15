# -*- coding: utf-8 -*-
"""TeamSpeak 3 overlay: показывает название текущего канала и клиентов канала.

Настройки (имя отслеживаемого процесса, API-ключ, отображение, цвета,
размер текста и окна) задаются в файле JSON. Путь к файлу передаётся
через командную строку; по умолчанию используется ts3o-vr-okb.json,
расположенный рядом с исполняемым файлом (или скриптом при запуске
из исходников).

Сборка в exe — Nuitka, PyQt6 (см. README.md).
"""

import argparse
import copy
import json
import os
import subprocess
import sys

import ts3.query
from PyQt6.QtCore import QRect, Qt, QTimer
from PyQt6.QtGui import QBrush, QColor, QFont, QFontMetrics, QPainter, QPen
from PyQt6.QtWidgets import QApplication, QMainWindow


def _app_dir() -> str:
    """Каталог исполняемого файла (Nuitka) либо каталог скрипта (разработка)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


DEFAULT_CONFIG_FILENAME = "ts3o-vr-okb.json"
APIKEY_PLACEHOLDER = "inset your ts3 api key"

HOST = "localhost"  # адрес (имя) query-сервера Teamspeak — в конфиг не выносится

DEFAULT_CONFIG: dict = {
    "process_name": "ts3client_win64.exe",  # имя отслеживаемого процесса
    "apikey": APIKEY_PLACEHOLDER,  # API-ключ query-сервера
    "display": {
        "show_channel": True,  # показывать название текущего канала
        "show_all": True,  # True - показывать всех, False - только говорящих сейчас
        "show_self": True,  # показывать себя
    },
    "colors": {
        "channel": "#17F707",  # цвет названия текущего канала
        "all": "#C0C0C0",  # цвет тех, кто не говорит сейчас
        "talking": "#FF00FF",  # цвет говорящих сейчас
        "muted": "#FFFF00",  # цвет клиентов с отключённым микрофоном
        "error": "#FF0000",  # цвет сообщения об ошибке
    },
    "text": {
        "font": "arial",  # семейство шрифта
        "size": 15,  # размер шрифта (pt)
    },
    "window": {
        "width": 150,  # ширина окна
        "height": 350,  # высота окна
    },
}


class ConfigError(ValueError):
    """Ошибка в файле настроек."""


def _merge(default: dict, loaded: object, path: str) -> dict:
    """Рекурсивно объединяет загруженные значения с дефолтными.

    Пропущенные ключи дополняются дефолтными значениями, неверные типы
    сообщаются через ConfigError.
    """
    if not isinstance(loaded, dict):
        raise ConfigError(f"в разделе {path or '(корень)'} ожидается объект ({{...}})")
    result: dict = {}
    for key, default_value in default.items():
        p = f"{path}.{key}" if path else key
        if key not in loaded:
            result[key] = copy.deepcopy(default_value)
            continue
        value = loaded[key]
        if isinstance(default_value, dict):
            result[key] = _merge(default_value, value, p)
            continue
        if isinstance(default_value, bool):
            if not isinstance(value, bool):
                raise ConfigError(f"поле {p}: ожидается bool")
        elif isinstance(default_value, int):
            if isinstance(value, bool) or not isinstance(value, int):
                raise ConfigError(f"поле {p}: ожидается целое число")
        elif not isinstance(value, str):
            raise ConfigError(f"поле {p}: ожидается строка")
        result[key] = value
    return result


def default_config_path() -> str:
    """Путь к файлу настроек по умолчанию: рядом с исполняемым файлом."""
    return os.path.join(_app_dir(), DEFAULT_CONFIG_FILENAME)


def ensure_default_config(path: str) -> None:
    """Создаёт файл настроек с дефолтными значениями, если его ещё нет."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps(DEFAULT_CONFIG, indent=2, ensure_ascii=False))
        f.write("\n")
    print(f"Файл настроек не найден - создан с дефолтными значениями: {path}")


def load_config(path: str) -> dict:
    """Загружает и валидирует файл настроек; при отсутствии - создаёт с дефолтами."""
    path = os.path.abspath(path)
    if not os.path.isfile(path):
        try:
            ensure_default_config(path)
        except OSError as exc:
            raise ConfigError(f"не удалось создать файл настроек {path}: {exc}") from exc
    with open(path, encoding="utf-8") as f:
        try:
            loaded = json.load(f)
        except json.JSONDecodeError as exc:
            raise ConfigError(f"файл {path} не является корректным JSON: {exc}") from exc
    merged = _merge(DEFAULT_CONFIG, loaded, "")
    merged["_path"] = path
    return merged


class Config:
    """Типизированный доступ к настройкам из JSON-файла."""

    HOST = HOST  # адрес query-сервера задаётся в коде, а не в конфиге

    def __init__(self, data: dict):
        self._d = data

    @property
    def path(self) -> str:
        return self._d["_path"]

    @property
    def process_name(self) -> str:
        return self._d["process_name"]

    @property
    def apikey(self) -> str:
        return self._d["apikey"]

    @property
    def host(self) -> str:
        return self.HOST

    @property
    def show_channel(self) -> bool:
        return self._d["display"]["show_channel"]

    @property
    def show_all(self) -> bool:
        return self._d["display"]["show_all"]

    @property
    def show_self(self) -> bool:
        return self._d["display"]["show_self"]

    @property
    def color_channel(self) -> QColor:
        return QColor(self._d["colors"]["channel"])

    @property
    def color_all(self) -> QColor:
        return QColor(self._d["colors"]["all"])

    @property
    def color_talking(self) -> QColor:
        return QColor(self._d["colors"]["talking"])

    @property
    def color_muted(self) -> QColor:
        return QColor(self._d["colors"]["muted"])

    @property
    def color_error(self) -> QColor:
        return QColor(self._d["colors"]["error"])

    @property
    def font_family(self) -> str:
        return self._d["text"]["font"]

    @property
    def font_size(self) -> int:
        return self._d["text"]["size"]

    @property
    def width(self) -> int:
        return self._d["window"]["width"]

    @property
    def height(self) -> int:
        return self._d["window"]["height"]


class DrawingWindow(QMainWindow):
    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.setWindowTitle("TS data")
        self.setGeometry(0, 0, config.width, config.height)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        #        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)

        self.painter = QPainter()
        self.painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.text_font = QFont(config.font_family, config.font_size)
        self.channelname = ""
        self.listnick: list[str] = []
        self.listflag: list[str] = []
        self.listmuted: list[str] = []
        self.ts3conn = None
        self.error_message = ""  # Сообщение об ошибке подключения (красным в окне)

        self.draw_timer = QTimer()
        self.draw_timer.start(20)  # Update the window every 20 milliseconds

    def paintEvent(self, event):
        self.painter.begin(self)
        self.painter.setPen(Qt.PenStyle.NoPen)
        self.painter.setBrush(QBrush(Qt.GlobalColor.transparent))
        self.painter.drawRect(
            QRect(0, 0, self.config.width, self.config.height)
        )  # Draw a transparent background
        self.painter.setFont(self.text_font)

        if self.error_message:
            # Не удалось подключиться к серверу - выводим красное сообщение
            metrics = QFontMetrics(self.text_font)
            text = metrics.elidedText(self.error_message, Qt.TextElideMode.ElideRight, self.config.width)
            self.painter.setPen(QPen(self.config.color_error, 0))
            self.painter.drawText(0, self.config.font_size, text)
        else:
            if self.config.show_channel:
                self.painter.setPen(QPen(self.config.color_channel, 0))
                self.painter.drawText(0, self.config.font_size, self.channelname)
            try:
                i = 0
                for n in range(len(self.listflag)):
                    ni = self.listnick[n]
                    if self.config.show_all:
                        pos_y = (self.config.font_size + 5) * (n + 2)
                        if self.listflag[n] == "1":
                            self.painter.setPen(QPen(self.config.color_talking, 0))
                        elif self.listmuted[n] == "1":
                            self.painter.setPen(QPen(self.config.color_muted, 0))
                        else:
                            self.painter.setPen(QPen(self.config.color_all, 0))
                        self.painter.drawText(0, pos_y, ni)
                    else:
                        self.painter.setPen(QPen(self.config.color_talking, 0))
                        if self.listflag[n] == "1":
                            i = i + 1
                            pos_y = (self.config.font_size + 8) * (i + 1)
                            self.painter.drawText(0, pos_y, ni)
            except IndexError as e:
                print(f"An IndexError occurred: {e}")
                # Handle the error appropriately, e.g., by logging it or notifying the user

        self.painter.end()
        self.update_data()
        QTimer.singleShot(10, self.update)  # Schedule a repaint after 0.01 second

    def reconnect(self):
        """Пытается (пере)установить соединение с query-сервером Teamspeak.

        Вызывается при старте и периодически, пока соединение отсутствует.
        При успешном подключении сбрасывает сообщение об ошибке.
        """
        if self.ts3conn is not None:
            return  # соединение уже есть
        try:
            conn = ts3.query.TS3ClientConnection(self.config.host)
            conn.auth(apikey=self.config.apikey)
            self.ts3conn = conn
            self.error_message = ""
            print(f"Подключено к {self.config.host}")
        except Exception as e:  # noqa: BLE001
            print(f"Не удалось подключиться к {self.config.host}: {e}")
            self.error_message = f"Failed to connect {self.config.host}"

    def update_data(self):
        if self.ts3conn is None:
            # нет соединения - показываем сообщение об ошибке, окно не закрывается
            self.error_message = f"Failed to connect {self.config.host}"
            return
        try:
            mi = self.ts3conn.whoami()
            self.error_message = ""  # соединение работает - сбрасываем ошибку
            my = mi[0]
            myclid, mycid = my.get("clid"), my.get("cid")

            cidnick = self.ts3conn.channelvariable(cid=mycid, properties=["channel_name"])
            self.channelname = cidnick[0].get("channel_name")

            self.listnick.clear()
            self.listflag.clear()
            self.listmuted.clear()
            cllist = self.ts3conn.channelclientlist(cid=mycid, voice=True)

            i = 0
            for i in range(50):  # получить полный список тех кто в текущем канале
                try:
                    mycllist = cllist[i]
                    lclid, nick, flag, muted = mycllist.get("clid"), mycllist.get("client_nickname"), mycllist.get("client_flag_talking"), mycllist.get("client_input_muted")
                    if lclid != myclid or lclid == myclid and self.config.show_self:
                        self.listnick.append(nick)
                        self.listflag.append(flag)
                        self.listmuted.append(muted)

                except IndexError:
                    break
        except Exception as e:  # noqa: BLE001
            # Соединение разорвано (например, при смене сервера) - не завершаем приложение,
            # сбрасываем соединение, чтобы таймер переподключения восстановил его,
            # и выводим красное сообщение об ошибке в окно
            print(f"Ошибка при обновлении данных: {e}")
            self.listnick.clear()
            self.listflag.clear()
            self.listmuted.clear()
            self.channelname = ""
            self.ts3conn = None
            self.error_message = f"Failed to connect {self.config.host}"


def is_ts3client_running(process_name: str) -> bool:
    """Проверяет, запущен ли процесс с указанным именем (через tasklist)."""
    try:
        # Используем tasklist для проверки процесса
        result = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {process_name}", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            check=True,
        )
        # Если процесс не найден, tasklist выводит строку "No tasks are running..."
        # (локализованную), поэтому проверяем именно наличие имени образа в выводе
        return process_name.lower() in result.stdout.lower()
    except subprocess.CalledProcessError:
        return False


def check_and_exit_if_no_ts3client(process_name: str):
    """Проверяет наличие процесса и завершает приложение, если его нет."""
    if not is_ts3client_running(process_name):
        print(f"Процесс {process_name} не найден. Завершение приложения.")
        # sys.exit() внутри слота Qt перехватывается диспетчером событий и
        # приложение продолжает работать - используем безусловное завершение
        os._exit(0)


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Оверлей TeamSpeak 3: название канала и клиенты канала.",
    )
    parser.add_argument(
        "config",
        nargs="?",
        default=None,
        metavar="PATH",
        help=(
            "путь к файлу настроек JSON (абсолютный или относительный); "
            f"по умолчанию: {DEFAULT_CONFIG_FILENAME} рядом с исполняемым файлом"
        ),
    )
    return parser.parse_args(argv)


def main():
    args = parse_args(sys.argv[1:])
    config_path = args.config if args.config else default_config_path()
    try:
        config = Config(load_config(config_path))
    except ConfigError as exc:
        print(f"Ошибка настроек: {exc}")
        sys.exit(1)

    app = QApplication(sys.argv)
    window = DrawingWindow(config)  # Create an instance of the DrawingWindow class
    window.show()  # Display the window

    # Первая попытка подключения к Teamspeak (при неудаче в окне
    # будет красное сообщение "Failed to connect <адрес сервера>")
    window.reconnect()

    # Добавляем таймер для проверки запущенного процесса:
    # приложение завершается только если указанного в настройках процесса нет
    process_check_timer = QTimer()
    process_check_timer.timeout.connect(lambda: check_and_exit_if_no_ts3client(config.process_name))
    process_check_timer.start(1000)  # Проверять каждую секунду

    # Таймер переподключения: пока соединения нет (например, при смене сервера
    # или при старте), периодически пробуем подключиться заново
    reconnect_timer = QTimer()
    reconnect_timer.timeout.connect(lambda: window.reconnect())
    reconnect_timer.start(3000)  # Пробовать каждые 3 секунды

    sys.exit(app.exec())  # Start the application event loop and exit when it's finished


if __name__ == "__main__":
    main()
