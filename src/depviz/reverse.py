"""Обратные зависимости: какие пакеты зависят от заданного (этап 4)."""

from dataclasses import dataclass

from depviz.errors import RepositoryError
from depviz.graph import build_graph


@dataclass
class ReverseResult:
    """Пакеты, зависящие от target, прямо и через другие пакеты."""

    target: str
    direct: list
    indirect: list


def invert_edges(graph):
    """Возвращает словарь: пакет -> список пакетов, которые от него зависят."""
    parents = {node: [] for node in graph.edges}
    for node, dependencies in graph.edges.items():
        for dependency in dependencies:
            parents.setdefault(dependency, []).append(node)
    return parents


def find_targets(graph, target):
    """Ищет узлы графа по точному имени или по префиксу 'group:artifact'."""
    if target in graph.edges:
        return [target]
    prefix = target + ":"
    found = [node for node in graph.edges if node.startswith(prefix)]
    if not found:
        raise RepositoryError(f"пакет '{target}' не найден в графе")
    return found


def reverse_for(parents, node, limit):
    """Обходит инвертированный граф тем же DFS, что и прямой граф."""
    reverse_graph = build_graph(node, lambda name: parents.get(name, []), limit)
    direct = reverse_graph.edges[node]
    indirect = [name for name in reverse_graph.edges
                if name != node and name not in direct]
    return ReverseResult(node, direct, indirect)


def reverse_dependencies(graph, target):
    """Возвращает обратные зависимости для каждого узла, подходящего target."""
    parents = invert_edges(graph)
    limit = len(graph.edges) + 1
    return [reverse_for(parents, node, limit)
            for node in find_targets(graph, target)]


def format_reverse(result):
    """Возвращает строки отчёта об обратных зависимостях."""
    lines = [f"Обратные зависимости {result.target}:"]
    if not result.direct:
        return lines + ["  (от пакета никто не зависит)"]
    lines.append("  Прямые:")
    lines += [f"    - {name}" for name in result.direct]
    if result.indirect:
        lines.append("  Через другие пакеты:")
        lines += [f"    - {name}" for name in result.indirect]
    return lines
