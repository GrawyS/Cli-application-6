"""Тесты этапа 5: ASCII-дерево."""

import unittest

from depviz.asciitree import render_tree
from depviz.graph import build_graph


def tree_of(table, root="A", depth=9):
    """Строит граф из словаря и возвращает его ASCII-дерево."""
    graph = build_graph(root, lambda node: table.get(node, []), depth)
    return render_tree(graph)


class TreeTest(unittest.TestCase):
    """Вид дерева."""

    def test_single_node(self):
        """Одиночный пакет — одна строка."""
        self.assertEqual(tree_of({}), "A")

    def test_branches(self):
        """Ветви и последний потомок выводятся разными символами."""
        text = tree_of({"A": ["B", "C"], "B": ["D"]})
        self.assertEqual(text, "\n".join([
            "A",
            "├── B",
            "│   └── D",
            "└── C",
        ]))

    def test_repeated_subtree_collapsed(self):
        """Повторное поддерево не раскрывается второй раз."""
        text = tree_of({"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": ["E"]})
        self.assertIn("D (см. выше)", text)
        self.assertEqual(text.count("E"), 1)

    def test_cycle_marked(self):
        """Обратное ребро цикла помечается."""
        text = tree_of({"A": ["B"], "B": ["A"]})
        self.assertEqual(text, "A\n└── B\n    └── A (цикл)")

    def test_truncated_marked(self):
        """Узлы на границе глубины помечаются."""
        text = tree_of({"A": ["B"], "B": ["C"]}, depth=1)
        self.assertEqual(text, "A\n└── B (...)")

    def test_deep_chain_without_recursion(self):
        """Очень глубокое дерево выводится без ошибки рекурсии."""
        size = 3000
        table = {str(i): [str(i + 1)] for i in range(size)}
        graph = build_graph("0", lambda node: table.get(node, []), size + 1)
        self.assertEqual(len(render_tree(graph).splitlines()), size + 1)


if __name__ == "__main__":
    unittest.main()
