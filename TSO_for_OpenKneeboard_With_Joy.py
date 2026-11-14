import os
import subprocess
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QShortcut, QMessageBox
from PyQt5.QtGui import QPainter, QBrush, QColor, QPen, QFont, QKeySequence, QFontMetrics
from PyQt5.QtCore import Qt, QTimer, QRect
import ts3, time
import pygame

# ------------------- Блок пользовательских настроек: настройка отображения. True - да, False - нет ---------
show_channel = sh_channel = True  # показывать название текущего канала
show_self = sh_self = True  # Показывать себя
show_all = sh_all = False  # True - показывать всех, выделяя другим цветом говорящих, False - показывать только тех, кто говорит в текущий момент

color_channel = QColor(23, 247, 7)  # салатный - цвет названия текущего канала
color_all = QColor(192, 192, 192)  # светло-серый  - цвет тех кто не говорит в настоящий момент
color_talking = QColor(255, 0, 255)  # пурпурный - цвет говорящих в настоящий момент

myjoy = " "  # наименование выбранного вами джойстика на котором будет использоваться кнопка
mybutton = 99  # номер кнопки на выбранном джойстике, при удержании которой показываются все присутствующие в канале. Нужна если show_all = sh_all = False (см выше)
# ------------------Конец блока настроек пользователя--------------------------------------------------

APIKEY = "YP07-R90J-9ZC0-1ECY-YD9X-S6E6"
HOST = "localhost"

ts3conn = None  # глобальное соединение с query-сервером Teamspeak

pygame.init()
pygame.joystick.init()
joysticks = [pygame.joystick.Joystick(x) for x in range(pygame.joystick.get_count())]
joystick_count = pygame.joystick.get_count()
for i in range(joystick_count):
    joystick = pygame.joystick.Joystick(i)
    name = joystick.get_name()
    if name == myjoy:
        print("Джойcтик", i, ":", name, " - Выбран как источник данных для кнопок.")
        myjoy_id = int(i)
    else:
        print("Джойcтик", i, ":", name)
    axes = joystick.get_numaxes()
    buttons = joystick.get_numbuttons()
    numball = joystick.get_numballs()
    for i in range(axes):
        axis = joystick.get_axis(i)
    for i in range(buttons):
        button = joystick.get_button(i)
    for i in range(numball):
        numball = joystick.get_numballs(i)

textsize = 15
width = 300
height = 500
x_coord = int(width / 2)
y_coord = int(height - 20)


class DrawingWindow(QMainWindow):
    def __init__(self, channelname, listnick, listflag, color_talking, button):
        super().__init__()
        self.setWindowTitle("TS data")
        self.setGeometry(0, 0, width, height)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        #        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setWindowFlags(Qt.FramelessWindowHint)

        self.painter = QPainter()
        self.painter.setRenderHint(QPainter.Antialiasing)
        self.text_font = QFont("arial", textsize)
        self.channelname = channelname  # Store the coordinates for drawing rectangles
        self.listnick = listnick
        self.listflag = listflag
        self.color_talking = color_talking
        self.sh_all = sh_all
        self.sh_channel = sh_channel
        self.sh_self = sh_self
        self.button = button
        self.error_message = ""  # Сообщение об ошибке подключения (красным в окне)

        self.draw_timer = QTimer()
        self.draw_timer.start(20)  # Update the window every 20 milliseconds

    def paintEvent(self, event):
        self.painter.begin(self)
        self.painter.setPen(Qt.NoPen)
        self.painter.setBrush(QBrush(Qt.transparent))
        self.painter.drawRect(QRect(0, 0, width, height))  # Draw a transparent background
        self.painter.setFont(self.text_font)

        if self.error_message:
            # Не удалось подключиться к серверу - выводим красное сообщение
            metrics = QFontMetrics(self.text_font)
            text = metrics.elidedText(self.error_message, Qt.ElideRight, width)
            self.painter.setPen(QPen(QColor("red"), 0))
            self.painter.drawText(0, textsize, text)
        else:
            if self.sh_channel:
                self.painter.setPen(QPen(QColor(color_channel), 0))
                self.painter.drawText(0, textsize, self.channelname)
        try:
            i = 0
            for n in range(len(listflag)):
                ni = listnick[n]
                if self.sh_all:
                    pos_y = (textsize + 5) * (n + 2)
                    if listflag[n] == "1":
                        self.painter.setPen(QPen(QColor(self.color_talking), 0))
                    else:
                        self.painter.setPen(QPen(QColor(color_all), 0))
                    self.painter.drawText(0, pos_y, ni)
                else:
                    self.painter.setPen(QPen(QColor(self.color_talking), 0))
                    if listflag[n] == "1":
                        i = i + 1
                        pos_y = (textsize + 8) * (i + 1)
                        self.painter.drawText(0, pos_y, ni)
        except:
            None

        self.painter.end()
        self.update_data()
        QTimer.singleShot(10, self.update)  # Schedule a repaint after 0.01 second

    def reconnect(self):
        """Пытается (пере)установить соединение с query-сервером Teamspeak.

        Вызывается при старте и периодически, пока соединение отсутствует.
        При успешном подключении сбрасывает сообщение об ошибке.
        """
        global ts3conn
        if ts3conn is not None:
            return  # соединение уже есть
        try:
            conn = ts3.query.TS3ClientConnection(HOST)
            conn.auth(apikey=APIKEY)
            ts3conn = conn
            self.error_message = ""
            print(f"Подключено к {HOST}")
        except Exception as e:
            print(f"Не удалось подключиться к {HOST}: {e}")
            self.error_message = f"Failed to connect {HOST}"

    def update_data(self):
        global ts3conn
        if ts3conn is None:
            # нет соединения - показываем сообщение об ошибке, окно не закрывается
            self.error_message = f"Failed to connect {HOST}"
            return
        try:
            mi = ts3conn.whoami()
            self.error_message = ""  # соединение работает - сбрасываем ошибку
            my = mi[0]
            myclid, mycid = my.get("clid"), my.get("cid")

            cidnick = ts3conn.channelvariable(cid=mycid, properties=["channel_name"])
            self.channelname = cidnick[0].get("channel_name")

            listnick.clear()
            listflag.clear()
            cllist = ts3conn.channelclientlist(cid=mycid, voice=True)

            k = pygame.event.poll()
            try:
                switch = pygame.joystick.Joystick(myjoy_id).get_button(self.button)
                if switch:
                    self.sh_channel, self.sh_all, self.sh_self = True, True, True
                else:
                    self.sh_channel, self.sh_all, self.sh_self = show_channel, show_all, show_self
            except Exception:
                None

            i = 0
            for i in range(50):  # получить полный список тех кто в текущем канале
                try:
                    mycllist = cllist[i]
                    lclid, nick, flag = mycllist.get("clid"), mycllist.get("client_nickname"), mycllist.get("client_flag_talking")
                    if lclid != myclid:
                        listnick.append(nick)
                        listflag.append(flag)
                    elif lclid == myclid:
                        if self.sh_self:
                            listnick.append(nick)
                            listflag.append(flag)
                        elif not self.sh_self:
                            None
                        else:
                            None
                except Exception:
                    break

            pygame.event.clear
            return listnick, listflag, color_talking, button
        except Exception as e:  # noqa: BLE001
            # Соединение разорвано (например, при смене сервера) - не завершаем приложение,
            # сбрасываем соединение, чтобы таймер переподключения восстановил его,
            # и выводим красное сообщение об ошибке в окно
            print(f"Ошибка при обновлении данных: {e}")
            listnick.clear()
            listflag.clear()
            self.channelname = ""
            ts3conn = None
            self.error_message = f"Failed to connect {HOST}"


