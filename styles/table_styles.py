# -*- coding: utf-8 -*-
"""
Ñòèëè òàáëèö â Excel-ñòèëå äëÿ PDF
"""
from reportlab.platypus import TableStyle
from reportlab.lib import colors
import config


def create_invoice_table_style(row_count: int) -> TableStyle:
    """
    Ñîçäàòü ñòèëü òàáëèöû äëÿ íàêëàäíîé â Excel-ñòèëå

    Args:
        row_count: Êîëè÷åñòâî ñòðîê â òàáëèöå (âêëþ÷àÿ çàãîëîâîê)

    Returns:
        Îáúåêò TableStyle
    """
    style_commands = []

    # ======================== ЗАГОЛОВОК ТАБЛИЦЫ ========================

    # Фон заголовка (синий #4472C4)
    style_commands.append(
        ('BACKGROUND', (0, 0), (-1, 0), config.TABLE_HEADER_BG_COLOR)
    )

    # Цвет текста заголовка (белый)
    style_commands.append(
        ('TEXTCOLOR', (0, 0), (-1, 0), config.TABLE_HEADER_TEXT_COLOR)
    )

    # Шрифт заголовка (жирный)
    style_commands.append(
        ('FONT', (0, 0), (-1, 0), config.FONT_TABLE_HEADER, config.FONT_SIZE_TABLE_HEADER)
    )

    # Выравнивание заголовка (по центру)
    style_commands.append(
        ('ALIGN', (0, 0), (-1, 0), 'CENTER')
    )

    style_commands.append(
        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE')
    )

    # ======================== СТРОКИ ДАННЫХ ========================

    if row_count > 1:
        # Шрифт данных
        style_commands.append(
            ('FONT', (0, 1), (-1, -2), config.FONT_TABLE_BODY, config.FONT_SIZE_TABLE_BODY)
        )

        # Выравнивание данных
        # Первая колонка (№) - по центру
        style_commands.append(
            ('ALIGN', (0, 1), (0, -2), 'CENTER')
        )

        # Товар - по левому краю
        style_commands.append(
            ('ALIGN', (1, 1), (1, -2), 'LEFT')
        )

        # Ед. - по центру
        style_commands.append(
            ('ALIGN', (2, 1), (2, -2), 'CENTER')
        )

        # Количество, Цена, Сумма - по правому краю
        style_commands.append(
            ('ALIGN', (3, 1), (-1, -2), 'RIGHT')
        )

        # Вертикальное выравнивание
        style_commands.append(
            ('VALIGN', (0, 1), (-1, -2), 'MIDDLE')
        )

        # Чередующийся фон строк (светло-серый #F2F2F2)
        for row in range(1, row_count - 1):
            if row % 2 == 0:  # Четные строки
                style_commands.append(
                    ('BACKGROUND', (0, row), (-1, row), config.TABLE_ROW_ALT_COLOR)
                )

    # ======================== СТРОКА ИТОГО ========================

    if row_count > 1:
        # Фон строки итого (светло-серый #F2F2F2)
        style_commands.append(
            ('BACKGROUND', (0, -1), (-1, -1), config.TABLE_ROW_ALT_COLOR)
        )

        # Шрифт строки итого (жирный)
        style_commands.append(
            ('FONT', (0, -1), (-1, -1), config.FONT_TABLE_HEADER, config.FONT_SIZE_TOTAL)
        )

        # Выравнивание строки итого
        style_commands.append(
            ('ALIGN', (0, -1), (-2, -1), 'RIGHT')
        )

        style_commands.append(
            ('ALIGN', (-1, -1), (-1, -1), 'RIGHT')
        )

        style_commands.append(
            ('VALIGN', (0, -1), (-1, -1), 'MIDDLE')
        )

    # ======================== ГРАНИЦЫ ТАБЛИЦЫ ========================

    # Внешняя граница (жирная черная 1pt)
    style_commands.append(
        ('BOX', (0, 0), (-1, -1), config.TABLE_OUTER_BORDER_WIDTH, config.TABLE_BORDER_COLOR)
    )

    # Внутренние линии сетки (тонкая серая #D9D9D9)
    style_commands.append(
        ('INNERGRID', (0, 0), (-1, -1), config.TABLE_BORDER_WIDTH, config.TABLE_GRID_COLOR)
    )

    # Горизонтальная линия после заголовка (жирная)
    style_commands.append(
        ('LINEBELOW', (0, 0), (-1, 0), config.TABLE_OUTER_BORDER_WIDTH, config.TABLE_BORDER_COLOR)
    )

    # Горизонтальная линия перед итого (жирная)
    if row_count > 1:
        style_commands.append(
            ('LINEABOVE', (0, -1), (-1, -1), config.TABLE_OUTER_BORDER_WIDTH, config.TABLE_BORDER_COLOR)
        )

    # ======================== ОТСТУПЫ В ЯЧЕЙКАХ ========================

    # Отступы для всех ячеек (padding)
    style_commands.append(
        ('LEFTPADDING', (0, 0), (-1, -1), 3)
    )

    style_commands.append(
        ('RIGHTPADDING', (0, 0), (-1, -1), 3)
    )

    style_commands.append(
        ('TOPPADDING', (0, 0), (-1, -1), 2)
    )

    style_commands.append(
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2)
    )

    return TableStyle(style_commands)


def get_column_widths():
    """
    Ïîëó÷èòü øèðèíó êîëîíîê òàáëèöû

    Returns:
        Ñïèñîê øèðèí êîëîíîê
    """
    return config.TABLE_COL_WIDTHS


def get_table_headers():
    """
    Ïîëó÷èòü çàãîëîâêè êîëîíîê òàáëèöû

    Returns:
        Ñïèñîê çàãîëîâêîâ
    """
    return config.TABLE_HEADERS
