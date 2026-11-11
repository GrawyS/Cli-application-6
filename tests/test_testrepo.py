"""Тесты тестового режима: файл описания репозитория."""

import unittest

from depviz.config import load_settings
from depviz.errors import RepositoryError
from depviz.repository import open_repository
from depviz.testrepo import FileRepository, parse_repository_text
from helpers import workdir, write_real_config, write_test_config


class ParseTest(unittest.TestCase):
    """Разбор текста описания."""

    def test_valid_text(self):
        """Строки, запятые и комментарии разбираются."""
        text = "# заголовок\nA: B, C  # хвост\n\nB: C\n"
        graph = parse_repository_text(text)
        self.assertEqual(graph, {"A": ["B", "C"], "B": ["C"]})

    def test_empty_dependencies(self):
        """Пакет без зависимостей допустим."""
        self.assertEqual(parse_repository_text("A:\n"), {"A": []})

    def test_lowercase_rejected(self):
        """Строчные имена отклоняются с номером строки."""
        with self.assertRaisesRegex(RepositoryError, "строка 2"):
            parse_repository_text("A: B\nb: C\n")

    def test_missing_colon(self):
        """Строка без двоеточия отклоняется."""
        with self.assertRaises(RepositoryError):
            parse_repository_text("A B\n")

    def test_duplicate_definition(self):
        """Повторное описание пакета отклоняется."""
        with self.assertRaises(RepositoryError):
            parse_repository_text("A: B\nA: C\n")


class RepositoryTest(unittest.TestCase):
    """Поведение репозитория."""

    def test_leaf_known_without_line(self):
        """Пакет, упомянутый только как зависимость, — лист."""
        repo = FileRepository(parse_repository_text("A: B\n"))
        self.assertEqual(repo.direct_dependencies("B"), [])

    def test_unknown_package(self):
        """Неизвестный пакет вызывает RepositoryError."""
        repo = FileRepository(parse_repository_text("A: B\n"))
        with self.assertRaises(RepositoryError):
            repo.direct_dependencies("Z")

    def test_missing_file(self):
        """Отсутствующий файл вызывает RepositoryError."""
        with self.assertRaises(RepositoryError):
            FileRepository.from_file("/no/such/repo.txt")

    def test_open_repository_test_mode(self):
        """В тестовом режиме корнем служит имя пакета."""
        with workdir() as folder:
            path = write_test_config(folder, "A: B\n")
            settings = load_settings(path)
            repository, root = open_repository(settings)
        self.assertEqual(root, "A")
        self.assertEqual(repository.direct_dependencies("A"), ["B"])

    def test_open_repository_real_mode(self):
        """В реальном режиме корень содержит версию."""
        with workdir() as folder:
            settings = load_settings(write_real_config(folder))
            _, root = open_repository(settings)
        self.assertEqual(root, "org.example:demo:1.0.0")


if __name__ == "__main__":
    unittest.main()
