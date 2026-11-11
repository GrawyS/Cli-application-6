"""Тесты этапа 3: обход DFS без рекурсии, глубина, циклы."""

import unittest

from depviz.errors import RepositoryError
from depviz.graph import build_graph, describe

CHAIN_LENGTH = 5000
BIG_DEPTH = 10 ** 6


def lookup(table):
    """Создаёт функцию получения зависимостей из словаря."""
    def get_dependencies(node):
        """Возвращает зависимости узла из словаря."""
        return table.get(node, [])
    return get_dependencies


class StructureTest(unittest.TestCase):
    """Форма получаемого графа."""

    def test_chain(self):
        """Цепочка A -> B -> C."""
        graph = build_graph("A", lookup({"A": ["B"], "B": ["C"]}), 5)
        self.assertEqual(graph.edges, {"A": ["B"], "B": ["C"], "C": []})

    def test_diamond_visits_shared_once(self):
        """Общая зависимость D присутствует один раз."""
        table = {"A": ["B", "C"], "B": ["D"], "C": ["D"]}
        graph = build_graph("A", lookup(table), 5)
        self.assertEqual(list(graph.edges), ["A", "B", "D", "C"])
        self.assertEqual(graph.cycles, [])

    def test_preorder_dfs(self):
        """Порядок узлов соответствует обходу в глубину."""
        table = {"A": ["B", "C"], "B": ["D"], "D": ["E"]}
        graph = build_graph("A", lookup(table), 9)
        self.assertEqual(list(graph.edges), ["A", "B", "D", "E", "C"])

    def test_duplicate_dependencies_removed(self):
        """Повторы в списке зависимостей схлопываются."""
        graph = build_graph("A", lookup({"A": ["B", "B"]}), 3)
        self.assertEqual(graph.edges["A"], ["B"])


class CycleTest(unittest.TestCase):
    """Циклические зависимости."""

    def test_simple_cycle(self):
        """A -> B -> A: цикл найден, обход завершён."""
        graph = build_graph("A", lookup({"A": ["B"], "B": ["A"]}), 9)
        self.assertEqual(graph.cycles, [("B", "A")])
        self.assertEqual(set(graph.edges), {"A", "B"})

    def test_self_loop(self):
        """Зависимость пакета от самого себя."""
        graph = build_graph("A", lookup({"A": ["A", "B"]}), 9)
        self.assertEqual(graph.cycles, [("A", "A")])
        self.assertIn("B", graph.edges)

    def test_cycle_not_through_root(self):
        """Цикл B -> C -> B вдали от корня."""
        table = {"A": ["B"], "B": ["C"], "C": ["B"]}
        graph = build_graph("A", lookup(table), 9)
        self.assertEqual(graph.cycles, [("C", "B")])

    def test_cycle_reported_once(self):
        """Одно и то же обратное ребро не дублируется."""
        table = {"A": ["B", "C"], "B": ["A"], "C": ["B"]}
        graph = build_graph("A", lookup(table), 9)
        self.assertEqual(graph.cycles.count(("B", "A")), 1)


class DepthTest(unittest.TestCase):
    """Ограничение глубины анализа."""

    def test_depth_one_only_direct(self):
        """Глубина 1: только прямые зависимости корня."""
        table = {"A": ["B"], "B": ["C"]}
        graph = build_graph("A", lookup(table), 1)
        self.assertEqual(set(graph.edges), {"A", "B"})
        self.assertEqual(graph.truncated, {"B"})

    def test_depth_two(self):
        """Глубина 2 раскрывает зависимости зависимостей."""
        table = {"A": ["B"], "B": ["C"], "C": ["D"]}
        graph = build_graph("A", lookup(table), 2)
        self.assertEqual(set(graph.edges), {"A", "B", "C"})
        self.assertEqual(graph.truncated, {"C"})

    def test_shorter_path_reexpands(self):
        """Узел, найденный сначала глубоко, раскрывается по короткому пути."""
        table = {"A": ["X", "Y"], "X": ["Y"], "Y": ["Z"], "Z": ["W"]}
        graph = build_graph("A", lookup(table), 3)
        self.assertIn("W", graph.edges)
        self.assertEqual(graph.truncated, {"W"})

    def test_truncated_cleared_after_expansion(self):
        """Раскрытый позже узел не считается обрезанным."""
        table = {"A": ["X", "Y"], "X": ["Y"], "Y": ["Z"]}
        graph = build_graph("A", lookup(table), 3)
        self.assertNotIn("Y", graph.truncated)


class RobustnessTest(unittest.TestCase):
    """Большие графы и ошибки репозитория."""

    def test_no_recursion_limit(self):
        """Цепочка длиннее лимита рекурсии Python обходится без ошибок."""
        table = {i: [i + 1] for i in range(CHAIN_LENGTH)}
        graph = build_graph(0, lookup(table), BIG_DEPTH)
        self.assertEqual(len(graph.edges), CHAIN_LENGTH + 1)

    def test_root_failure_raises(self):
        """Ошибка получения корня прерывает построение."""
        def broken(node):
            """Всегда сообщает об ошибке."""
            raise RepositoryError("нет пакета " + node)
        with self.assertRaises(RepositoryError):
            build_graph("A", broken, 3)

    def test_child_failure_recorded(self):
        """Ошибка для вложенного пакета запоминается, граф строится."""
        def partly(node):
            """Падает на пакете B."""
            if node == "B":
                raise RepositoryError("недоступен")
            return {"A": ["B", "C"]}.get(node, [])
        graph = build_graph("A", partly, 3)
        self.assertEqual(graph.failed, {"B": "недоступен"})
        self.assertIn("C", graph.edges)


class DescribeTest(unittest.TestCase):
    """Текстовое описание графа."""

    def test_describe_lines(self):
        """В описании есть счётчики, рёбра и циклы."""
        graph = build_graph("A", lookup({"A": ["B"], "B": ["A"]}), 3)
        text = "\n".join(describe(graph))
        self.assertIn("Узлов: 2", text)
        self.assertIn("A -> B", text)
        self.assertIn("Цикл: B -> A", text)


if __name__ == "__main__":
    unittest.main()
