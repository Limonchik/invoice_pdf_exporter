# -*- coding: utf-8 -*-
"""
Модуль для парсинга CSV файлов с данными накладных, экспортированных из 1С 7.7
"""
import logging
import os
from datetime import datetime
from typing import List, Optional
from modules.invoice_extractor import Invoice


logger = logging.getLogger(__name__)


def parse_invoices_csv(csv_file_path: str) -> List[Invoice]:
    """
    Парсит CSV файл с накладными

    Формат CSV:
        HEADER|номер|дата|общая_сумма
        ITEM|товар|единица|количество|цена|сумма
        ITEM|...
        HEADER|...

    Args:
        csv_file_path: Путь к CSV файлу

    Returns:
        Список объектов Invoice

    Raises:
        FileNotFoundError: Если файл не найден
        ValueError: Если формат файла неверный
    """
    if not os.path.exists(csv_file_path):
        raise FileNotFoundError(f"CSV файл не найден: {csv_file_path}")

    invoices = []
    current_invoice = None

    try:
        # Читаем файл с кодировкой cp1251 (1С использует эту кодировку)
        with open(csv_file_path, 'r', encoding='cp1251') as f:
            line_num = 0

            for line in f:
                line_num += 1
                line = line.strip()

                # Пропускаем пустые строки
                if not line:
                    continue

                # Разбиваем строку по разделителю |
                parts = line.split('|')

                if len(parts) < 2:
                    logger.warning(f"Строка {line_num}: недостаточно полей, пропускаем")
                    continue

                record_type = parts[0]

                if record_type == "HEADER":
                    # Заголовок накладной
                    if len(parts) < 4:
                        logger.warning(f"Строка {line_num}: неполный заголовок, пропускаем")
                        continue

                    # Сохраняем предыдущую накладную, если есть
                    if current_invoice is not None:
                        invoices.append(current_invoice)

                    # Парсим заголовок
                    number = parts[1]
                    date_str = parts[2]
                    # total_amount = parts[3]  # Общая сумма (рассчитаем из строк)

                    # Преобразуем дату
                    try:
                        # Формат даты из 1С: YYYY-MM-DD HH:MM:SS или DD.MM.YYYY
                        if '.' in date_str:
                            # Формат DD.MM.YYYY
                            date_obj = datetime.strptime(date_str.split()[0], '%d.%m.%Y')
                        else:
                            # Формат YYYY-MM-DD
                            date_obj = datetime.strptime(date_str.split()[0], '%Y-%m-%d')
                    except Exception as e:
                        logger.warning(f"Строка {line_num}: ошибка парсинга даты '{date_str}': {e}")
                        date_obj = datetime.now()

                    # Создаем новую накладную
                    current_invoice = Invoice(
                        number=number,
                        date=date_obj,
                        order_number=""
                    )

                    logger.debug(f"Накладная: {number} от {date_obj}")

                elif record_type == "ITEM":
                    # Строка товара
                    if current_invoice is None:
                        logger.warning(f"Строка {line_num}: товар без заголовка, пропускаем")
                        continue

                    if len(parts) < 6:
                        logger.warning(f"Строка {line_num}: неполная строка товара, пропускаем")
                        continue

                    # Парсим данные товара
                    item_name = parts[1]
                    unit = parts[2]
                    quantity_str = parts[3]
                    price_str = parts[4]
                    amount_str = parts[5]

                    # Преобразуем числа
                    try:
                        quantity = float(quantity_str.replace(',', '.'))
                        price = float(price_str.replace(',', '.'))
                        amount = float(amount_str.replace(',', '.'))
                    except ValueError as e:
                        logger.warning(f"Строка {line_num}: ошибка преобразования чисел: {e}")
                        continue

                    # Добавляем товар в накладную
                    current_invoice.add_item(
                        item_name=item_name,
                        unit=unit,
                        quantity=quantity,
                        price=price,
                        amount=amount
                    )

                    logger.debug(f"  Товар: {item_name} - {quantity} {unit} x {price} = {amount}")

                else:
                    logger.warning(f"Строка {line_num}: неизвестный тип записи '{record_type}'")

            # Сохраняем последнюю накладную
            if current_invoice is not None:
                invoices.append(current_invoice)

    except Exception as e:
        logger.error(f"Ошибка при парсинге CSV файла: {str(e)}", exc_info=True)
        raise ValueError(f"Не удалось распарсить CSV файл: {str(e)}")

    logger.info(f"Распарсено накладных: {len(invoices)}")

    return invoices


def validate_invoice(invoice: Invoice) -> bool:
    """
    Проверяет корректность данных накладной

    Args:
        invoice: Объект накладной для проверки

    Returns:
        True если данные корректны
    """
    # Проверка наличия обязательных полей
    if not invoice.number:
        logger.warning(f"Накладная без номера")
        return False

    if not invoice.date:
        logger.warning(f"Накладная {invoice.number} без даты")
        return False

    # Проверка наличия товаров
    if len(invoice.items) == 0:
        logger.warning(f"Накладная {invoice.number} без товарных позиций")
        return False

    # Проверка корректности сумм
    calculated_total = sum(item['amount'] for item in invoice.items)
    actual_total = invoice.get_total_amount()

    # Допускаем небольшую погрешность из-за округления
    if abs(calculated_total - actual_total) > 0.01:
        logger.warning(
            f"Накладная {invoice.number}: расхождение в суммах "
            f"(рассчитано: {calculated_total}, фактически: {actual_total})"
        )
        # Не считаем это критической ошибкой
        # return False

    return True


def parse_and_validate(csv_file_path: str) -> List[Invoice]:
    """
    Парсит и валидирует накладные из CSV файла

    Args:
        csv_file_path: Путь к CSV файлу

    Returns:
        Список валидных объектов Invoice
    """
    invoices = parse_invoices_csv(csv_file_path)

    # Фильтруем только валидные накладные
    valid_invoices = [inv for inv in invoices if validate_invoice(inv)]

    if len(valid_invoices) < len(invoices):
        logger.warning(
            f"Отфильтровано невалидных накладных: {len(invoices) - len(valid_invoices)}"
        )

    return valid_invoices
