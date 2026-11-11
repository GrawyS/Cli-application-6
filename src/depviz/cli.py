"""Интерфейс командной строки."""

import argparse
import sys

from depviz.config import format_settings, load_settings
from depviz.errors import ConfigError

DEFAULT_CONFIG = "config.ini"
EXIT_OK = 0
EXIT_ERROR = 1


def build_parser():
    """Создаёт разбор аргументов командной строки."""
    parser = argparse.ArgumentParser(
        prog="depviz",
        description="Визуализация графа зависимостей Maven-пакета.",
    )
    parser.add_argument(
        "-c", "--config", default=DEFAULT_CONFIG,
        help="путь к INI-файлу настроек (по умолчанию config.ini)",
    )
    parser.add_argument(
        "--show-config", action="store_true",
        help="этап 1: вывести настройки в формате ключ = значение",
    )
    return parser


def print_errors(messages):
    """Печатает список ошибок конфигурации в stderr."""
    print("Ошибки в конфигурации:", file=sys.stderr)
    for message in messages:
        print(f"  - {message}", file=sys.stderr)


def main(argv=None):
    """Запускает приложение и возвращает код завершения."""
    args = build_parser().parse_args(argv)
    try:
        settings = load_settings(args.config)
    except ConfigError as exc:
        print_errors(exc.messages)
        return EXIT_ERROR
    if args.show_config:
        print("\n".join(format_settings(settings)))
    return EXIT_OK
