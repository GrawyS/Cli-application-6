"""Тесты этапа 4: обратные зависимости."""

import unittest

from depviz.errors import RepositoryError
from depviz.graph import build_graph
from depviz.reverse import (
    find_targets, format_reverse, invert_edges, reverse_dependencies,
)

DIAMOND = {"A": ["B", "C"], "B": ["D"], "C": ["D", "E"]}


def graph_of(table, root="A", depth=9):
    """Строит граф из словаря зависимостей."""
    return build_graph(root, lambda node: table.get(node, []), depth)


class ReverseTest(unittest.TestCase):
    """Поиск пакетов, зависящих от заданного."""

    def test_invert_edges(self):
        """Рёбра разворачиваются."""
        parents = invert_edges(graph_of(DIAMOND))
        self.assertEqual(parents["D"], ["B", "C"])
        self.assertEqual(parents["A"], [])

    def test_direct_and_indirect(self):
        """D: прямые B и C, косвенный A."""
        result = reverse_dependencies(graph_of(DIAMOND), "D")[0]
        self.assertEqual(result.direct, ["B", "C"])
        self.assertEqual(result.indirect, ["A"])

    def test_leaf_with_single_parent(self):
        """E зависит только через C."""
        result = reverse_dependencies(graph_of(DIAMOND), "E")[0]
        self.assertEqual(result.direct, ["C"])
        self.assertEqual(result.indirect, ["A"])

    def test_root_has_no_dependents(self):
        """От корня никто не зависит."""
        result = reverse_dependencies(graph_of(DIAMOND), "A")[0]
        self.assertEqual(result.direct, [])
        self.assertIn("никто не зависит", "\n".join(format_reverse(result)))

    def test_cycle_does_not_hang(self):
        """В циклическом графе обход завершается."""
        table = {"A": ["B"], "B": ["C"], "C": ["A"]}
        result = reverse_dependencies(graph_of(table), "A")[0]
        self.assertEqual(result.direct, ["C"])
        self.assertEqual(result.indirect, ["B"])

    def test_unknown_target(self):
        """Неизвестный пакет вызывает RepositoryError."""
        with self.assertRaises(RepositoryError):
            reverse_dependencies(graph_of(DIAMOND), "Z")

    def test_maven_prefix_matches_all_versions(self):
        """Имя без версии находит узлы всех версий."""
        table = {"r:r:1": ["l:l:1", "l:l:2"], "l:l:1": [], "l:l:2": []}
        graph = graph_of(table, root="r:r:1")
        self.assertEqual(find_targets(graph, "l:l"), ["l:l:1", "l:l:2"])
        results = reverse_dependencies(graph, "l:l")
        self.assertEqual([r.direct for r in results], [["r:r:1"], ["r:r:1"]])

    def test_format_lists_both_groups(self):
        """В отчёте есть прямые и косвенные зависимости."""
        result = reverse_dependencies(graph_of(DIAMOND), "D")[0]
        text = "\n".join(format_reverse(result))
        self.assertIn("Прямые", text)
        self.assertIn("Через другие пакеты", text)


if __name__ == "__main__":
    unittest.main()
