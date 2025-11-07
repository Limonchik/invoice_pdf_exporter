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
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table as RichTable
from rich import box
from rich.spinner import Spinner
from rich.live import Live

import config
from modules.utils import (
    setup_logging, parse_date, parse_date_range,
    format_date_display, get_today_date, get_file_info
)
from modules.invoice_extractor import InvoiceExtractor
from modules.pdf_generator import create_pdf

# Настройка консоли для UTF-8
if sys.platform == 'win32':
    # Устанавливаем UTF-8 для stdout и stderr
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    os.system('chcp 65001 >nul 2>&1')

# Инициализация
console = Console(force_terminal=True, legacy_windows=True)
logger = logging.getLogger(__name__)


def check_for_updates():
    """
    Проверить и применить обновления из git-репозитория

    Returns:
        bool: True если обновления были применены, False если обновлений нет или ошибка
    """
    try:
        console.print("\n[cyan]Проверка обновлений...[/cyan]")

        # Проверяем, является ли текущая директория git-репозиторием
        script_dir = os.path.dirname(os.path.abspath(__file__))
        git_dir = os.path.join(script_dir, '.git')

        if not os.path.exists(git_dir):
            console.print("[yellow]⚠ Это не git-репозиторий. Обновление невозможно.[/yellow]")
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
            console.print(f"[red]✗ Ошибка при получении текущей версии[/red]")
            return False

        current_hash = result.stdout.strip()

        # Получаем обновления с удаленного репозитория
        console.print("[cyan]Загрузка обновлений...[/cyan]")
        result = subprocess.run(
            ['git', 'fetch'],
            cwd=script_dir,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )

        if result.returncode != 0:
            console.print(f"[red]✗ Ошибка при загрузке обновлений:[/red] {result.stderr}")
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
            console.print("[yellow]⚠ Не удалось определить удаленную ветку[/yellow]")
            return False

        remote_hash = result.stdout.strip()

        # Сравниваем хеши
        if current_hash == remote_hash:
            console.print("[green]✓ Обновлений нет. Используется последняя версия.[/green]")
            return False

        # Применяем обновления
        console.print("[cyan]Применение обновлений...[/cyan]")
        result = subprocess.run(
            ['git', 'pull'],
            cwd=script_dir,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )

        if result.returncode != 0:
            console.print(f"[red]✗ Ошибка при применении обновлений:[/red] {result.stderr}")
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
            console.print("\n[green]✓ Обновления успешно применены:[/green]")
            for line in result.stdout.strip().split('\n'):
                console.print(f"  [dim]{line}[/dim]")
        else:
            console.print("[green]✓ Обновления применены[/green]")

        return True

    except FileNotFoundError:
        console.print("[red]✗ Git не установлен или не найден в PATH[/red]")
        return False
    except Exception as e:
        console.print(f"[red]✗ Ошибка при обновлении:[/red] {str(e)}")
        logger.error(f"Ошибка при обновлении: {str(e)}")
        return False


def print_header():
    """
    Âûâåñòè çàãîëîâîê ïðèëîæåíèÿ
    """
    console.clear()
    header_text = """
[bold blue]═══════════════════════════════════════════════════════════[/bold blue]
[bold cyan]    Экспорт расходных накладных 1С 7.7 → PDF[/bold cyan]
[bold blue]═══════════════════════════════════════════════════════════[/bold blue]
    """
    console.print(header_text)


def print_menu():
    """
    Âûâåñòè ãëàâíîå ìåíþ
    """
    menu_table = RichTable(show_header=False, box=box.SIMPLE, padding=(0, 2))
    menu_table.add_column("Option", style="cyan", width=4)
    menu_table.add_column("Description", style="white")

    menu_table.add_row("1", "Экспорт за сегодня")
    menu_table.add_row("2", "Экспорт за конкретную дату")
    menu_table.add_row("3", "Экспорт за период (диапазон дат)")
    menu_table.add_row("4", "Настройки")
    menu_table.add_row("5", "Выход")

    console.print("\n")
    console.print(menu_table)
    console.print("\n")


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

        console.print(f"\n[cyan]Период:[/cyan] {period_str}\n")

        # Извлечение накладных
        with console.status("[bold green]Извлечение накладных из DBF...", spinner="dots") as status:
            extractor = InvoiceExtractor(config.DATABASE_PATH)
            invoices = extractor.extract_invoices(start_date, end_date)

        if not invoices:
            console.print("[yellow]⚠ Накладные не найдены за указанный период[/yellow]")
            return

        console.print(f"[green]✓ Найдено накладных:[/green] {len(invoices)}")

        # Генерация PDF
        with console.status("[bold green]Генерация PDF...", spinner="dots") as status:
            output_path = create_pdf(invoices, start_date, end_date)

        if output_path:
            console.print(f"[green]✓ PDF создан:[/green] {output_path}")

            # Информация о файле
            file_info = get_file_info(output_path)
            if file_info:
                console.print(f"[dim]  Размер: {file_info['size_formatted']}[/dim]")

        else:
            console.print("[red]✗ Ошибка при создании PDF[/red]")

    except Exception as e:
        logger.error(f"Ошибка при экспорте: {str(e)}")
        console.print(f"[red]✗ Ошибка:[/red] {str(e)}")


