"""Тестовый репозиторий: граф пакетов из текстового файла (этап 3).

Формат файла: одна строка на пакет, ``A: B C``. Имена пакетов состоят
из заглавных латинских букв, комментарии начинаются с ``#``.
"""

import re

from depviz.errors import RepositoryError

NAME = re.compile(r"^[A-Z]+$")
COMMENT_MARK = "#"
SEPARATOR = ":"


def _parse_line(number, line):
    """Разбирает строку 'A: B C' и возвращает (имя, список зависимостей)."""
    name, separator, tail = line.partition(SEPARATOR)
    if not separator:
        raise RepositoryError(f"строка {number}: ожидается 'A: B C'")
    names = [name.strip()] + tail.replace(",", " ").split()
    for item in names:
        if not NAME.match(item):
            raise RepositoryError(
                f"строка {number}: '{item}' - нужны заглавные буквы A-Z")
    return names[0], list(dict.fromkeys(names[1:]))


def parse_repository_text(text):
    """Преобразует текст описания репозитория в словарь пакет -> зависимости."""
    graph = {}
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.split(COMMENT_MARK, maxsplit=1)[0].strip()
        if not line:
            continue
        name, dependencies = _parse_line(number, line)
        if name in graph:
            raise RepositoryError(f"строка {number}: '{name}' уже описан")
        graph[name] = dependencies
    return graph


class FileRepository:
    """Репозиторий, данные которого загружены из файла описания графа."""

    def __init__(self, graph):
        """Запоминает граф и множество всех известных пакетов."""
        self.graph = graph
        self.warnings = []
        self.known = set(graph)
        for dependencies in graph.values():
            self.known.update(dependencies)

    @classmethod
    def from_file(cls, path):
        """Читает файл описания и создаёт репозиторий."""
        try:
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
        except (OSError, UnicodeDecodeError) as exc:
            raise RepositoryError(f"не удалось прочитать '{path}': {exc}") \
                from exc
        return cls(parse_repository_text(text))

    def direct_dependencies(self, node):
        """Возвращает прямые зависимости пакета из файла."""
        if node not in self.known:
            raise RepositoryError(f"пакет '{node}' не найден в репозитории")
        return list(self.graph.get(node, []))
