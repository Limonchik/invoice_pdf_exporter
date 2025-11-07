# -*- coding: utf-8 -*-
"""
Êîíôèãóðàöèÿ äëÿ ýêñïîðòà ðàñõîäíûõ íàêëàäíûõ èç 1Ñ 7.7 â PDF
"""
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm


# ======================== ПУТЬ К ФАЙЛАМ ========================

# Базовая директория проекта
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Директория для выходных PDF
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

# Директория для логов
LOGS_DIR = os.path.join(BASE_DIR, "logs")

# Путь к файлу конфигурации
CONFIG_FILE = os.path.join(BASE_DIR, "config.txt")


# ======================== НАСТРОЙКИ 1С 7.7 (DBF) ========================

def load_config():
    """
    Çàãðóæàåò íàñòðîéêè èç config.txt
    Âîçâðàùàåò ñëîâàðü ñ êîíôèãóðàöèåé
    """
    try:
        if not os.path.exists(CONFIG_FILE):
            raise FileNotFoundError(f"Файл конфигурации не найден: {CONFIG_FILE}")

        config_data = {}
        with open(CONFIG_FILE, 'r', encoding='cp1251') as f:
            for line in f:
                line = line.strip()
                # Ïðîïóñêàåì êîììåíòàðèè è ïóñòûå ñòðîêè
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        config_data[key.strip()] = value.strip()

        return config_data
    except Exception as e:
        raise Exception(f"Ошибка чтения config.txt: {str(e)}")


def load_database_path():
    """
    Çàãðóæàåò ïóòü ê áàçå äàííûõ èç config.txt
    """
    config_data = load_config()
    if 'DATABASE_PATH' not in config_data:
        raise ValueError("DATABASE_PATH не найден в config.txt")
    return config_data['DATABASE_PATH']


# Путь к базе данных 1С (загружается из config.txt)
try:
    config_data = load_config()
    DATABASE_PATH = config_data.get('DATABASE_PATH', '')
except Exception as e:
    print(f"ОШИБКА: Не удалось загрузить конфигурацию из config.txt: {e}")
    DATABASE_PATH = ""


# ======================== НАСТРОЙКИ PDF ========================

# Размер страницы
PAGE_SIZE = A4
PAGE_WIDTH, PAGE_HEIGHT = A4

# Количество накладных на одной странице (максимум)
MAX_INVOICES_PER_PAGE = 3

# Отступы страницы (в мм)
PAGE_MARGIN_TOP = 10 * mm
PAGE_MARGIN_BOTTOM = 10 * mm
PAGE_MARGIN_LEFT = 10 * mm
PAGE_MARGIN_RIGHT = 10 * mm

# Расстояние между накладными (в мм)
INVOICE_SPACING = 1 * mm

# Ширина области накладной
INVOICE_WIDTH = PAGE_WIDTH - PAGE_MARGIN_LEFT - PAGE_MARGIN_RIGHT

# Доступная высота для размещения накладных
AVAILABLE_HEIGHT = PAGE_HEIGHT - PAGE_MARGIN_TOP - PAGE_MARGIN_BOTTOM

# Параметры динамического дизайна для расчёта высоты накладных
DESIGN_CONFIG = {
    'header_height': 50,           # Высота заголовка накладной (pt)
    'table_row_height': 15,        # Высота строки товара (pt)
    'table_header_height': 20,     # Высота заголовка таблицы (pt)
    'footer_height': 60,           # Итоги + сумма прописью (pt)
    'spacing_internal': 10         # Внутренние отступы (pt)
}

# УСТАРЕВШИЕ параметры (оставлены для совместимости, но не используются в динамической компоновке)
INVOICES_PER_PAGE = 3  # Заменено на MAX_INVOICES_PER_PAGE
INVOICE_HEIGHT = (PAGE_HEIGHT - PAGE_MARGIN_TOP - PAGE_MARGIN_BOTTOM -
                  (INVOICES_PER_PAGE - 1) * INVOICE_SPACING) / INVOICES_PER_PAGE


# ======================== НАСТРОЙКИ ШРИФТОВ ========================

# Директория для шрифтов TTF
FONTS_DIR = os.path.join(BASE_DIR, "fonts")