def menu_export_today():
    """
    Экспорт за сегодня
    """
    console.print("\n[bold cyan]═══ Экспорт за сегодня ═══[/bold cyan]")
    today = get_today_date()
    export_invoices(today)


def menu_export_date():
    """
    Экспорт за конкретную дату
    """
    console.print("\n[bold cyan]═══ Экспорт за конкретную дату ═══[/bold cyan]")

    while True:
        date_str = Prompt.ask("\nВведите дату (ДД.ММ.ГГГГ)")
        target_date = parse_date(date_str)

        if target_date:
            export_invoices(target_date)
            break
        else:
            console.print("[red]✗ Неверный формат даты. Используйте ДД.ММ.ГГГГ[/red]")


def menu_export_range():
    """
    Экспорт за период
    """
    console.print("\n[bold cyan]═══ Экспорт за период ═══[/bold cyan]")

    while True:
        start_str = Prompt.ask("\nВведите начальную дату (ДД.ММ.ГГГГ)")
        start_date = parse_date(start_str)

        if not start_date:
            console.print("[red]✗ Неверный формат даты. Используйте ДД.ММ.ГГГГ[/red]")
            continue

        end_str = Prompt.ask("Введите конечную дату (ДД.ММ.ГГГГ)")
        end_date = parse_date(end_str)

        if not end_date:
            console.print("[red]✗ Неверный формат даты. Используйте ДД.ММ.ГГГГ[/red]")
            continue

        if start_date > end_date:
            console.print("[red]✗ Начальная дата не может быть позже конечной[/red]")
            continue

        export_invoices(start_date, end_date)
        break


def menu_settings():
    """
    Íàñòðîéêè
    """
    console.print("\n[bold cyan]═══ Настройки ═══[/bold cyan]\n")

    settings_table = RichTable(show_header=True, box=box.SIMPLE)
    settings_table.add_column("Параметр", style="cyan")
    settings_table.add_column("Значение", style="white")

    settings_table.add_row("Путь к базе 1С", config.DATABASE_PATH or "[red]Не настроено[/red]")
    settings_table.add_row("Файл конфигурации", config.CONFIG_FILE)
    settings_table.add_row("Директория вывода", config.OUTPUT_DIR)
    settings_table.add_row("Директория логов", config.LOGS_DIR)
    settings_table.add_row("Формат даты", config.DATE_FORMAT_DISPLAY)

    console.print(settings_table)
    console.print("\n[dim]Для изменения настроек отредактируйте файл config.txt[/dim]")


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
            console.print("\n[green]Перезапустите программу для использования обновленной версии.[/green]")
        input("\nНажмите Enter для выхода...")
        return

    # Загружаем путь к базе данных
    try:
        config.DATABASE_PATH = config.load_database_path()
    except Exception as e:
        console.print(f"[red]✗ Ошибка загрузки конфигурации:[/red] {str(e)}")
        console.print("\n[yellow]Отредактируйте файл config.txt и укажите путь к базе 1С[/yellow]")
        input("\nНажмите Enter для выхода...")
        return

    # Проверяем существование базы данных
    print_header()
    if not os.path.exists(config.DATABASE_PATH):
        console.print(f"[red]✗ База данных не найдена:[/red] {config.DATABASE_PATH}")
        console.print("\n[yellow]Проверьте путь к базе в config.txt[/yellow]")
        input("\nНажмите Enter для выхода...")
        return

    console.print(f"[green]✓ База данных найдена:[/green] {config.DATABASE_PATH}\n")

    # Главный цикл меню
    try:
        while True:
            print_header()
            print_menu()

            choice = Prompt.ask("Выберите действие", choices=["1", "2", "3", "4", "5"], default="1")

            if choice == "1":
                menu_export_today()
            elif choice == "2":
                menu_export_date()
            elif choice == "3":
                menu_export_range()
            elif choice == "4":
                menu_settings()
            elif choice == "5":
                console.print("\n[cyan]До свидания![/cyan]\n")
                break

            # Пауза перед возвратом в меню
            if choice != "5":
                input("\nНажмите Enter для продолжения...")

    except KeyboardInterrupt:
        console.print("\n\n[yellow]Прервано пользователем[/yellow]")
    except Exception as e:
        logger.error(f"Критическая ошибка: {str(e)}")
        console.print(f"\n[red]✗ Критическая ошибка:[/red] {str(e)}")


if __name__ == "__main__":
    main()
