"""Тесты этапа 1: загрузка и проверка конфигурации."""

import unittest

from depviz.config import format_settings, load_settings
from depviz.errors import ConfigError
from helpers import workdir, write_file, write_real_config, write_test_config


def messages_for(**overrides):
    """Возвращает сообщения об ошибках для конфигурации с подменами."""
    with workdir() as folder:
        path = write_real_config(folder, **overrides)
        try:
            load_settings(path)
        except ConfigError as exc:
            return exc.messages
    return []


class ValidConfigTest(unittest.TestCase):
    """Корректные конфигурации."""

    def test_real_mode_values(self):
        """Реальный режим: значения читаются и приводятся к типам."""
        with workdir() as folder:
            settings = load_settings(write_real_config(folder))
        self.assertEqual(settings.package_name, "org.example:demo")
        self.assertEqual(settings.max_depth, 3)
        self.assertTrue(settings.ascii_tree)

    def test_test_mode_needs_no_version(self):
        """Тестовый режим: версия может быть пустой."""
        with workdir() as folder:
            path = write_test_config(folder, "A: B\n")
            settings = load_settings(path)
        self.assertEqual(settings.repo_mode, "test")
        self.assertEqual(settings.package_version, "")

    def test_format_settings_key_value(self):
        """Настройки выводятся строками 'ключ = значение'."""
        with workdir() as folder:
            lines = format_settings(load_settings(write_real_config(folder)))
        self.assertIn("max_depth = 3", lines)
        self.assertIn("repo_mode = real", lines)
        self.assertEqual(len(lines), len(set(lines)))


class InvalidConfigTest(unittest.TestCase):
    """Обработка ошибок для каждого параметра."""

    def assert_error_for(self, name, **overrides):
        """Проверяет, что сообщение об ошибке относится к параметру."""
        messages = messages_for(**overrides)
        self.assertTrue(
            any(message.startswith(name + ":") for message in messages),
            messages,
        )

    def test_bad_package_name(self):
        """Имя пакета без artifactId отклоняется."""
        self.assert_error_for("package_name", package_name="onlyname")

    def test_bad_url(self):
        """URL без схемы http/https отклоняется."""
        self.assert_error_for("repo_url", repo_url="ftp://host/path")

    def test_bad_mode(self):
        """Неизвестный режим отклоняется."""
        self.assert_error_for("repo_mode", repo_mode="demo")

    def test_latest_version(self):
        """Версия latest не поддерживается."""
        self.assert_error_for("package_version", package_version="latest")

    def test_bad_output_extension(self):
        """Файл изображения должен быть .svg."""
        self.assert_error_for("output_file", output_file="graph.png")

    def test_missing_output_folder(self):
        """Каталог для изображения должен существовать."""
        self.assert_error_for("output_file", output_file="/no/dir/g.svg")

    def test_bad_ascii_flag(self):
        """Режим ASCII-дерева принимает только логические значения."""
        self.assert_error_for("ascii_tree", ascii_tree="maybe")

    def test_depth_not_number(self):
        """Глубина должна быть числом."""
        self.assert_error_for("max_depth", max_depth="many")

    def test_depth_not_positive(self):
        """Глубина должна быть не меньше единицы."""
        self.assert_error_for("max_depth", max_depth="0")

    def test_empty_value(self):
        """Пустой обязательный параметр отклоняется."""
        self.assert_error_for("package_name", package_name="")

    def test_unknown_parameter(self):
        """Неизвестный параметр считается ошибкой."""
        self.assert_error_for("colour", colour="red")

    def test_all_errors_reported_together(self):
        """Все ошибки возвращаются одним списком."""
        messages = messages_for(max_depth="x", repo_mode="demo")
        self.assertGreaterEqual(len(messages), 2)


class BrokenFileTest(unittest.TestCase):
    """Проблемы с самим файлом конфигурации."""

    def test_missing_file(self):
        """Отсутствующий файл даёт ConfigError."""
        with self.assertRaises(ConfigError):
            load_settings("/no/such/config.ini")

    def test_missing_section(self):
        """Файл без секции [settings] отклоняется."""
        with workdir() as folder:
            path = write_file(folder, "c.ini", "[other]\na = 1\n")
            with self.assertRaises(ConfigError):
                load_settings(path)

    def test_syntax_error(self):
        """Файл с синтаксической ошибкой отклоняется."""
        with workdir() as folder:
            path = write_file(folder, "c.ini", "just text\n")
            with self.assertRaises(ConfigError):
                load_settings(path)

    def test_test_repo_file_missing(self):
        """В тестовом режиме отсутствующий файл репозитория — ошибка."""
        with workdir() as folder:
            path = write_test_config(folder, "A:\n", repo_url="/no/repo.txt")
            with self.assertRaises(ConfigError):
                load_settings(path)


if __name__ == "__main__":
    unittest.main()
