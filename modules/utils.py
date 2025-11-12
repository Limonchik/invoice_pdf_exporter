# -*- coding: utf-8 -*-
"""
Âñïîìîãàòåëüíûå ôóíêöèè
"""
import logging
import os
from datetime import datetime, date
from typing import Optional, Tuple
import config


def setup_logging():
    """
    Íàñòðîèòü ëîãèðîâàíèå
    """
    # Создаем директорию для логов, если не существует
    os.makedirs(config.LOGS_DIR, exist_ok=True)

    # Настройка логирования
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL),
        format=config.LOG_FORMAT,
        datefmt=config.LOG_DATE_FORMAT,
        handlers=[
            # Лог в файл (UTF-8 для поддержки всех символов)
            logging.FileHandler(config.LOG_FILE, encoding='utf-8'),
            # Лог в консоль
            logging.StreamHandler()
        ]
    )

    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("Система экспорта накладных 1С 7.7 запущена")
    logger.info("=" * 60)


def parse_date(date_str: str) -> Optional[date]:
    """
    Ðàçîáðàòü ñòðîêó äàòû â îáúåêò date

    Args:
        date_str: Ñòðîêà äàòû â ôîðìàòå DD.MM.YYYY

    Returns:
        Îáúåêò date èëè None â ñëó÷àå îøèáêè
    """
    try:
        dt = datetime.strptime(date_str, config.DATE_FORMAT_DISPLAY)
        return dt.date()
    except ValueError:
        return None


def parse_date_range(date_range_str: str) -> Optional[Tuple[date, date]]:
    """
    Ðàçîáðàòü ñòðîêó äèàïàçîíà äàò

    Args:
        date_range_str: Ñòðîêà â ôîðìàòå "DD.MM.YYYY - DD.MM.YYYY"
                        èëè "DD.MM.YYYY-DD.MM.YYYY"

    Returns:
        Êîðòåæ (start_date, end_date) èëè None â ñëó÷àå îøèáêè
    """
    try:
        # Убираем пробелы и разделяем
        parts = date_range_str.replace(" ", "").split("-")

        if len(parts) != 2:
            return None

        start_date = parse_date(parts[0])
        end_date = parse_date(parts[1])

        if start_date and end_date:
            return (start_date, end_date)

        return None
    except Exception:
        return None


def format_date_display(dt: date) -> str:
    """
    Îòôîðìàòèðîâàòü äàòó äëÿ îòîáðàæåíèÿ

    Args:
        dt: Îáúåêò date

    Returns:
        Ñòðîêà äàòû â ôîðìàòå DD.MM.YYYY
    """
    return dt.strftime(config.DATE_FORMAT_DISPLAY)


def validate_database_path(path: str) -> bool:
    """
    Ïðîâåðèòü, ñóùåñòâóåò ëè ïóòü ê áàçå äàííûõ

    Args:
        path: Ïóòü ê áàçå äàííûõ

    Returns:
        True åñëè ïóòü ñóùåñòâóåò
    """
    return os.path.exists(path)


def get_today_date() -> date:
    """
    Ïîëó÷èòü ñåãîäíÿøíþþ äàòó

    Returns:
        Îáúåêò date
    """
    return date.today()


def ensure_output_directory():
    """
    Óáåäèòüñÿ, ÷òî äèðåêòîðèÿ âûõîäíûõ ôàéëîâ ñóùåñòâóåò
    """
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)


def clear_screen():
    """
    Î÷èñòèòü ýêðàí êîíñîëè
    """
    os.system('cls' if os.name == 'nt' else 'clear')


def format_file_size(size_bytes: int) -> str:
    """
    Îòôîðìàòèðîâàòü ðàçìåð ôàéëà

    Args:
        size_bytes: Ðàçìåð â áàéòàõ

    Returns:
        Ñòðîêà ñ ðàçìåðîì (íàïðèìåð, "1.23 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def get_file_info(file_path: str) -> dict:
    """
    Ïîëó÷èòü èíôîðìàöèþ î ôàéëå

    Args:
        file_path: Ïóòü ê ôàéëó

    Returns:
        Ñëîâàðü ñ èíôîðìàöèåé î ôàéëå
    """
    try:
        if not os.path.exists(file_path):
            return {}

        stat = os.stat(file_path)
        return {
            'path': file_path,
            'size': stat.st_size,
            'size_formatted': format_file_size(stat.st_size),
            'created': datetime.fromtimestamp(stat.st_ctime),
            'modified': datetime.fromtimestamp(stat.st_mtime)
        }
    except Exception:
        return {}


def truncate_string(s: str, max_length: int, suffix: str = "...") -> str:
    """
    Îáðåçàòü ñòðîêó äî ìàêñèìàëüíîé äëèíû

    Args:
        s: Èñõîäíàÿ ñòðîêà
        max_length: Ìàêñèìàëüíàÿ äëèíà
        suffix: Ñóôôèêñ äëÿ îáðåçàííîé ñòðîêè

    Returns:
        Îáðåçàííàÿ ñòðîêà
    """
    if len(s) <= max_length:
        return s
    return s[:max_length - len(suffix)] + suffix


def truncate_text(text: str, col_width: float, font_name: str, font_size: float,
                  cell_padding_left: float = 4, cell_padding_right: float = 4) -> str:
    """
    Обрезает текст с учётом реальной ширины в PDF и добавляет троеточие

    Функция точно рассчитывает, сколько символов текста поместится в колонку
    заданной ширины с учётом padding и шрифта. Если текст не помещается,
    обрезает его и добавляет троеточие в пределах доступной ширины.

    Args:
        text: Исходный текст для отображения
        col_width: Ширина колонки в единицах ReportLab (points)
        font_name: Название шрифта (например, 'Arial')
        font_size: Размер шрифта в пунктах
        cell_padding_left: Отступ слева в пикселях (по умолчанию 4px)
        cell_padding_right: Отступ справа в пикселях (по умолчанию 4px)

    Returns:
        Обрезанный текст с троеточием или исходный текст, если помещается

    Example:
        >>> truncate_text("Длинное название товара", 100, "Arial", 11)
        "Длинное назва..."
    """
    from reportlab.pdfbase import pdfmetrics

    # Доступная ширина = ширина колонки - отступы
    available_width = col_width - cell_padding_left - cell_padding_right

    # Рассчитываем ширину исходного текста
    text_width = pdfmetrics.stringWidth(text, font_name, font_size)

    # Если текст помещается, возвращаем как есть
    if text_width <= available_width:
        return text

    # Рассчитываем ширину троеточия
    ellipsis = config.ELLIPSIS
    ellipsis_width = pdfmetrics.stringWidth(ellipsis, font_name, font_size)

    # Доступная ширина для текста (без троеточия)
    text_available_width = available_width - ellipsis_width

    # Если даже троеточие не помещается, возвращаем пустую строку
    if text_available_width <= 0:
        return ellipsis

    # Обрезаем текст посимвольно до тех пор, пока не поместится с троеточием
    # Начинаем с приблизительной оценки количества символов
    avg_char_width = text_width / len(text) if len(text) > 0 else font_size / 2
    estimated_chars = int(text_available_width / avg_char_width)

    # Гарантируем, что не выходим за пределы строки
    estimated_chars = max(1, min(estimated_chars, len(text)))

    # Точная подгонка: уменьшаем количество символов, пока текст + троеточие не поместится
    truncated = text[:estimated_chars]
    while len(truncated) > 0:
        truncated_width = pdfmetrics.stringWidth(truncated, font_name, font_size)
        if truncated_width <= text_available_width:
            break
        truncated = truncated[:-1]

    return truncated + ellipsis