def is_ts3client_running():
    """Проверяет, запущен ли процесс ts3client_win64.exe"""
    try:
        # Используем tasklist для проверки процесса
        result = subprocess.run(["tasklist", "/FI", "IMAGENAME eq ts3client_win64.exe", "/FO", "CSV", "/NH"], capture_output=True, text=True, check=True)
        # Если процесс не найден, tasklist выводит строку "No tasks are running..."
        # (локализованную), поэтому проверяем именно наличие имени образа в выводе
        return "ts3client_win64.exe" in result.stdout.lower()
    except subprocess.CalledProcessError:
        return False


def check_and_exit_if_no_ts3client():
    """Проверяет наличие процесса ts3client_win64.exe и завершает приложение, если его нет"""
    if not is_ts3client_running():
        print("Процесс ts3client_win64.exe не найден. Завершение приложения.")
        # sys.exit() внутри слота Qt перехватывается диспетчером событий и
        # приложение продолжает работать - используем безусловное завершение
        os._exit(0)
        my = mi[0]
        myclid, mycid = my.get("clid"), my.get("cid")

        cidnick = ts3conn.channelvariable(cid=mycid, properties=["channel_name"])
        self.channelname = cidnick[0].get("channel_name")

        listnick.clear()
        listflag.clear()
        cllist = ts3conn.channelclientlist(cid=mycid, voice=True)

        k = pygame.event.poll()
        try:
            switch = pygame.joystick.Joystick(myjoy_id).get_button(self.button)
            if switch:
                self.sh_channel, self.sh_all, self.sh_self = True, True, True
            else:
                self.sh_channel, self.sh_all, self.sh_self = show_channel, show_all, show_self
        except:
            None

        i = 0
        for i in range(50):  # получить полный список тех кто в текущем канале
            try:
                mycllist = cllist[i]
                lclid, nick, flag = mycllist.get("clid"), mycllist.get("client_nickname"), mycllist.get("client_flag_talking")
                if lclid != myclid:
                    listnick.append(nick)
                    listflag.append(flag)
                elif lclid == myclid:
                    if self.sh_self:
                        listnick.append(nick)
                        listflag.append(flag)
                    elif not self.sh_self:
                        None
                    else:
                        None
            except:
                break

        pygame.event.clear
        return listnick, listflag, color_talking, button


def main():
    channelname = ""  # parametrs initialization
    listnick = []
    listflag = []
    button = mybutton
    app = QApplication(sys.argv)
    window = DrawingWindow(channelname, listnick, listflag, color_talking, button)  # Create an instance of the DrawingWindow class with the given coordinates
    window.show()  # Display the window

    # Первая попытка подключения к Teamspeak (при неудаче в окне
    # будет красное сообщение "Failed to connect <адрес сервера>")
    window.reconnect()

    # Добавляем таймер для проверки запущенного процесса:
    # приложение завершается только если процесса ts3client_win64.exe нет
    process_check_timer = QTimer()
    process_check_timer.timeout.connect(lambda: check_and_exit_if_no_ts3client())
    process_check_timer.start(1000)  # Проверять каждую секунду

    # Таймер переподключения: пока соединения нет (например, при смене сервера
    # или при старте), периодически пробуем подключиться заново
    reconnect_timer = QTimer()
    reconnect_timer.timeout.connect(lambda: window.reconnect())
    reconnect_timer.start(3000)  # Пробовать каждые 3 секунды

    sys.exit(app.exec_())  # Start the application event loop and exit when it's finished


if __name__ == "__main__":
    main()
