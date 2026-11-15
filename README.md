# TeamSpeakOverlayVR

Оверлей для TeamSpeak 3: показывает название текущего канала и список клиентов
канала, выделяя цветом тех, кто говорит прямо сейчас (и тех, у кого выключен микрофон).

Скрипт `ts3o-vr-okb.py` (PyQt6) подключается к query-серверу TeamSpeak,
отрисовывает полупрозрачное окно и работает, пока запущен клиент
TeamSpeak (проверяется через `tasklist`).

## Установка

Требуется Python 3.12+ и `uv`:

```bat
uv venv --python 3.12
uv pip install -r requirements.txt
```

## Запуск

```bat
runner.cmd
uv run ts3o-vr-okb.py
```

Небольшой оверлей появится в левом верхнем углу экрана. Если сервер TeamSpeak
недоступен, в окне будет красным показано `Failed to connect <адрес>`, и
приложение будет периодически пытаться переподключиться.

## Настройки (файл JSON)

Все параметры задаются в файле настроек JSON. Путь к файлу передаётся
первым аргументом командной строки (абсолютный или относительный):

```bat
runner.cmd D:\config\ts3o-vr-okb.json
uv run ts3o-vr-okb.py C:\ts3o\ts3o-vr-okb.json
```

Если аргумент не передан, используется `ts3o-vr-okb.json` из каталога
исполняемого файла (при запуске из исходников — каталог скрипта).
Если файла нет, он создаётся автоматически со значениями по умолчанию.
Частичный файл тоже допустим: пропущенные ключи дополняются дефолтами,
при неверном типе значения выводится сообщение об ошибке.

Поля:

| Поле | Тип | По умолчанию | Описание |
|---|---|---|---|
| `process_name` | строка | `ts3client_win64.exe` | имя процесса TeamSpeak-клиента; если процесс не запущен, оверлей завершается |
| `apikey` | строка | `inset your ts3 api key` | API-ключ query-сервера (замените на свой) |
| `display.show_channel` | bool | `true` | показывать название текущего канала |
| `display.show_all` | bool | `true` | `true` — показывать всех клиентов, `false` — только говорящих сейчас |
| `display.show_self` | bool | `true` | показывать себя в списке |
| `colors.channel` | строка | `#17F707` | цвет названия канала |
| `colors.all` | строка | `#C0C0C0` | цвет клиентов, не говорящих сейчас |
| `colors.talking` | строка | `#FF00FF` | цвет говорящих сейчас |
| `colors.muted` | строка | `#FFFF00` | цвет клиентов с отключённым микрофоном |
| `colors.error` | строка | `#FF0000` | цвет сообщения об ошибке |
| `text.font` | строка | `arial` | семейство шрифта |
| `text.size` | число | `15` | размер шрифта (pt) |
| `window.width` | число | `150` | ширина окна |
| `window.height` | число | `350` | высота окна |

Пример файла `ts3o-vr-okb.json`:

```json
{
  "process_name": "ts3client_win64.exe",
  "apikey": "inset your ts3 api key",
  "display": {
    "show_channel": true,
    "show_all": true,
    "show_self": true
  },
  "colors": {
    "channel": "#17F707",
    "all": "#C0C0C0",
    "talking": "#FF00FF",
    "muted": "#FFFF00",
    "error": "#FF0000"
  },
  "text": {
    "font": "arial",
    "size": 15
  },
  "window": {
    "width": 150,
    "height": 350
  }
}
```

Адрес query-сервера (`HOST`) задаётся в коде (`ts3o-vr-okb.py`), а не в файле настроек.

## Сборка в exe (Nuitka)

Скрипт использует только Qt и stdlib, поэтому собирается в standalone
одной командой:

```bat
uv pip install nuitka
.venv\Scripts\python.exe -m nuitka ts3o-vr-okb.py --standalone --onefile --pyqt6=module --enable-plugin=nogui --module-name=ts3o_vr_okb --output-filename=ts3o-vr-okb.exe --remove-output
```

Для сборки нужен C-компилятор (MSVC Build Tools или MinGW64/LLVM).

Итоговый `ts3o-vr-okb.exe` запускается так же, как скрипт:
без аргументов конфиг берётся из каталога exe, либо путь передаётся
как первый аргумент:

```bat
ts3o-vr-okb.exe D:\config\ts3o-vr-okb.json
```

## Структура проекта

```
TeamSpeakOverlayVR/
├── runner.cmd                  # запуск (передаёт аргументы скрипту)
├── ts3o-vr-okb.py              # оверлей: канал + клиенты канала (PyQt6)
├── ts3o-vr-okb.json            # файл настроек (создаётся автоматически, если отсутствует)
├── ts3o-vr-joystick-okb.py     # joystick-вариант оверлея
├── requirements.txt
└── pyproject.toml
```
