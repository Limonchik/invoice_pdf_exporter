# -*- coding: utf-8 -*-
"""
Ñòèëè òàáëèö â Excel-ñòèëå äëÿ PDF
"""
from reportlab.platypus import TableStyle
from reportlab.lib import colors
import config


def create_minimal_table_style(row_count: int) -> TableStyle:
    """
    Ñòèëü òàáëèöû MINIMAL - ìàêñèìàëüíàÿ ýêîíîìèÿ ÷åðíèë

    Args:
        row_count: Êîëè÷åñòâî ñòðîê â òàáëèöå (âêëþ÷àÿ çàãîëîâîê)

    Returns:
        Îáúåêò TableStyle
    """
    style_commands = []

    # ======================== ЗАГОЛОВОК ТАБЛИЦЫ ========================

    # БЕЗ ФОНА для экономии чернил

    # Цвет текста заголовка (черный)
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

        # БЕЗ ФОНА для экономии чернил
        # Вместо фона используем очень светлые разделительные линии для визуального разделения
        for row in range(1, row_count - 1):
            if row % 2 == 0:  # Четные строки - добавляем тонкую светлую линию снизу
                style_commands.append(
                    ('LINEBELOW', (0, row), (-1, row), 0.25, config.TABLE_DOTTED_LINE_COLOR)
                )

    # ======================== СТРОКА ИТОГО ========================

    if row_count > 1:
        # БЕЗ ФОНА для экономии чернил

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

    # Внешняя граница (тонкая черная 0.25pt для экономии чернил)
    style_commands.append(
        ('BOX', (0, 0), (-1, -1), 0.25, config.TABLE_BORDER_COLOR)
    )

    # Внутренние линии сетки (тонкая серая 0.25pt #D9D9D9)
    style_commands.append(
        ('INNERGRID', (0, 0), (-1, -1), 0.25, config.TABLE_GRID_COLOR)
    )

    # Горизонтальная линия после заголовка (утолщенная для выделения)
    style_commands.append(
        ('LINEBELOW', (0, 0), (-1, 0), 1.5, config.TABLE_BORDER_COLOR)
    )

    # Двойная горизонтальная линия перед итого (классический бухгалтерский стиль)
    if row_count > 1:
        # Первая линия двойной границы (под последней строкой данных)
        style_commands.append(
            ('LINEBELOW', (0, -2), (-1, -2), 0.75, config.TABLE_BORDER_COLOR)
        )
        # Вторая линия двойной границы (над строкой итого)
        style_commands.append(
            ('LINEABOVE', (0, -1), (-1, -1), 0.75, config.TABLE_BORDER_COLOR)
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


def create_classic_table_style(row_count: int) -> TableStyle:
    """
    Ñòèëü òàáëèöû CLASSIC - óëó÷øåííàÿ ÷èòàåìîñòü ñ ìèíèìàëüíûì ðàñõîäîì ÷åðíèë

    Args:
        row_count: Êîëè÷åñòâî ñòðîê â òàáëèöå (âêëþ÷àÿ çàãîëîâîê)

    Returns:
        Îáúåêò TableStyle
    """
    style_commands = []

    # Цвета для classic стиля (очень светлые фоны)
    HEADER_BG = colors.Color(245/255, 245/255, 245/255)  # #F5F5F5 (~3% чернил)
    ALT_ROW_BG = colors.Color(250/255, 250/255, 250/255)  # #FAFAFA (~1-2% чернил)
    GRID_COLOR = colors.Color(204/255, 204/255, 204/255)  # #CCCCCC (чуть заметнее)

    # ======================== ЗАГОЛОВОК ТАБЛИЦЫ ========================

    # Фон заголовка (очень светлый серый)
    style_commands.append(
        ('BACKGROUND', (0, 0), (-1, 0), HEADER_BG)
    )

    # Цвет текста заголовка (черный)
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

        # Чередующиеся фоны строк для улучшения читаемости
        for row in range(1, row_count - 1):
            if row % 2 == 0:  # Четные строки - очень светлый фон
                style_commands.append(
                    ('BACKGROUND', (0, row), (-1, row), ALT_ROW_BG)
                )

    # ======================== СТРОКА ИТОГО ========================

    if row_count > 1:
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

    # Внешняя граница (чуть толще для структурности)
    style_commands.append(
        ('BOX', (0, 0), (-1, -1), 0.5, config.TABLE_BORDER_COLOR)
    )

    # Внутренние линии сетки (чуть заметнее)
    style_commands.append(
        ('INNERGRID', (0, 0), (-1, -1), 0.3, GRID_COLOR)
    )

    # Горизонтальная линия после заголовка (утолщенная для выделения)
    style_commands.append(
        ('LINEBELOW', (0, 0), (-1, 0), 2.0, config.TABLE_BORDER_COLOR)
    )

    # Двойная горизонтальная линия перед итого (классический бухгалтерский стиль)
    if row_count > 1:
        # Первая линия двойной границы (под последней строкой данных)
        style_commands.append(
            ('LINEBELOW', (0, -2), (-1, -2), 0.75, config.TABLE_BORDER_COLOR)
        )
        # Вторая линия двойной границы (над строкой итого)
        style_commands.append(
            ('LINEABOVE', (0, -1), (-1, -1), 0.75, config.TABLE_BORDER_COLOR)
        )

    # ======================== ОТСТУПЫ В ЯЧЕЙКАХ ========================

    # Отступы для всех ячеек (больше воздуха)
    style_commands.append(
        ('LEFTPADDING', (0, 0), (-1, -1), 4)
    )

    style_commands.append(
        ('RIGHTPADDING', (0, 0), (-1, -1), 4)
    )

    style_commands.append(
        ('TOPPADDING', (0, 0), (-1, -1), 3)
    )

    style_commands.append(
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3)
    )

    return TableStyle(style_commands)


def create_invoice_table_style(row_count: int) -> TableStyle:
    """
    Ñîçäàòü ñòèëü òàáëèöû äëÿ íàêëàäíîé â Excel-ñòèëå
    (óíèâåðñàëüíàÿ ôóíêöèÿ, âûáèðàþùàÿ ñòèëü èç êîíôèãà)

    Args:
        row_count: Êîëè÷åñòâî ñòðîê â òàáëèöå (âêëþ÷àÿ çàãîëîâîê)

    Returns:
        Îáúåêò TableStyle
    """
    table_style = getattr(config, 'TABLE_STYLE', 'classic').lower()

    if table_style == 'minimal':
        return create_minimal_table_style(row_count)
    elif table_style == 'classic':
        return create_classic_table_style(row_count)
    else:
        # По умолчанию используем classic
        return create_classic_table_style(row_count)


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
