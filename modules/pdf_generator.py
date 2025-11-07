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

        Args:
            invoice: Объект Invoice

        Returns:
            Высота накладной в пунктах
        """
        height = 0.0

        # Номер заказа (если есть)
        if invoice.order_number:
            height += 15  # Высота строки номера заказа

        # Заголовок накладной
        height += 20  # Высота строки заголовка

        # Таблица: заголовок + строки товаров + итоговая строка
        rows_count = 1 + len(invoice.items) + 1  # header + items + total
        row_height = 15  # Средняя высота строки таблицы
        table_height = rows_count * row_height
        height += table_height

        # Сумма прописью
        height += 20  # Высота строки суммы прописью

        # Добавляем небольшой запас
        height += 10

        logger.debug(f"Вычислена высота накладной {invoice.number}: {height} пунктов ({len(invoice.items)} товаров)")
        return height

    def generate_pdf(self, invoices: List[Invoice], output_path: str) -> bool:
        """
        Ãåíåðèðîâàòü PDF ñ íàêëàäíûìè

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

            # Генерируем накладные с динамическим размещением
            page_number = 1
            current_y = config.PAGE_HEIGHT - config.PAGE_MARGIN_TOP
            invoices_on_page = 0

            for idx, invoice in enumerate(invoices):
                # Вычисляем требуемую высоту накладной
                required_height = self._calculate_invoice_height(invoice)

                # Проверяем, помещается ли накладная на текущую позицию
                if current_y - required_height < config.PAGE_MARGIN_BOTTOM:
                    # Накладная не помещается, создаем новую страницу
                    logger.debug(f"Накладная {invoice.number} не помещается, создаем страницу {page_number + 1}")
                    c.showPage()
                    page_number += 1
                    current_y = config.PAGE_HEIGHT - config.PAGE_MARGIN_TOP
                    invoices_on_page = 0

                logger.debug(f"Генерация накладной №{invoice.number} на позиции Y={current_y} (страница {page_number})")

                # Генерируем накладную
                self._generate_invoice(c, invoice, current_y)

                # Сдвигаем позицию вниз
                current_y -= (required_height + config.INVOICE_SPACING)
                invoices_on_page += 1

            # Сохраняем PDF
            c.save()

            logger.info(f"PDF создан: {output_path} (страниц: {page_number})")
            return True

        except Exception as e:
            logger.error(f"Ошибка при генерации PDF: {str(e)}")
            return False

    def _generate_page(self, c: canvas.Canvas, invoices: List[Invoice]):
        """
        Ãåíåðèðîâàòü îäíó ñòðàíèöó ñ íàêëàäíûìè

        Args:
            c: Canvas äëÿ ðèñîâàíèÿ
            invoices: Ñïèñîê íàêëàäíûõ äëÿ ýòîé ñòðàíèöû (äî 3 øòóê)
        """
        # Вычисляем позиции для каждой накладной
        for idx, invoice in enumerate(invoices):
            # Позиция Y для текущей накладной (сверху вниз)
            y_position = (config.PAGE_HEIGHT - config.PAGE_MARGIN_TOP -
                         idx * (config.INVOICE_HEIGHT + config.INVOICE_SPACING))

            logger.debug(f"Генерация накладной №{invoice.number} на позиции Y={y_position}")

            # Генерируем накладную
            self._generate_invoice(c, invoice, y_position)

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
            row = [
                str(idx),
                item['item_name'],
                item['unit'],
                config.QUANTITY_FORMAT.format(item['quantity']),
                config.NUMBER_FORMAT.format(item['price']),
                config.NUMBER_FORMAT.format(item['amount'])
            ]
            table_data.append(row)

        # Добавляем строку итого
        total_amount = invoice.get_total_amount()
        total_row = [
            "",
            "",
            "",
            "",
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

        amount_in_words = self._amount_to_words(total_amount)
        c.setFont(config.FONT_BODY, config.FONT_SIZE_AMOUNT_IN_WORDS)
        amount_text = config.AMOUNT_IN_WORDS_TEMPLATE.format(amount_words=amount_in_words)
        c.drawString(x_left, current_y, amount_text)

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
