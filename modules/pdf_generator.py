# -*- coding: utf-8 -*-
"""
Ìîäóëü äëÿ ãåíåðàöèè PDF ñ ðàñõîäíûìè íàêëàäíûìè
"""
import logging
import os
from datetime import date, datetime
from typing import List
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Table
from num2words import num2words

import config
from modules.invoice_extractor import Invoice
from styles.table_styles import create_invoice_table_style, get_column_widths, get_table_headers


logger = logging.getLogger(__name__)


class PDFGenerator:
    """
    Êëàññ äëÿ ãåíåðàöèè PDF ñ ðàñõîäíûìè íàêëàäíûìè
    """

    def __init__(self):
        """
        Èíèöèàëèçàöèÿ ãåíåðàòîðà PDF
        """
        self._register_fonts()

    def _register_fonts(self):
        """
        Ðåãèñòðàöèÿ øðèôòîâ äëÿ PDF (äëÿ êèðèëëèöû)
        """
        try:
            # Регистрируем TTF шрифты Arial для поддержки кириллицы
            # Arial Regular
            if os.path.exists(config.FONT_ARIAL_TTF):
                pdfmetrics.registerFont(TTFont('Arial', config.FONT_ARIAL_TTF))
                logger.debug(f"Шрифт Arial зарегистрирован: {config.FONT_ARIAL_TTF}")
            else:
                logger.warning(f"Файл шрифта не найден: {config.FONT_ARIAL_TTF}")

            # Arial Bold
            if os.path.exists(config.FONT_ARIAL_BOLD_TTF):
                pdfmetrics.registerFont(TTFont('ArialBold', config.FONT_ARIAL_BOLD_TTF))
                logger.debug(f"Шрифт ArialBold зарегистрирован: {config.FONT_ARIAL_BOLD_TTF}")
            else:
                logger.warning(f"Файл шрифта не найден: {config.FONT_ARIAL_BOLD_TTF}")

        except Exception as e:
            logger.error(f"Ошибка при регистрации шрифтов: {str(e)}")
            # Продолжаем работу, будут использоваться стандартные шрифты

    def _calculate_invoice_height(self, invoice: Invoice) -> float:
        """
        Вычислить реальную высоту накладной в зависимости от количества товаров
        (используя параметры из DESIGN_CONFIG)

        Args:
            invoice: Объект Invoice

        Returns:
            Высота накладной в пунктах
        """
        height = 0.0
        design = config.DESIGN_CONFIG

        # Заголовок накладной (включая номер заказа, если есть)
        height += design['header_height']

        # Заголовок таблицы
        height += design['table_header_height']

        # Строки товаров
        num_items = len(invoice.items)
        height += num_items * design['table_row_height']

        # Итоговая строка таблицы
        height += design['table_row_height']

        # Подвал (итоги + сумма прописью)
        height += design['footer_height']

        # Внутренние отступы
        height += design['spacing_internal']

        logger.debug(f"Вычислена высота накладной {invoice.number}: {height:.1f} пунктов ({num_items} товаров)")
        return height

    def _get_size_category(self, invoice_height: float) -> tuple:
        """
        Определить категорию размещения накладной (1/3, 1/2 или полная страница)

        Args:
            invoice_height: Реальная высота накладной в пунктах

        Returns:
            Кортеж (категория, выделяемая_высота)
            Категория: 'third' (1/3), 'half' (1/2), 'full' (полная страница)
        """
        # Вычитаем spacing из доступной высоты, чтобы 3 накладные 'third' гарантированно поместились
        # Максимум 3 накладные на странице = 2 spacing между ними
        max_spacings = config.MAX_INVOICES_PER_PAGE - 1
        available_for_invoices = config.AVAILABLE_HEIGHT - (max_spacings * config.INVOICE_SPACING)

        # Высоты зон (с учётом spacing)
        zone_third = available_for_invoices / 3
        zone_half = available_for_invoices / 2
        zone_full = available_for_invoices

        if invoice_height <= zone_third:
            return ('third', zone_third)
        elif invoice_height <= zone_half:
            return ('half', zone_half)
        else:
            return ('full', zone_full)

    def _layout_invoices(self, invoices: List[Invoice]) -> List[List[tuple]]:
        """
        Разместить накладные по страницам с динамической компоновкой

        Args:
            invoices: Список накладных

        Returns:
            Список страниц, где каждая страница - список кортежей (накладная, выделенная_высота, реальная_высота)
        """
        pages = []
        current_page = []
        current_page_height = 0
        invoices_on_page = 0

        for invoice in invoices:
            # Рассчитать реальную высоту накладной
            invoice_height = self._calculate_invoice_height(invoice)

            # Определить категорию размещения и выделяемую высоту
            category, allocated_height = self._get_size_category(invoice_height)

            logger.debug(f"Накладная {invoice.number}: высота={invoice_height:.1f} pt, категория={category}, выделено={allocated_height:.1f} pt")

            # Проверить: поместится ли на текущей странице?
            # Spacing добавляется только МЕЖДУ накладными (не после первой)
            needed_height = current_page_height + allocated_height
            if invoices_on_page > 0:
                needed_height += config.INVOICE_SPACING

            # Добавляем tolerance 0.01 pt для учёта погрешности float
            fits_on_page = (needed_height <= config.AVAILABLE_HEIGHT + 0.01 and
                            invoices_on_page < config.MAX_INVOICES_PER_PAGE)

            if not fits_on_page and current_page:
                # Начать новую страницу
                logger.debug(f"Страница заполнена ({invoices_on_page} накладных, {current_page_height:.1f} pt), создаём новую")
                pages.append(current_page)
                current_page = []
                current_page_height = 0
                invoices_on_page = 0

            # Разместить накладную на текущей странице
            current_page.append((invoice, allocated_height, invoice_height))

            # Добавляем spacing ПЕРЕД накладной (если это не первая накладная)
            if invoices_on_page > 0:
                current_page_height += config.INVOICE_SPACING

            # Добавляем высоту самой накладной
            current_page_height += allocated_height
            invoices_on_page += 1

        # Добавить последнюю страницу
        if current_page:
            logger.debug(f"Последняя страница: {invoices_on_page} накладных, {current_page_height:.1f} pt")
            pages.append(current_page)

        logger.info(f"Накладные размещены на {len(pages)} страницах с динамической компоновкой")
        return pages

    def generate_pdf(self, invoices: List[Invoice], output_path: str) -> bool:
        """
        Ãåíåðèðîâàòü PDF ñ íàêëàäíûìè (с динамической компоновкой)

        Args:
            invoices: Ñïèñîê îáúåêòîâ Invoice
            output_path: Ïóòü ê âûõîäíîìó PDF ôàéëó

        Returns:
            True åñëè óñïåøíî, False â ïðîòèâíîì ñëó÷àå
        """
        try:
            logger.info(f"Генерация PDF: {output_path}")
            logger.info(f"Количество накладных: {len(invoices)}")

            # Создаем canvas
            c = canvas.Canvas(output_path, pagesize=A4)

            # Динамическая компоновка накладных по страницам
            pages = self._layout_invoices(invoices)

            # Отрисовка страниц
            for page_num, page in enumerate(pages, 1):
                logger.debug(f"Отрисовка страницы {page_num} ({len(page)} накладных)")

                y_position = config.PAGE_HEIGHT - config.PAGE_MARGIN_TOP

                for invoice_data in page:
                    invoice, allocated_height, real_height = invoice_data

                    logger.debug(f"  Накладная {invoice.number}: Y={y_position:.1f}, выделено={allocated_height:.1f}, реально={real_height:.1f}")

                    # Отрисовка накладной (начиная сверху выделенной зоны)
                    self._generate_invoice(c, invoice, y_position)

                    # Переход к следующей позиции (вниз на выделенную высоту + spacing)
                    y_position -= (allocated_height + config.INVOICE_SPACING)

                # Переход к следующей странице (если есть ещё страницы)
                if page_num < len(pages):
                    c.showPage()

            # Сохраняем PDF
            c.save()

            logger.info(f"PDF создан: {output_path} (страниц: {len(pages)})")
            return True

        except Exception as e:
            logger.error(f"Ошибка при генерации PDF: {str(e)}")
            return False

    def _generate_invoice(self, c: canvas.Canvas, invoice: Invoice, y_top: float):
        """
        Ãåíåðèðîâàòü îäíó íàêëàäíóþ

        Args:
            c: Canvas äëÿ ðèñîâàíèÿ
            invoice: Îáúåêò Invoice
            y_top: Âåðõíÿÿ ïîçèöèÿ íàêëàäíîé íà ñòðàíèöå
        """
        x_left = config.PAGE_MARGIN_LEFT
        current_y = y_top

        # ======================== НОМЕР ЗАКАЗА (если есть) ========================

        if invoice.order_number:
            c.setFont(config.FONT_HEADER, config.FONT_SIZE_ORDER)
            order_text = f"Номер заказа {invoice.order_number}"
            c.drawString(x_left, current_y, order_text)
            current_y -= 15  # Отступ после номера заказа

        # ======================== ЗАГОЛОВОК НАКЛАДНОЙ ========================

        c.setFont(config.FONT_HEADER, config.FONT_SIZE_INVOICE_HEADER)
        invoice_title = config.INVOICE_TITLE_TEMPLATE.format(number=invoice.number)
        c.drawString(x_left, current_y, invoice_title)

        # Дата (справа)
        date_text = self._format_date(invoice.date)
        c.setFont(config.FONT_BODY, config.FONT_SIZE_DATE)
        date_width = c.stringWidth(date_text, config.FONT_BODY, config.FONT_SIZE_DATE)
        c.drawString(config.PAGE_WIDTH - config.PAGE_MARGIN_RIGHT - date_width, current_y, date_text)

        current_y -= 20  # Отступ перед таблицей

        # ======================== ТАБЛИЦА С ТОВАРАМИ ========================

        # Подготовка данных таблицы
        table_data = [get_table_headers()]

        # Добавляем строки товаров
        for idx, item in enumerate(invoice.items, 1):
            # Форматирование количества: для ДРН - целые числа, для МРН - три знака после запятой
            if invoice.doc_type == 'ДРН':
                quantity_str = str(int(item['quantity']))  # Целое число без дробной части
            else:
                quantity_str = config.QUANTITY_FORMAT.format(item['quantity'])  # 3 знака после запятой

            row = [
                str(idx),
                item['item_name'],
                item['unit'],
                quantity_str,
                config.NUMBER_FORMAT.format(item['price']),
                config.NUMBER_FORMAT.format(item['amount'])
            ]
            table_data.append(row)

        # Добавляем строку итого
        total_amount = invoice.get_total_amount()
        total_quantity = sum(item['quantity'] for item in invoice.items)

        # Форматирование итогового количества: для ДРН - целые числа, для МРН - три знака после запятой
        if invoice.doc_type == 'ДРН':
            total_quantity_str = str(int(total_quantity))
        else:
            total_quantity_str = config.QUANTITY_FORMAT.format(total_quantity)

        total_row = [
            "",
            "",
            "",
            total_quantity_str,
            config.TOTAL_LABEL,
            config.NUMBER_FORMAT.format(total_amount)
        ]
        table_data.append(total_row)

        # Создаем таблицу
        table = Table(table_data, colWidths=get_column_widths())
        table.setStyle(create_invoice_table_style(len(table_data)))

        # Рисуем таблицу
        table_width, table_height = table.wrap(config.INVOICE_WIDTH, config.INVOICE_HEIGHT)
        table.drawOn(c, x_left, current_y - table_height)

        current_y -= (table_height + 10)  # Отступ после таблицы

        # ======================== СУММА ПРОПИСЬЮ ========================
        # Закомментировано по запросу пользователя (можно восстановить при необходимости)

        # amount_in_words = self._amount_to_words(total_amount)
        # c.setFont(config.FONT_BODY, config.FONT_SIZE_AMOUNT_IN_WORDS)
        # amount_text = config.AMOUNT_IN_WORDS_TEMPLATE.format(amount_words=amount_in_words)
        # c.drawString(x_left, current_y, amount_text)

    def _format_date(self, dt: datetime) -> str:
        """
        Ôîðìàòèðîâàòü äàòó â ðóññêîì ôîðìàòå

        Args:
            dt: Îáúåêò datetime

        Returns:
            Îòôîðìàòèðîâàííàÿ ñòðîêà äàòû (íàïðèìåð, "от 15 января 2024 г.")
        """
        day = dt.day
        month_name = config.MONTH_NAMES_GENITIVE.get(dt.month, "")
        year = dt.year
        return config.INVOICE_DATE_TEMPLATE.format(date=f"{day} {month_name} {year}")

    def _amount_to_words(self, amount: float) -> str:
        """
        Ïðåîáðàçîâàòü ñóììó â ñëîâà (ðóññêèé ÿçûê)

        Args:
            amount: Ñóììà â ðóáëÿõ

        Returns:
            Ñóììà ïðîïèñüþ (íàïðèìåð, "сто двадцать три рубля 45 копеек")
        """
        try:
            # Разделяем на рубли и копейки
            rubles = int(amount)
            kopecks = int(round((amount - rubles) * 100))

            # Рубли прописью (только число, без валюты)
            rubles_words = num2words(rubles, lang='ru')

            # Склонение слова "рубль"
            if rubles % 100 in [11, 12, 13, 14]:
                ruble_word = "рублей"
            elif rubles % 10 == 1:
                ruble_word = "рубль"
            elif rubles % 10 in [2, 3, 4]:
                ruble_word = "рубля"
            else:
                ruble_word = "рублей"

            # Копейки с числом и склонением
            if kopecks > 0:
                # Склонение слова "копейка"
                if kopecks % 100 in [11, 12, 13, 14]:
                    kopeck_word = "копеек"
                elif kopecks % 10 == 1:
                    kopeck_word = "копейка"
                elif kopecks % 10 in [2, 3, 4]:
                    kopeck_word = "копейки"
                else:
                    kopeck_word = "копеек"

                return f"{rubles_words} {ruble_word} {kopecks:02d} {kopeck_word}"
            else:
                return f"{rubles_words} {ruble_word}"

        except Exception as e:
            logger.error(f"Ошибка при преобразовании суммы в слова: {str(e)}")
            return f"{amount:.2f} руб."

    def generate_filename(self, start_date: date, end_date: date = None) -> str:
        """
        Ãåíåðèðîâàòü èìÿ ôàéëà äëÿ PDF

        Args:
            start_date: Íà÷àëüíàÿ äàòà
            end_date: Êîíå÷íàÿ äàòà (åñëè None, òî èñïîëüçóåòñÿ start_date)

        Returns:
            Èìÿ ôàéëà (íàïðèìåð, "invoices_15.01.2024.pdf")
        """
        if end_date is None or start_date == end_date:
            # Одна дата
            date_str = start_date.strftime(config.DATE_FORMAT_FILENAME)
            filename = f"invoices_{date_str}.pdf"
        else:
            # Диапазон дат
            start_str = start_date.strftime(config.DATE_FORMAT_FILENAME)
            end_str = end_date.strftime(config.DATE_FORMAT_FILENAME)
            filename = f"invoices_{start_str}_-_{end_str}.pdf"

        return os.path.join(config.OUTPUT_DIR, filename)


def create_pdf(invoices: List[Invoice], start_date: date, end_date: date = None) -> str:
    """
    Ñîçäàòü PDF ñ íàêëàäíûìè

    Args:
        invoices: Ñïèñîê îáúåêòîâ Invoice
        start_date: Íà÷àëüíàÿ äàòà
        end_date: Êîíå÷íàÿ äàòà

    Returns:
        Ïóòü ê ñîçäàííîìó ôàéëó èëè ïóñòóþ ñòðîêó â ñëó÷àå îøèáêè
    """
    try:
        generator = PDFGenerator()
        output_path = generator.generate_filename(start_date, end_date)

        if generator.generate_pdf(invoices, output_path):
            return output_path
        return ""

    except Exception as e:
        logger.error(f"Не удалось создать PDF: {str(e)}")
        return ""
