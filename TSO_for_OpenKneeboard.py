import subprocess
import sys

import ts3
from PyQt5.QtCore import QRect, Qt, QTimer
from PyQt5.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PyQt5.QtWidgets import QApplication, QMainWindow

# ------------------- Блок пользовательских настроек: настройка отображения. True - да, False - нет ---------
show_channel = sh_channel = True  # показывать название текущего канала
show_all = sh_all = True  # True - показывать всех, выделяя другим цветом говорящих, False - показывать только тех, кто говорит в текущий момент
show_self = sh_self = True  # Показывать себя

color_channel = QColor(23, 247, 7)  # 'салатный' - цвет названия текущего канала
color_all = QColor(192, 192, 192)  # светло-серый  - цвет тех кто не говорит в настоящий момент
color_talking = QColor("#FF00FF")  # синий - цвет говорящих в настоящий момент
color_muted = QColor("#FFFF00")  # жёлтый - отключен микрофон
# ------------------Конец блока настроек пользователя--------------------------------------------------

textsize = 15
width = 150  # 300
height = 350  # 500
x_coord = int(width / 2)
y_coord = int(height - 20)


class DrawingWindow(QMainWindow):
    def __init__(self, channelname, listnick, listflag, listmuted, color_talking, color_muted, ts3conn):
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
        self.listmuted = listmuted
        self.color_talking = color_talking
        self.color_muted = color_muted
        self.sh_all = sh_all
        self.sh_channel = sh_channel
        self.sh_self = sh_self
        self.ts3conn = ts3conn

        self.draw_timer = QTimer()
        self.draw_timer.start(20)  # Update the window every 20 milliseconds

    def paintEvent(self, event):
        self.painter.begin(self)
        self.painter.setPen(Qt.NoPen)
        self.painter.setBrush(QBrush(Qt.transparent))
        self.painter.drawRect(QRect(0, 0, width, height))  # Draw a transparent background
        self.painter.setFont(self.text_font)

        if self.sh_channel:
            self.painter.setPen(QPen(QColor(color_channel), 0))
            self.painter.drawText(0, textsize, self.channelname)
        try:
            i = 0
            for n in range(len(self.listflag)):
                ni = self.listnick[n]
                if self.sh_all:
                    pos_y = (textsize + 5) * (n + 2)
                    if self.listflag[n] == "1":
                        self.painter.setPen(QPen(QColor(self.color_talking), 0))
                    elif self.listmuted[n] == "1":
                        self.painter.setPen(QPen(QColor(self.color_muted), 0))
                    else:
                        self.painter.setPen(QPen(QColor(color_all), 0))
                    self.painter.drawText(0, pos_y, ni)
                else:
                    self.painter.setPen(QPen(QColor(self.color_talking), 0))
                    if self.listflag[n] == "1":
                        i = i + 1
                        pos_y = (textsize + 8) * (i + 1)
                        self.painter.drawText(0, pos_y, ni)
        except IndexError as e:
            print(f"An IndexError occurred: {e}")
            # Handle the error appropriately, e.g., by logging it or notifying the user

        self.painter.end()
        self.update_data()
        QTimer.singleShot(10, self.update)  # Schedule a repaint after 0.01 second

    def update_data(self):
        mi = self.ts3conn.whoami()
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
                if lclid != myclid or lclid == myclid and self.sh_self:
                    self.listnick.append(nick)
                    self.listflag.append(flag)
                    self.listmuted.append(muted)

            except IndexError:
                break
        return self.listnick, self.listflag, self.listmuted, self.color_talking, self.color_muted


def is_ts3client_running():
    """Проверяет, запущен ли процесс ts3client_win64.exe"""
    try:
        # Используем tasklist для проверки процесса
        result = subprocess.run(["tasklist", "/FI", "IMAGENAME eq ts3client_win64.exe", "/FO", "CSV", "/NH"], capture_output=True, text=True, check=True)
        # Если результат не пустой, процесс запущен
        return bool(result.stdout.strip())
    except subprocess.CalledProcessError:
        return False


def check_and_exit_if_no_ts3client():
    """Проверяет наличие процесса ts3client_win64.exe и завершает приложение, если его нет"""
    if not is_ts3client_running():
        print("Процесс ts3client_win64.exe не найден. Завершение приложения.")
        sys.exit(0)


def main():
    APIKEY = "YP07-R90J-9ZC0-1ECY-YD9X-S6E6"
    HOST = "localhost"
    with ts3.query.TS3ClientConnection(HOST) as ts3conn:
        ts3conn.auth(apikey=APIKEY)

        channelname = ""  # parametrs initialization
        listnick = []
        listflag = []
        listmuted = []
        app = QApplication(sys.argv)
        window = DrawingWindow(
            channelname, listnick, listflag, listmuted, color_talking, color_muted, ts3conn
        )  # Create an instance of the DrawingWindow class with the given coordinates
        window.show()  # Display the window

        # Добавляем таймер для проверки запущенного процесса
        process_check_timer = QTimer()
        process_check_timer.timeout.connect(lambda: check_and_exit_if_no_ts3client())
        process_check_timer.start(1000)  # Проверять каждую секунду

        sys.exit(app.exec_())  # Start the application event loop and exit when it's finished


if __name__ == "__main__":
    main()
