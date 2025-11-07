# -*- coding: utf-8 -*-
"""
Главный модуль для экспорта расходных накладных из 1С 7.7 в PDF
"""
import sys
import os
import logging
import argparse
import subprocess
from datetime import date

import config
from modules.utils import (
    setup_logging, parse_date, parse_date_range,
    format_date_display, get_today_date, get_file_info
)
from modules.invoice_extractor import InvoiceExtractor
from modules.pdf_generator import create_pdf

# Инициализация
logger = logging.getLogger(__name__)


def check_for_updates():
    """
    Проверить и применить обновления из git-репозитория

    Returns:
        bool: True если обновления были применены, False если обновлений нет или ошибка
    """
    try:
        print("\nПроверка обновлений...")

        # Проверяем, является ли текущая директория git-репозиторием
        script_dir = os.path.dirname(os.path.abspath(__file__))
        git_dir = os.path.join(script_dir, '.git')

        if not os.path.exists(git_dir):
            print("Это не git-репозиторий. Обновление невозможно.")
            return False

        # Получаем текущую ветку и хеш коммита
        result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            cwd=script_dir,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )

        if result.returncode != 0:
            print("Ошибка при получении текущей версии")
            return False

        current_hash = result.stdout.strip()

        # Получаем обновления с удаленного репозитория
        print("Загрузка обновлений...")
        result = subprocess.run(
            ['git', 'fetch'],
            cwd=script_dir,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )

        if result.returncode != 0:
            print(f"Ошибка при загрузке обновлений: {result.stderr}")
            return False

        # Проверяем, есть ли новые коммиты
        result = subprocess.run(
            ['git', 'rev-parse', '@{u}'],
            cwd=script_dir,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )

        if result.returncode != 0:
            print("Не удалось определить удаленную ветку")
            return False

        remote_hash = result.stdout.strip()

        # Сравниваем хеши
        if current_hash == remote_hash:
            print("Обновлений нет. Используется последняя версия.")
            return False

        # Применяем обновления
        print("Применение обновлений...")
        result = subprocess.run(
            ['git', 'pull'],
            cwd=script_dir,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )

        if result.returncode != 0:
            print(f"Ошибка при применении обновлений: {result.stderr}")
            return False

        # Показываем информацию об обновлениях
        result = subprocess.run(
            ['git', 'log', '--oneline', f'{current_hash}..HEAD'],
            cwd=script_dir,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )

        if result.stdout.strip():
            print("\nОбновления успешно применены:")
            for line in result.stdout.strip().split('\n'):
                print(f"  {line}")
        else:
            print("Обновления применены")

        return True

    except FileNotFoundError:
        print("Git не установлен или не найден в PATH")
        return False
    except Exception as e:
        print(f"Ошибка при обновлении: {str(e)}")
        logger.error(f"Ошибка при обновлении: {str(e)}")
        return False


def print_header():
    """
    Вывести заголовок приложения
    """
    os.system('cls' if os.name == 'nt' else 'clear')
    print("=" * 60)
    print("  Экспорт расходных накладных 1С 7.7 -> PDF")
    print("=" * 60)


def print_menu():
    """
    Вывести главное меню
    """
    print("\n")
    print("  1. Экспорт за сегодня")
    print("  2. Экспорт за конкретную дату")
    print("  3. Экспорт за период (диапазон дат)")
    print("  4. Настройки")
    print("  5. Выход")
    print("\n")


def export_invoices(start_date: date, end_date: date = None):
    """
    Экспортировать накладные за указанный период

    Args:
        start_date: Начальная дата
        end_date: Конечная дата (если None, то используется start_date)
    """
    try:
        if end_date is None:
            end_date = start_date

        # Отображаем период
        if start_date == end_date:
            period_str = format_date_display(start_date)
        else:
            period_str = f"{format_date_display(start_date)} - {format_date_display(end_date)}"

        print(f"\nПериод: {period_str}\n")

        # Извлечение накладных
        print("Извлечение накладных из DBF...")
        extractor = InvoiceExtractor(config.DATABASE_PATH)
        invoices = extractor.extract_invoices(start_date, end_date)

        if not invoices:
            print("Накладные не найдены за указанный период")
            return

        print(f"Найдено накладных: {len(invoices)}")

        # Генерация PDF
        print("Генерация PDF...")
        output_path = create_pdf(invoices, start_date, end_date)

        if output_path:
            print(f"PDF создан: {output_path}")

            # Информация о файле
            file_info = get_file_info(output_path)
            if file_info:
                print(f"  Размер: {file_info['size_formatted']}")

        else:
            print("Ошибка при создании PDF")

    except Exception as e:
        logger.error(f"Ошибка при экспорте: {str(e)}")
        print(f"Ошибка: {str(e)}")


