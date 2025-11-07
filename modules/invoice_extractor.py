# -*- coding: utf-8 -*-
"""
Модуль для извлечения данных расходных накладных из 1С 7.7
Читает данные напрямую из DBF файлов базы
"""
import logging
import os
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from pathlib import Path

from modules.dbf_reader import create_reader

logger = logging.getLogger(__name__)


class Invoice:
    """
    Класс для хранения данных расходной накладной
    """

    def __init__(self, number: str, date: datetime, order_number: str = ""):
        """
        Инициализация накладной

        Args:
            number: Номер накладной
            date: Дата накладной
            order_number: Номер заказа (опционально)
        """
        self.number = number
        self.date = date
        self.order_number = order_number
        self.items = []  # Список товарных позиций

    def add_item(self, item_name: str, unit: str, quantity: float, price: float, amount: float):
        """
        Добавить товарную позицию в накладную

        Args:
            item_name: Название товара
            unit: Единица измерения
            quantity: Количество
            price: Цена с НДС
            amount: Сумма с НДС
        """
        self.items.append({
            'item_name': item_name,
            'unit': unit,
            'quantity': quantity,
            'price': price,
            'amount': amount
        })

    def get_total_amount(self) -> float:
        """
        Получить общую сумму накладной

        Returns:
            Общая сумма всех позиций
        """
        return sum(item['amount'] for item in self.items)

    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразовать накладную в словарь

        Returns:
            Словарь с данными накладной
        """
        return {
            'number': self.number,
            'date': self.date,
            'order_number': self.order_number,
            'items': self.items,
            'total_amount': self.get_total_amount()
        }

    def __repr__(self):
        return f"Invoice(number='{self.number}', date={self.date}, items={len(self.items)})"


class InvoiceExtractor:
    """
    Класс для извлечения расходных накладных из 1С 7.7
    Читает данные напрямую из DBF файлов базы данных
    """

    def __init__(self, database_path: str, username: str = "", password: str = ""):
        """
        Инициализация извлекателя накладных

        Args:
            database_path: Путь к базе данных 1С
            username: Имя пользователя (не используется в DBF подходе, оставлен для совместимости)
            password: Пароль (не используется в DBF подходе, оставлен для совместимости)
        """
        self.database_path = database_path

        # Создаем DBF reader (выбросит исключение при ошибке)
        self.dbf_reader = create_reader(database_path)

        logger.debug("InvoiceExtractor инициализирован (DBF подход)")

    def extract_invoices(self, start_date: date, end_date: Optional[date] = None) -> List[Invoice]:
        """
        Извлечь расходные накладные за указанный период

        Args:
            start_date: Начальная дата
            end_date: Конечная дата (если None, то используется start_date)

        Returns:
            Список объектов Invoice
        """
        if end_date is None:
            end_date = start_date

        try:
            logger.info(f"Извлечение накладных за период: {start_date} - {end_date}")

            # Читаем накладные из DBF
            raw_invoices = self.dbf_reader.read_invoices(start_date, end_date)

            # Преобразуем в объекты Invoice
            invoices = []
            for raw_inv in raw_invoices:
                # Создаем объект Invoice
                # Используем contractor_number как order_number
                contractor_number = raw_inv.get('contractor_number', '')
                invoice = Invoice(
                    number=raw_inv['number'],
                    date=raw_inv['date'],
                    order_number=contractor_number
                )

                # Добавляем товарные позиции
                for item in raw_inv['items']:
                    invoice.add_item(
                        item_name=item['item_name'],
                        unit=item['unit'],
                        quantity=item['quantity'],
                        price=item['price'],
                        amount=item['amount']
                    )

                invoices.append(invoice)

            logger.info(f"[OK] Извлечено накладных: {len(invoices)}")
            return invoices

        except Exception as e:
            logger.error(f"Ошибка при извлечении накладных: {str(e)}", exc_info=True)
            return []

    def extract_invoices_for_today(self) -> List[Invoice]:
        """
        Извлечь накладные за сегодня

        Returns:
            Список объектов Invoice
        """
        today = date.today()
        return self.extract_invoices(today, today)

    def extract_invoices_for_date(self, target_date: date) -> List[Invoice]:
        """
        Извлечь накладные за конкретную дату

        Args:
            target_date: Дата для поиска

        Returns:
            Список объектов Invoice
        """
        return self.extract_invoices(target_date, target_date)

    def extract_invoices_for_range(self, start_date: date, end_date: date) -> List[Invoice]:
        """
        Извлечь накладные за диапазон дат

        Args:
            start_date: Начальная дата
            end_date: Конечная дата

        Returns:
            Список объектов Invoice
        """
        return self.extract_invoices(start_date, end_date)


def create_extractor(database_path: str, username: str = "", password: str = "") -> Optional[InvoiceExtractor]:
    """
    Создать объект извлекателя накладных

    Args:
        database_path: Путь к базе данных 1С
        username: Имя пользователя (не используется в DBF подходе)
        password: Пароль (не используется в DBF подходе)

    Returns:
        Объект InvoiceExtractor или None в случае ошибки
    """
    try:
        return InvoiceExtractor(database_path, username, password)
    except Exception as e:
        logger.error(f"Ошибка при создании extractor: {str(e)}")
        return None
