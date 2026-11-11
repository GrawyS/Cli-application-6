"""Интерфейс командной строки."""

import argparse
import sys

from depviz.asciitree import render_tree
from depviz.config import format_settings, load_settings
from depviz.errors import ConfigError, RenderError, RepositoryError
from depviz.graph import build_graph, describe
from depviz.plantuml import save_source, save_svg
from depviz.repository import open_repository
from depviz.reverse import format_reverse, reverse_dependencies

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
    parser.add_argument(
        "--reverse", metavar="ПАКЕТ",
        help="этап 4: вывести пакеты, зависящие от ПАКЕТА",
    )
    parser.add_argument(
        "--puml-only", action="store_true",
        help="этап 5: сохранить только .puml, не строить SVG",
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


def load_graph(settings):
    """Строит граф зависимостей по настройкам пользователя."""
    repository, root = open_repository(settings)
    graph = build_graph(
        root, repository.direct_dependencies, settings.max_depth)
    print_warnings(repository)
    return graph


def show_direct(settings):
    """Этап 2: печатает прямые зависимости заданной версии пакета."""
    repository, root = open_repository(settings)
    dependencies = repository.direct_dependencies(root)
    print_warnings(repository)
    print(f"Прямые зависимости {root}:")
    for dependency in dependencies or ["(нет прямых зависимостей)"]:
        print(f"  - {dependency}")


def show_reverse(settings, target):
    """Этап 4: печатает обратные зависимости пакета target."""
    graph = load_graph(settings)
    for result in reverse_dependencies(graph, target):
        print("\n".join(format_reverse(result)))


def show_graph(settings, puml_only):
    """Этапы 3 и 5: печатает граф, ASCII-дерево и сохраняет диаграмму."""
    graph = load_graph(settings)
    print("\n".join(describe(graph)))
    if settings.ascii_tree:
        print("\nДерево зависимостей:")
        print(render_tree(graph))
    source = save_source(graph, settings.output_file)
    print(f"\nДиаграмма PlantUML: {source}")
    if not puml_only:
        save_svg(graph, settings.output_file)
        print(f"Изображение графа: {settings.output_file}")


def run_mode(args, settings):
    """Выполняет режим, выбранный опциями командной строки."""
    if args.show_config:
        print("\n".join(format_settings(settings)))
    elif args.direct:
        show_direct(settings)
    elif args.reverse:
        show_reverse(settings, args.reverse)
    else:
        show_graph(settings, args.puml_only)


def main(argv=None):
    """Запускает приложение и возвращает код завершения."""
    args = build_parser().parse_args(argv)
    try:
        settings = load_settings(args.config)
    except ConfigError as exc:
        print_errors(exc.messages)
        return EXIT_ERROR
    try:
        run_mode(args, settings)
    except (RepositoryError, RenderError) as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return EXIT_ERROR
    return EXIT_OK