def menu_export_today():
    """
    Экспорт за сегодня
    """
    print("\n=== Экспорт за сегодня ===")
    today = get_today_date()
    export_invoices(today)


def menu_export_date():
    """
    Экспорт за конкретную дату
    """
    print("\n=== Экспорт за конкретную дату ===")

    while True:
        date_str = input("\nВведите дату (ДД.ММ.ГГГГ): ")
        target_date = parse_date(date_str)

        if target_date:
            export_invoices(target_date)
            break
        else:
            print("Неверный формат даты. Используйте ДД.ММ.ГГГГ")


def menu_export_range():
    """
    Экспорт за период
    """
    print("\n=== Экспорт за период ===")

    while True:
        start_str = input("\nВведите начальную дату (ДД.ММ.ГГГГ): ")
        start_date = parse_date(start_str)

        if not start_date:
            print("Неверный формат даты. Используйте ДД.ММ.ГГГГ")
            continue

        end_str = input("Введите конечную дату (ДД.ММ.ГГГГ): ")
        end_date = parse_date(end_str)

        if not end_date:
            print("Неверный формат даты. Используйте ДД.ММ.ГГГГ")
            continue

        if start_date > end_date:
            print("Начальная дата не может быть позже конечной")
            continue

        export_invoices(start_date, end_date)
        break


def menu_settings():
    """
    Настройки
    """
    print("\n=== Настройки ===\n")

    print(f"Путь к базе 1С: {config.DATABASE_PATH or 'Не настроено'}")
    print(f"Файл конфигурации: {config.CONFIG_FILE}")
    print(f"Директория вывода: {config.OUTPUT_DIR}")
    print(f"Директория логов: {config.LOGS_DIR}")
    print(f"Формат даты: {config.DATE_FORMAT_DISPLAY}")

    print("\nДля изменения настроек отредактируйте файл config.txt")


def main():
    """
    Главная функция
    """
    # Настройка логирования
    setup_logging()

    # Обработка аргументов командной строки
    parser = argparse.ArgumentParser(
        description='Экспорт расходных накладных из 1С 7.7 в PDF',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--update',
        action='store_true',
        help='Проверить и применить обновления из git-репозитория'
    )
    args = parser.parse_args()

    # Если указан флаг --update, выполняем обновление и выходим
    if args.update:
        updated = check_for_updates()
        if updated:
            print("\nПерезапустите программу для использования обновленной версии.")
        input("\nНажмите Enter для выхода...")
        return

    # Загружаем путь к базе данных
    try:
        config.DATABASE_PATH = config.load_database_path()
    except Exception as e:
        print(f"Ошибка загрузки конфигурации: {str(e)}")
        print("\nОтредактируйте файл config.txt и укажите путь к базе 1С")
        input("\nНажмите Enter для выхода...")
        return

    # Проверяем существование базы данных
    print_header()
    if not os.path.exists(config.DATABASE_PATH):
        print(f"База данных не найдена: {config.DATABASE_PATH}")
        print("\nПроверьте путь к базе в config.txt")
        input("\nНажмите Enter для выхода...")
        return

    print(f"База данных найдена: {config.DATABASE_PATH}\n")

    # Главный цикл меню
    try:
        while True:
            print_header()
            print_menu()

            choice = input("Выберите действие [1-5]: ").strip()

            if choice not in ["1", "2", "3", "4", "5"]:
                print("\nНеверный выбор. Введите число от 1 до 5.")
                input("\nНажмите Enter для продолжения...")
                continue

            if choice == "1":
                menu_export_today()
            elif choice == "2":
                menu_export_date()
            elif choice == "3":
                menu_export_range()
            elif choice == "4":
                menu_settings()
            elif choice == "5":
                print("\nДо свидания!\n")
                break

            # Пауза перед возвратом в меню
            if choice != "5":
                input("\nНажмите Enter для продолжения...")

    except KeyboardInterrupt:
        print("\n\nПрервано пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {str(e)}")
        print(f"\nКритическая ошибка: {str(e)}")


if __name__ == "__main__":
    main()