# Пути к TTF шрифтам (для поддержки кириллицы)
FONT_ARIAL_TTF = os.path.join(FONTS_DIR, "arial.ttf")
FONT_ARIAL_BOLD_TTF = os.path.join(FONTS_DIR, "arialbd.ttf")

# Имена зарегистрированных шрифтов для использования в ReportLab
FONT_HEADER = "ArialBold"
FONT_BODY = "Arial"
FONT_TABLE_HEADER = "ArialBold"
FONT_TABLE_BODY = "Arial"

# Размеры шрифтов
FONT_SIZE_ORDER = 12
FONT_SIZE_INVOICE_HEADER = 10
FONT_SIZE_DATE = 9
FONT_SIZE_TABLE_HEADER = 9
FONT_SIZE_TABLE_BODY = 8
FONT_SIZE_TOTAL = 9
FONT_SIZE_AMOUNT_IN_WORDS = 8


# ======================== НАСТРОЙКИ ТАБЛИЦЫ ========================

# Ширина колонок таблицы (в относительных единицах)
TABLE_COL_WIDTHS = [25, 200, 40, 70, 80, 80]

# Цвета таблицы (Excel-стиль)
TABLE_HEADER_BG_COLOR = colors.Color(68/255, 114/255, 196/255)  # #4472C4
TABLE_HEADER_TEXT_COLOR = colors.white
TABLE_ROW_ALT_COLOR = colors.Color(242/255, 242/255, 242/255)  # #F2F2F2
TABLE_GRID_COLOR = colors.Color(217/255, 217/255, 217/255)  # #D9D9D9
TABLE_BORDER_COLOR = colors.black

# Толщина границ
TABLE_BORDER_WIDTH = 0.5
TABLE_OUTER_BORDER_WIDTH = 1.0

# Заголовки колонок таблицы
TABLE_HEADERS = [
    "№",
    "Товар",
    "Ед.",
    "Количество",
    "Цена с НДС",
    "Сумма с НДС"
]


# ======================== ФОРМАТИРОВАНИЕ ЧИСЕЛ ========================

# Количество десятичных знаков для сумм
DECIMAL_PLACES = 2

# Формат отображения чисел
NUMBER_FORMAT = "{:.2f}"

# Формат для количества (может быть дробным)
QUANTITY_FORMAT = "{:.3f}"


# ======================== НАСТРОЙКИ ЛОГИРОВАНИЯ ========================

# Имя лог-файла
LOG_FILE = os.path.join(LOGS_DIR, "invoices.log")

# Уровень логирования
LOG_LEVEL = "INFO"

# Формат лог-сообщений
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"

# Формат даты в логах
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


# ======================== ФОРМАТЫ ДАЧИ И ВРЕМЕНИ ========================

# Формат даты для отображения (русский стандарт)
DATE_FORMAT_DISPLAY = "%d.%m.%Y"

# Формат даты для имени файла
DATE_FORMAT_FILENAME = "%d.%m.%Y"

# Названия месяцев (родительный падеж для "от ... г.")
MONTH_NAMES_GENITIVE = {
    1: "января",
    2: "февраля",
    3: "марта",
    4: "апреля",
    5: "мая",
    6: "июня",
    7: "июля",
    8: "августа",
    9: "сентября",
    10: "октября",
    11: "ноября",
    12: "декабря"
}


# ======================== ТЕКСТОВЫЕ КОНСТАНТЫ ========================

# Заголовок накладной
INVOICE_TITLE_TEMPLATE = "Расходная накладная № {number}"

# Дата накладной
INVOICE_DATE_TEMPLATE = "от {date} г."

# Итого
TOTAL_LABEL = "Итого:"

# Всего к оплате (сумма прописью)
AMOUNT_IN_WORDS_TEMPLATE = "Всего к оплате: {amount_words}"


# ======================== ИНИЦИАЛИЗАЦИЯ ДИРЕКТОРИЙ ========================

def init_directories():
    """
    Ñîçäàåò íåîáõîäèìûå äèðåêòîðèè, åñëè îíè íå ñóùåñòâóþò
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(LOGS_DIR, exist_ok=True)


# Автоматическая инициализация при импорте
init_directories()
