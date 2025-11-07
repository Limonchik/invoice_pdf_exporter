# -*- coding: utf-8 -*-
"""
Модуль для чтения расходных накладных из DBF файлов 1С 7.7
"""
import logging
import os
from datetime import date, datetime
from typing import List, Dict, Any, Optional
from dbfread import DBF

logger = logging.getLogger(__name__)


class InvoiceDBFReader:
    """
    Читает расходные накладные напрямую из DBF файлов 1С 7.7
    """

    def __init__(self, database_path: str):
        """
        Инициализация reader'а

        Args:
            database_path: Путь к базе данных 1С 7.7
        """
        self.database_path = database_path

        # Проверяем существование базы
        if not os.path.exists(database_path):
            raise ValueError(f"База данных не найдена: {database_path}")

        # Путь к журналу (всегда 1SJOURN.DBF)
        self.journal_path = os.path.join(database_path, "1SJOURN.DBF")
        if not os.path.exists(self.journal_path):
            raise ValueError(f"Файл журнала не найден: {self.journal_path}")

        # Автоопределение файлов накладных
        logger.info("Автоопределение файлов расходных накладных...")
        self._detect_invoice_files()
        logger.info(f"Типы документов: {self.invoice_doc_types}")

        # Автоопределение справочников
        logger.info("Автоопределение справочников...")
        self._detect_catalog_files()

        logger.debug("DBF Reader инициализирован")

    def _detect_field_structure(self, table, doc_type: str) -> Dict[str, str]:
        """
        Автоматически определяет структуру полей табличной части

        Args:
            table: Объект DBF таблицы
            doc_type: Тип документа

        Returns:
            Словарь с маппингом полей: {'item': 'SP1031', 'unit': 'SP1032', ...}
        """
        fields = table.field_names

        # Получаем первую запись для анализа
        first_record = None
        for record in table:
            first_record = record
            break

        if not first_record:
            raise ValueError(f"Табличная часть для типа {doc_type} пуста")

        # Ищем поля с кодами справочников (короткие строковые значения)
        # и числовые поля (количество, цена, сумма)
        item_field = None
        unit_field = None
        quantity_field = None
        price_field = None
        amount_field = None

        string_fields = []
        numeric_fields = []

        for field in fields:
            if field in ['IDDOC', 'LINENO']:
                continue

            value = first_record.get(field)

            # Строковые поля (потенциально коды справочников)
            if isinstance(value, str):
                value = value.strip()
                if 1 <= len(value) <= 5:
                    string_fields.append((field, value))
            # Числовые поля
            elif isinstance(value, (int, float)) and value > 0:
                numeric_fields.append((field, value))

        # Определяем поля товара и единицы (первые два строковых поля)
        if len(string_fields) >= 1:
            item_field = string_fields[0][0]
        if len(string_fields) >= 2:
            unit_field = string_fields[1][0]

        # СНАЧАЛА проверяем стандартные поля 1С 7.7 (они имеют приоритет!)
        # В 1С 7.7 расходные накладные обычно используют:
        # SP1031: Товар, SP1032: Единица, SP1033: Количество
        # SP4505: Цена с НДС (НЕ SP1036 - это цена БЕЗ НДС!), SP1040: Сумма с НДС
        if 'SP1031' in fields:
            item_field = 'SP1031'
        if 'SP1032' in fields:
            unit_field = 'SP1032'
        if 'SP1033' in fields:
            quantity_field = 'SP1033'
        if 'SP4505' in fields:
            price_field = 'SP4505'  # ИСПРАВЛЕНО: SP4505 содержит цену С НДС
        if 'SP1040' in fields:
            amount_field = 'SP1040'

        # Для МРН (тип 3H8) используем известную структуру
        if doc_type == '3H8':
            # МРН имеет специфическую структуру полей
            if 'SP4533' in fields:
                item_field = 'SP4533'      # Товар
            if 'SP4537' in fields:
                unit_field = 'SP4537'      # Единица измерения (НЕ SP4534!)
            if 'SP4535' in fields:
                quantity_field = 'SP4535'  # Количество
            if 'SP4545' in fields:
                price_field = 'SP4545'     # Цена с НДС за единицу (ИСПРАВЛЕНО: SP4545, НЕ SP4543!)
            if 'SP4542' in fields:
                amount_field = 'SP4542'    # Сумма с НДС

            logger.debug(f"МРН: используем специальный маппинг полей")

        # Если стандартных полей нет, используем эвристику
        elif not quantity_field or not price_field or not amount_field:
            if len(numeric_fields) >= 3:
                # Сортируем по значению
                sorted_numeric = sorted(numeric_fields, key=lambda x: x[1])

                # Количество - второе по величине (пропускаем SP1034 который обычно = 1)
                if not quantity_field:
                    quantity_field = sorted_numeric[1][0] if len(sorted_numeric) > 1 else sorted_numeric[0][0]

                # Сумма - самое большое
                if not amount_field:
                    amount_field = sorted_numeric[-1][0]

                # Цена - пытаемся найти поле, где значение близко к (сумма / количество)
                if not price_field and len(sorted_numeric) >= 3:
                    qty_val = first_record.get(quantity_field, 1)
                    amt_val = sorted_numeric[-1][1]
                    expected_price = amt_val / qty_val if qty_val > 0 else 0

                    best_price_field = None
                    best_diff = float('inf')

                    for field, value in sorted_numeric[1:-1]:
                        diff = abs(value - expected_price)
                        if diff < best_diff:
                            best_diff = diff
                            best_price_field = field

                    price_field = best_price_field if best_price_field else sorted_numeric[1][0]

        # Финальный fallback
        if not item_field:
            item_field = fields[2] if len(fields) > 2 else None
        if not unit_field:
            unit_field = fields[3] if len(fields) > 3 else None
        if not quantity_field:
            quantity_field = fields[4] if len(fields) > 4 else None
        if not price_field:
            price_field = fields[5] if len(fields) > 5 else None
        if not amount_field:
            amount_field = fields[6] if len(fields) > 6 else None

        return {
            'item': item_field,
            'unit': unit_field,
            'quantity': quantity_field,
            'price': price_field,
            'amount': amount_field
        }

    @staticmethod
    def _decode_base36(code: str) -> int:
        """
        Декодирует код из base-36 в десятичное число

        Args:
            code: Код в base-36 (например, 'S3')

        Returns:
            Десятичное число (например, 1011 для 'S3')
        """
        result = 0
        for char in code.upper():
            if char.isdigit():
                result = result * 36 + int(char)
            elif char.isalpha():
                result = result * 36 + (ord(char) - ord('A') + 10)
        return result

    def _detect_invoice_files(self):
        """
        Автоматически определяет файлы расходных накладных через анализ журнала
        """
        try:
            journal = DBF(self.journal_path, encoding='cp1251', ignore_missing_memofile=True)

            # Проверяем, есть ли поле DESCR в журнале
            has_descr = 'DESCR' in journal.field_names

            invoice_types = set()

            if has_descr:
                # Метод 1: Ищем типы документов по описанию (если есть поле DESCR)
                keywords = ['РНК', 'РАСХОДНАЯ', 'НАКЛАДНАЯ']
                for record in journal:
                    descr = record.get('DESCR', '').strip().upper()
                    if any(keyword in descr for keyword in keywords):
                        doc_type = record.get('IDDOCDEF', '').strip()
                        if doc_type:
                            invoice_types.add(doc_type)

                if invoice_types:
                    logger.info(f"Найдены типы документов по описанию: {invoice_types}")

            # Метод 2: Fallback - анализируем номера документов
            if not invoice_types:
                logger.info("Поле DESCR не найдено или пусто. Анализируем номера документов...")
                doc_type_counts = {}

                for record in journal:
                    doc_type = record.get('IDDOCDEF', '').strip()
                    docno = record.get('DOCNO', '').strip().upper()

                    # Ищем документы с префиксами типа расходных накладных
                    # Примеры: "ДРН-", "МРН-", "РНК-", "РН-"
                    # ВАЖНО: СРН (складские расходные накладные) ИСКЛЮЧЕНЫ
                    if doc_type and docno:
                        if any(prefix in docno for prefix in ['ДРН', 'МРН', 'РНК', 'РН-', 'НАКЛ']):
                            # Дополнительная проверка: если это СРН - пропускаем
                            if 'СРН' not in docno:
                                doc_type_counts[doc_type] = doc_type_counts.get(doc_type, 0) + 1

                if doc_type_counts:
                    # Берем ВСЕ найденные типы (не только самый частый)
                    invoice_types.update(doc_type_counts.keys())
                    logger.info(f"Найдены типы по номерам документов: {dict(doc_type_counts)}")

            # Метод 3: Используем стандартный код 'S3' если ничего не нашли
            if not invoice_types:
                logger.warning("Не удалось автоматически определить тип. Использую стандартный код 'S3'")
                invoice_types.add('S3')

            # Сохраняем ВСЕ найденные типы
            self.invoice_doc_types = sorted(invoice_types)

            # Для каждого типа создаем пути к файлам
            self.invoice_files = {}
            for doc_type_code in self.invoice_doc_types:
                file_num = self._decode_base36(doc_type_code)
                header_path = os.path.join(self.database_path, f"DH{file_num}.DBF")
                table_path = os.path.join(self.database_path, f"DT{file_num}.DBF")

                # Проверяем существование файлов
                if os.path.exists(header_path) and os.path.exists(table_path):
                    self.invoice_files[doc_type_code] = {
                        'header_path': header_path,
                        'table_path': table_path,
                        'file_num': file_num
                    }
                    logger.debug(f"Тип {doc_type_code} -> Файлы: DH{file_num}.DBF, DT{file_num}.DBF")
                else:
                    logger.warning(f"Файлы для типа {doc_type_code} не найдены")

            if not self.invoice_files:
                raise ValueError("Не найдено ни одного файла накладных")

            logger.debug(f"Обнаружены типы накладных: {self.invoice_doc_types}")
            logger.info(f"Найдено файлов накладных: {len(self.invoice_files)}")

        except Exception as e:
            logger.error(f"Ошибка при автоопределении файлов накладных: {e}")
            raise ValueError(f"Не удалось определить файлы накладных: {e}")

    def _find_catalogs_for_type(self, table, doc_type: str) -> Dict[str, str]:
        """
        Находит справочники товаров и единиц для конкретного типа документа

        Args:
            table: Объект DBF таблицы
            doc_type: Тип документа

        Returns:
            Словарь с путями к справочникам: {'items': 'path', 'units': 'path'}
        """
        # Получаем первую запись для определения кодов
        first_record = None
        for record in table:
            first_record = record
            break

        if not first_record:
            raise ValueError(f"Табличная часть для типа {doc_type} пуста")

        # Получаем образцы кодов из маппинга полей
        field_mapping = self.field_mappings[doc_type]
        item_field = field_mapping.get('item')
        unit_field = field_mapping.get('unit')

        item_code_sample = ''
        unit_code_sample = ''

        if item_field:
            value = first_record.get(item_field)
            if isinstance(value, str):
                item_code_sample = value.strip()

        if unit_field:
            value = first_record.get(unit_field)
            if isinstance(value, str):
                unit_code_sample = value.strip()

        logger.info(f"Образцы кодов для {doc_type}: товар='{item_code_sample}', единица='{unit_code_sample}'")

        # Ищем справочники по образцам кодов
        sc_files = []
        for filename in os.listdir(self.database_path):
            if filename.upper().startswith('SC') and filename.upper().endswith('.DBF'):
                sc_files.append(os.path.join(self.database_path, filename))

        items_catalog = None
        units_catalog = None

        for sc_file in sc_files:
            try:
                catalog = DBF(sc_file, encoding='cp1251', ignore_missing_memofile=True)
                for rec in catalog:
                    rec_id = rec.get('ID', '').strip()

                    if item_code_sample and rec_id == item_code_sample and not items_catalog:
                        items_catalog = sc_file
                        logger.debug(f"Найден справочник товаров для {doc_type}: {os.path.basename(sc_file)}")

                    if unit_code_sample and rec_id == unit_code_sample and not units_catalog:
                        units_catalog = sc_file
                        logger.debug(f"Найден справочник единиц для {doc_type}: {os.path.basename(sc_file)}")

                    if items_catalog and units_catalog:
                        break

                if items_catalog and units_catalog:
                    break
            except Exception as e:
                logger.debug(f"Не удалось прочитать {sc_file}: {e}")
                continue

        # Fallback: используем первый найденный справочник
        if not items_catalog and sc_files:
            items_catalog = sc_files[0]
            logger.warning(f"Справочник товаров для {doc_type} не найден, используется {os.path.basename(items_catalog)}")

        if not units_catalog and sc_files:
            units_catalog = items_catalog  # используем тот же что и для товаров
            logger.warning(f"Справочник единиц для {doc_type} не найден, используется {os.path.basename(units_catalog)}")

        return {
            'items': items_catalog,
            'units': units_catalog
        }

    def _detect_catalog_files(self):
        """
        Автоматически определяет файлы справочников для каждого типа документа
        """
        try:
            # Для каждого типа документа определяем структуру полей И справочники
            self.field_mappings = {}
            self.catalog_paths = {}  # Хранит справочники для каждого типа

            for doc_type, files in self.invoice_files.items():
                table_path = files['table_path']

                # Читаем табличную часть
                table = DBF(table_path, encoding='cp1251', ignore_missing_memofile=True)

                # Определяем структуру полей для этого типа
                field_mapping = self._detect_field_structure(table, doc_type)
                self.field_mappings[doc_type] = field_mapping

                logger.info(f"Поля типа {doc_type}: товар={field_mapping['item']}, единица={field_mapping['unit']}, "
                           f"количество={field_mapping['quantity']}, цена={field_mapping['price']}, сумма={field_mapping['amount']}")

                # Определяем справочники ДЛЯ ЭТОГО ТИПА
                # Нужно повторно прочитать таблицу, т.к. предыдущий итератор исчерпан
                table = DBF(table_path, encoding='cp1251', ignore_missing_memofile=True)
                catalogs = self._find_catalogs_for_type(table, doc_type)
                self.catalog_paths[doc_type] = catalogs

                logger.info(f"Справочники для {doc_type}: товары={os.path.basename(catalogs['items'])}, "
                           f"единицы={os.path.basename(catalogs['units'])}")

            # Загружаем ВСЕ справочники в память
            self._load_all_catalogs()

        except Exception as e:
            logger.error(f"Ошибка при автоопределении справочников: {e}")
            raise ValueError(f"Не удалось определить справочники: {e}")

    def _load_contractor_catalog(self):
        """Загружает справочник контрагентов (обычно SC174.DBF)"""
        self.contractors_catalog = {}

        # Ищем справочник контрагентов
        contractor_catalog_path = os.path.join(self.database_path, 'SC174.DBF')

        if os.path.exists(contractor_catalog_path):
            try:
                catalog = DBF(contractor_catalog_path, encoding='cp1251', ignore_missing_memofile=True)
                for record in catalog:
                    contractor_id = record.get('ID', '').strip()
                    if contractor_id:
                        # DESCR содержит номер контрагента (например, "265")
                        contractor_number = record.get('DESCR', '').strip()
                        contractor_code = record.get('CODE', '').strip()
                        self.contractors_catalog[contractor_id] = {
                            'number': contractor_number,
                            'code': contractor_code
                        }
                logger.debug(f"Загружено контрагентов: {len(self.contractors_catalog)}")
            except Exception as e:
                logger.warning(f"Не удалось загрузить справочник контрагентов: {e}")
        else:
            logger.warning(f"Справочник контрагентов не найден: {contractor_catalog_path}")

    def _load_all_catalogs(self):
        """Загружает ВСЕ справочники для всех типов документов"""
        self.items_catalogs = {}  # Справочники товаров по типу документа
        self.units_catalogs = {}  # Справочники единиц по типу документа

        # Загружаем справочник контрагентов
        self._load_contractor_catalog()

        for doc_type, catalogs in self.catalog_paths.items():
            # Загружаем товары для этого типа
            items_catalog = {}
            if catalogs['items'] and os.path.exists(catalogs['items']):
                try:
                    catalog = DBF(catalogs['items'], encoding='cp1251', ignore_missing_memofile=True)
                    for record in catalog:
                        item_id = record.get('ID', '').strip()
                        if item_id:
                            # Используем SP149 (полное название) если есть, иначе DESCR (складское)
                            full_name = record.get('SP149', '').strip()
                            short_name = record.get('DESCR', '').strip()
                            items_catalog[item_id] = {
                                'name': full_name if full_name else short_name,
                                'code': record.get('CODE', '').strip(),
                            }
                    logger.debug(f"Загружено товаров для {doc_type}: {len(items_catalog)}")
                except Exception as e:
                    logger.warning(f"Не удалось загрузить справочник товаров для {doc_type}: {e}")

            # Загружаем единицы для этого типа
            units_catalog = {}
            if catalogs['units'] and os.path.exists(catalogs['units']):
                try:
                    catalog = DBF(catalogs['units'], encoding='cp1251', ignore_missing_memofile=True)
                    for record in catalog:
                        unit_id = record.get('ID', '').strip()
                        if unit_id:
                            units_catalog[unit_id] = record.get('DESCR', '').strip()
                    logger.debug(f"Загружено единиц измерения для {doc_type}: {len(units_catalog)}")
                except Exception as e:
                    logger.warning(f"Не удалось загрузить справочник единиц для {doc_type}: {e}")

            self.items_catalogs[doc_type] = items_catalog
            self.units_catalogs[doc_type] = units_catalog

            logger.info(f"Загружено для {doc_type}: товаров={len(items_catalog)}, единиц={len(units_catalog)}")

    def read_invoices(self, start_date: date, end_date: Optional[date] = None) -> List[Dict[str, Any]]:
        """
        Читает расходные накладные за указанный период

        Args:
            start_date: Начальная дата
            end_date: Конечная дата (если None, то используется start_date)

        Returns:
            Список словарей с данными накладных
        """
        if end_date is None:
            end_date = start_date

        logger.info(f"Чтение накладных за период: {start_date} - {end_date}")

        try:
            # Читаем журнал документов
            journal = DBF(self.journal_path, encoding='cp1251', ignore_missing_memofile=True)

            # Находим документы нужного типа (автоопределенные расходные накладные) и даты
            target_doc_ids = []

            for record in journal:
                # Получаем тип документа
                doc_type = record.get('IDDOCDEF', '').strip()

                # Проверяем, что тип документа соответствует расходным накладным
                if doc_type not in self.invoice_doc_types:
                    continue

                # ВАЖНО: Исключаем СРН (складские расходные накладные)
                docno = record.get('DOCNO', '').strip().upper()
                if 'СРН' in docno:
                    logger.debug(f"Пропущен документ СРН: {docno}")
                    continue

                # Проверяем дату
                doc_date = record.get('DATE')
                if not doc_date:
                    continue

                if isinstance(doc_date, datetime):
                    doc_date = doc_date.date()

                if start_date <= doc_date <= end_date:
                    target_doc_ids.append({
                        'iddoc': record.get('IDDOC', '').strip(),
                        'docno': record.get('DOCNO', '').strip(),
                        'date': doc_date,
                        'doc_type': doc_type
                    })

            logger.info(f"Найдено документов в журнале: {len(target_doc_ids)}")

            if not target_doc_ids:
                return []

            # Группируем документы по типам
            docs_by_type = {}
            for doc_info in target_doc_ids:
                doc_type = doc_info.get('doc_type', '')
                if doc_type not in docs_by_type:
                    docs_by_type[doc_type] = []
                docs_by_type[doc_type].append(doc_info)

            # Читаем заголовки и табличные части из всех файлов
            header_map = {}
            table_map = {}

            for doc_type, docs in docs_by_type.items():
                if doc_type not in self.invoice_files:
                    logger.warning(f"Файлы для типа {doc_type} не найдены, пропускаем {len(docs)} документов")
                    continue

                files = self.invoice_files[doc_type]
                header_path = files['header_path']
                table_path = files['table_path']

                logger.debug(f"Чтение типа {doc_type} из {os.path.basename(header_path)}")

                # Читаем заголовки
                headers = DBF(header_path, encoding='cp1251', ignore_missing_memofile=True)
                target_iddocs = [d['iddoc'] for d in docs]

                for record in headers:
                    iddoc = record.get('IDDOC', '').strip()
                    if iddoc in target_iddocs:
                        header_map[iddoc] = record

                # Читаем табличную часть
                tables = DBF(table_path, encoding='cp1251', ignore_missing_memofile=True)

                for record in tables:
                    iddoc = record.get('IDDOC', '').strip()
                    if iddoc in header_map:
                        if iddoc not in table_map:
                            table_map[iddoc] = []
                        table_map[iddoc].append(record)

            logger.info(f"Найдено заголовков: {len(header_map)}")
            logger.info(f"Найдено документов с табличной частью: {len(table_map)}")

            # Собираем результат
            invoices = []

            for doc_info in target_doc_ids:
                iddoc = doc_info['iddoc']

                if iddoc not in header_map:
                    logger.warning(f"Заголовок не найден для {iddoc}")
                    continue

                header = header_map[iddoc]
                items = table_map.get(iddoc, [])

                # Преобразуем товарные позиции
                decoded_items = []
                doc_type = doc_info['doc_type']
                for item_record in items:
                    decoded_items.append(self._decode_item(item_record, doc_type))

                # Извлекаем номер контрагента из заголовка (SP1012 для ДРН, SP4515 для МРН)
                contractor_number = self._get_contractor_number(header, doc_type)

                invoice = {
                    'number': doc_info['docno'],
                    'date': doc_info['date'],
                    'iddoc': iddoc,
                    'header': header,
                    'items': decoded_items,
                    'total_amount': self._get_total_amount(header),
                    'contractor_number': contractor_number
                }

                invoices.append(invoice)

            logger.info(f"[OK] Извлечено накладных: {len(invoices)}")
            return invoices

        except Exception as e:
            logger.error(f"Ошибка при чтении DBF: {str(e)}", exc_info=True)
            return []

    def _decode_item(self, item_record: Dict[str, Any], doc_type: str) -> Dict[str, Any]:
        """
        Декодирует товарную позицию (преобразует коды в названия)

        Args:
            item_record: Запись из табличной части
            doc_type: Тип документа для выбора правильного маппинга полей

        Returns:
            Словарь с декодированными данными
        """
        # Получаем маппинг полей для этого типа документа
        field_mapping = self.field_mappings.get(doc_type, {})

        # Получаем ПРАВИЛЬНЫЕ справочники для этого типа документа
        items_catalog = self.items_catalogs.get(doc_type, {})
        units_catalog = self.units_catalogs.get(doc_type, {})

        # Код товара
        item_field = field_mapping.get('item', 'SP1031')
        item_code = item_record.get(item_field, '').strip() if isinstance(item_record.get(item_field), str) else ''
        item_info = items_catalog.get(item_code, {})
        item_name = item_info.get('name', f'[Товар {item_code}]')

        # Код единицы измерения
        unit_field = field_mapping.get('unit', 'SP1032')
        unit_code = item_record.get(unit_field, '').strip() if isinstance(item_record.get(unit_field), str) else ''
        unit_name = units_catalog.get(unit_code, unit_code)

        # Числовые значения
        quantity_field = field_mapping.get('quantity', 'SP1033')
        price_field = field_mapping.get('price', 'SP1036')
        amount_field = field_mapping.get('amount', 'SP1040')

        # Читаем числовые значения
        quantity = float(item_record.get(quantity_field, 0) or 0)
        price = float(item_record.get(price_field, 0) or 0)
        amount = float(item_record.get(amount_field, 0) or 0)

        return {
            'item_name': item_name,
            'unit': unit_name,
            'quantity': quantity,
            'price': price,
            'amount': amount
        }

    def _get_contractor_number(self, header: Dict[str, Any], doc_type: str) -> str:
        """
        Извлекает номер контрагента из заголовка

        Args:
            header: Запись заголовка документа
            doc_type: Тип документа (например, 'S3' для ДРН, '3H8' для МРН)

        Returns:
            Номер контрагента или пустая строка
        """
        contractor_code = ''

        # Для разных типов документов контрагент хранится в разных полях
        if doc_type == '3H8':  # МРН
            # В МРН контрагент (номер заказа) в поле SP4509
            contractor_code = header.get('SP4509', '').strip() if isinstance(header.get('SP4509'), str) else ''
        else:  # ДРН и другие
            # В расходных накладных контрагент обычно в SP1012
            contractor_code = header.get('SP1012', '').strip() if isinstance(header.get('SP1012'), str) else ''

        if contractor_code and hasattr(self, 'contractors_catalog'):
            contractor_info = self.contractors_catalog.get(contractor_code, {})
            contractor_number = contractor_info.get('number', '')
            if contractor_number:
                return contractor_number

        return ''

    def _get_total_amount(self, header: Dict[str, Any]) -> float:
        """
        Извлекает общую сумму из заголовка

        Args:
            header: Запись заголовка документа

        Returns:
            Общая сумма
        """
        # В DH1011 общая сумма обычно в поле SP1040 (или SP1037, SP1039)
        # Нужно проверить, какое именно поле содержит итоговую сумму с НДС
        for field_name in ['SP1040', 'SP1039', 'SP1037']:
            value = header.get(field_name, 0)
            if value and value > 0:
                return float(value)

        return 0.0


def create_reader(database_path: str) -> InvoiceDBFReader:
    """
    Создать объект reader'а

    Args:
        database_path: Путь к базе данных 1С

    Returns:
        Объект InvoiceDBFReader

    Raises:
        ValueError: Если не удалось создать reader
    """
    return InvoiceDBFReader(database_path)
