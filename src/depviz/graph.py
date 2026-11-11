"""Граф зависимостей: обход в глубину (DFS) без рекурсии (этап 3)."""

from dataclasses import dataclass, field

from depviz.errors import RepositoryError

UNEXPANDED = float("inf")


@dataclass
class Graph:
    """Граф зависимостей, построенный от корневого пакета."""

    root: str
    edges: dict = field(default_factory=dict)
    cycles: list = field(default_factory=list)
    truncated: set = field(default_factory=set)
    failed: dict = field(default_factory=dict)


class GraphWalker:
    """Итеративный DFS с явным стеком, лимитом глубины и поиском циклов."""

    def __init__(self, root, get_dependencies, max_depth):
        """Подготавливает состояние обхода."""
        self.graph = Graph(root)
        self.get_dependencies = get_dependencies
        self.max_depth = max_depth
        self.best_depth = {}
        self.on_path = set()
        self.stack = []

    def run(self):
        """Выполняет обход и возвращает готовый граф."""
        self._open(self.graph.root, 0)
        while self.stack:
            self._step()
        return self.graph

    def _fetch(self, node):
        """Получает зависимости узла; ошибки не-корня запоминает."""
        try:
            found = self.get_dependencies(node)
        except RepositoryError as exc:
            if node == self.graph.root:
                raise
            self.graph.failed[node] = str(exc)
            return []
        return list(dict.fromkeys(found))

    def _open(self, node, depth):
        """Входит в узел: читает зависимости и кладёт его на стек."""
        if depth >= self.max_depth:
            self.graph.edges.setdefault(node, [])
            self.graph.truncated.add(node)
            return
        dependencies = self._fetch(node)
        self.graph.edges[node] = dependencies
        self.graph.truncated.discard(node)
        self.best_depth[node] = depth
        self.on_path.add(node)
        self.stack.append((node, iter(dependencies), depth))

    def _step(self):
        """Обрабатывает следующую зависимость узла на вершине стека."""
        node, children, depth = self.stack[-1]
        child = next(children, None)
        if child is None:
            self.stack.pop()
            self.on_path.discard(node)
            return
        if child in self.on_path:
            self._remember_cycle(node, child)
            return
        child_depth = depth + 1
        if self.best_depth.get(child, UNEXPANDED) > child_depth:
            self._open(child, child_depth)

    def _remember_cycle(self, node, child):
        """Записывает обратное ребро, замыкающее цикл."""
        edge = (node, child)
        if edge not in self.graph.cycles:
            self.graph.cycles.append(edge)


def build_graph(root, get_dependencies, max_depth):
    """Строит граф зависимостей от root обходом DFS без рекурсии.

    get_dependencies(node) возвращает список прямых зависимостей узла,
    узлы глубже max_depth не раскрываются.
    """
    return GraphWalker(root, get_dependencies, max_depth).run()


def describe(graph):
    """Возвращает текстовое описание графа построчно."""
    lines = [f"Узлов: {len(graph.edges)}, "
             f"рёбер: {sum(map(len, graph.edges.values()))}"]
    for node, dependencies in graph.edges.items():
        targets = ", ".join(dependencies) or "-"
        lines.append(f"  {node} -> {targets}")
    for source, target in graph.cycles:
        lines.append(f"Цикл: {source} -> {target}")
    for node in sorted(graph.truncated):
        lines.append(f"Глубина исчерпана, не раскрыт: {node}")
    for node, reason in graph.failed.items():
        lines.append(f"Не удалось получить {node}: {reason}")
    return lines
