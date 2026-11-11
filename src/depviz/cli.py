"""Интерфейс командной строки."""

import argparse
import sys

from depviz.config import format_settings, load_settings
from depviz.errors import ConfigError, RepositoryError
from depviz.graph import build_graph, describe
from depviz.repository import open_repository

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
    parser.add_argument(
        "--direct", action="store_true",
        help="этап 2: вывести прямые зависимости пакета",
    )
    return parser


def print_errors(messages):
    """Печатает список ошибок конфигурации в stderr."""
    print("Ошибки в конфигурации:", file=sys.stderr)
    for message in messages:
        print(f"  - {message}", file=sys.stderr)


def print_warnings(repository):
    """Печатает предупреждения репозитория в stderr."""
    for warning in repository.warnings:
        print(f"Предупреждение: {warning}", file=sys.stderr)


def show_direct(settings):
    """Этап 2: печатает прямые зависимости заданной версии пакета."""
    repository, root = open_repository(settings)
    dependencies = repository.direct_dependencies(root)
    print_warnings(repository)
    print(f"Прямые зависимости {root}:")
    for dependency in dependencies or ["(нет прямых зависимостей)"]:
        print(f"  - {dependency}")


def show_graph(settings):
    """Этап 3: строит граф зависимостей и печатает его описание."""
    repository, root = open_repository(settings)
    graph = build_graph(
        root, repository.direct_dependencies, settings.max_depth)
    print_warnings(repository)
    print("\n".join(describe(graph)))


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
    try:
        if args.direct:
            show_direct(settings)
        elif not args.show_config:
            show_graph(settings)
    except RepositoryError as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return EXIT_ERROR
    return EXIT_OK
