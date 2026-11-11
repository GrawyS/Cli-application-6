"""Вспомогательные функции для тестов."""

import os
import tempfile
from contextlib import contextmanager

REAL_CONFIG = """[settings]
package_name = org.example:demo
repo_url = https://repo.example.org/maven2
repo_mode = real
package_version = 1.0.0
output_file = {output}
ascii_tree = true
max_depth = 3
"""

TEST_CONFIG = """[settings]
package_name = A
repo_url = {repo}
repo_mode = test
package_version =
output_file = {output}
ascii_tree = false
max_depth = 5
"""


@contextmanager
def workdir():
    """Создаёт временный каталог и убирает его после использования."""
    with tempfile.TemporaryDirectory() as folder:
        yield folder


def write_file(folder, name, text):
    """Записывает текстовый файл во временный каталог, возвращает путь."""
    path = os.path.join(folder, name)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    return path


def apply_overrides(text, overrides):
    """Заменяет значения параметров в тексте INI-файла."""
    for key, value in overrides.items():
        lines = [line for line in text.splitlines()
                 if not line.startswith(key + " =")]
        lines.append(f"{key} = {value}")
        text = "\n".join(lines) + "\n"
    return text


def write_real_config(folder, **overrides):
    """Создаёт INI-файл для реального режима с подменой значений."""
    text = REAL_CONFIG.format(output=os.path.join(folder, "g.svg"))
    return write_file(folder, "config.ini", apply_overrides(text, overrides))


def write_test_config(folder, repo_text, **overrides):
    """Создаёт тестовый репозиторий и INI-файл для тестового режима."""
    repo = write_file(folder, "repo.txt", repo_text)
    text = TEST_CONFIG.format(
        repo=repo, output=os.path.join(folder, "g.svg"))
    return write_file(folder, "config.ini", apply_overrides(text, overrides))
