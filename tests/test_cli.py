"""Сквозные тесты командной строки на тестовом репозитории."""

import contextlib
import io
import os
import unittest
from unittest import mock

from depviz.cli import EXIT_ERROR, EXIT_OK, main
from helpers import workdir, write_test_config

DIAMOND = "A: B C\nB: D\nC: D E\n"
SVG = b"<svg/>"


def run_cli(*args):
    """Запускает main и возвращает (код, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(list(args))
    return code, out.getvalue(), err.getvalue()


class CliTest(unittest.TestCase):
    """Режимы работы приложения."""

    def test_show_config(self):
        """--show-config печатает пары ключ = значение."""
        with workdir() as folder:
            config = write_test_config(folder, DIAMOND)
            code, out, _ = run_cli("-c", config, "--show-config")
        self.assertEqual(code, EXIT_OK)
        self.assertIn("repo_mode = test", out)

    def test_bad_config(self):
        """Ошибки конфигурации дают код 1 и сообщения в stderr."""
        with workdir() as folder:
            config = write_test_config(folder, DIAMOND, max_depth="0")
            code, _, err = run_cli("-c", config)
        self.assertEqual(code, EXIT_ERROR)
        self.assertIn("max_depth", err)

    def test_direct(self):
        """--direct печатает прямые зависимости корня."""
        with workdir() as folder:
            config = write_test_config(folder, DIAMOND)
            code, out, _ = run_cli("-c", config, "--direct")
        self.assertEqual(code, EXIT_OK)
        self.assertIn("  - B", out)
        self.assertNotIn("  - D", out)

    def test_reverse(self):
        """--reverse печатает пакеты, зависящие от D."""
        with workdir() as folder:
            config = write_test_config(folder, DIAMOND)
            code, out, _ = run_cli("-c", config, "--reverse", "D")
        self.assertEqual(code, EXIT_OK)
        self.assertIn("Прямые", out)

    def test_unknown_root(self):
        """Корневой пакет, которого нет в файле, — ошибка."""
        with workdir() as folder:
            config = write_test_config(folder, DIAMOND, package_name="Z")
            code, _, err = run_cli("-c", config)
        self.assertEqual(code, EXIT_ERROR)
        self.assertIn("не найден", err)

    def test_graph_with_tree_and_svg(self):
        """Полный запуск: дерево, .puml и SVG."""
        with workdir() as folder:
            config = write_test_config(folder, DIAMOND, ascii_tree="true")
            with mock.patch("depviz.plantuml.render_svg", return_value=SVG):
                with mock.patch("depviz.cli.save_svg") as save:
                    code, out, _ = run_cli("-c", config)
            self.assertTrue(os.path.exists(os.path.join(folder, "g.puml")))
        self.assertEqual(code, EXIT_OK)
        self.assertIn("├── B", out)
        save.assert_called_once()

    def test_puml_only_skips_render(self):
        """--puml-only не вызывает построение SVG."""
        with workdir() as folder:
            config = write_test_config(folder, DIAMOND)
            with mock.patch("depviz.cli.save_svg") as save:
                code, out, _ = run_cli("-c", config, "--puml-only")
        self.assertEqual(code, EXIT_OK)
        save.assert_not_called()
        self.assertNotIn("├──", out)

    def test_cycle_demo(self):
        """Цикл выводится в описании и не вешает программу."""
        with workdir() as folder:
            config = write_test_config(folder, "A: B\nB: A\n")
            code, out, _ = run_cli("-c", config, "--puml-only")
        self.assertEqual(code, EXIT_OK)
        self.assertIn("Цикл: B -> A", out)


if __name__ == "__main__":
    unittest.main()
