"""Локальная проверка правил оформления кода (см. список нарушений)."""

import ast
import os
import re
import sys

MAX_LINE = 80
MAX_FUNCTION_LINES = 40
MAX_COMPLEXITY = 10
MAX_ARGS = 7
MAX_FILE_LINES = 1000
SNAKE = re.compile(r"^_{0,2}[a-z][a-z0-9_]*_{0,2}$")
CAMEL = re.compile(r"^[A-Z][A-Za-z0-9]*$")
UPPER = re.compile(r"^_?[A-Z][A-Z0-9_]*$")
BRANCHES = (ast.If, ast.For, ast.While, ast.ExceptHandler, ast.IfExp,
            ast.Assert, ast.comprehension)
FUNCTIONS = (ast.FunctionDef, ast.AsyncFunctionDef)


def complexity(func):
    """Считает цикломатическую сложность функции."""
    total = 1
    for node in ast.walk(func):
        if isinstance(node, BRANCHES):
            total += 1
        elif isinstance(node, ast.BoolOp):
            total += len(node.values) - 1
    return total


def count_args(func):
    """Считает аргументы функции, исключая self и cls."""
    args = func.args
    names = [a.arg for a in args.posonlyargs + args.args + args.kwonlyargs]
    names = [name for name in names if name not in ("self", "cls")]
    return len(names) + bool(args.vararg) + bool(args.kwarg)


def magic_numbers(tree):
    """Возвращает номера строк с числовыми литералами в сравнениях."""
    lines = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare):
            continue
        for inner in ast.walk(node):
            is_number = isinstance(inner, ast.Constant) and isinstance(
                inner.value, (int, float)) and not isinstance(
                    inner.value, bool)
            if is_number:
                lines.append(inner.lineno)
    return lines


def check_function(path, func):
    """Проверяет длину, сложность, аргументы и docstring функции."""
    problems = []
    length = func.end_lineno - func.lineno + 1
    if length > MAX_FUNCTION_LINES:
        problems.append((func.lineno, f"функция {func.name}: {length} строк"))
    if complexity(func) > MAX_COMPLEXITY:
        problems.append((func.lineno, f"{func.name}: сложность"))
    if count_args(func) > MAX_ARGS:
        problems.append((func.lineno, f"{func.name}: много аргументов"))
    if ast.get_docstring(func) is None:
        problems.append((func.lineno, f"{func.name}: нет docstring"))
    if not SNAKE.match(func.name):
        problems.append((func.lineno, f"{func.name}: имя не по PEP8"))
    return [(path, line, text) for line, text in problems]


def check_names(path, tree):
    """Проверяет имена классов и констант уровня модуля."""
    problems = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and not CAMEL.match(node.name):
            problems.append((path, node.lineno, f"класс {node.name}"))
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    ok = UPPER.match(target.id) or SNAKE.match(target.id)
                    if not ok:
                        problems.append((path, node.lineno, target.id))
    problems += check_aliases(path, tree)
    return problems


def check_aliases(path, tree):
    """Проверяет, что псевдонимы импорта записаны в snake_case."""
    problems = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                if alias.asname and not SNAKE.match(alias.asname):
                    problems.append((path, node.lineno, alias.asname))
    return problems


def check_text(path, text):
    """Проверяет длину строк, размер файла и комментарии."""
    problems = []
    lines = text.splitlines()
    if len(lines) > MAX_FILE_LINES:
        problems.append((path, 1, "файл слишком большой"))
    for number, line in enumerate(lines, start=1):
        if len(line) > MAX_LINE:
            problems.append((path, number, f"строка {len(line)} символов"))
        if line.lstrip().startswith("#") and not line.startswith("#!"):
            problems.append((path, number, "комментарий вместо docstring"))
    return problems


def check_file(path):
    """Проверяет один Python-файл и возвращает список проблем."""
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    tree = ast.parse(text)
    problems = check_text(path, text)
    problems += check_names(path, tree)
    problems += [(path, n, "магическое число") for n in magic_numbers(tree)]
    if ast.get_docstring(tree) is None:
        problems.append((path, 1, "нет docstring модуля"))
    for node in ast.walk(tree):
        if isinstance(node, FUNCTIONS):
            problems += check_function(path, node)
    return problems


def python_files(roots):
    """Перечисляет .py-файлы в указанных каталогах."""
    for root in roots:
        for folder, _, names in os.walk(root):
            for name in sorted(names):
                if name.endswith(".py"):
                    yield os.path.join(folder, name)


def main(argv):
    """Запускает проверку и возвращает код завершения."""
    problems = []
    for path in python_files(argv or ["src", "tests", "tools"]):
        problems += check_file(path)
    for path, line, text in problems:
        print(f"{path}:{line}: {text}")
    print(f"Найдено проблем: {len(problems)}")
    return int(bool(problems))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
