"""Загрузка и проверка настроек из INI-файла (этап 1)."""

import configparser
import os
import re
from dataclasses import asdict, dataclass
from urllib.parse import urlparse

from depviz.errors import ConfigError

SECTION = "settings"
MODE_REAL = "real"
MODE_TEST = "test"
MODES = (MODE_REAL, MODE_TEST)
MIN_DEPTH = 1
IMAGE_EXTENSION = ".svg"
HTTP_SCHEMES = ("http", "https")
TRUE_VALUES = ("true", "1", "yes", "on")
FALSE_VALUES = ("false", "0", "no", "off")
MAVEN_NAME = re.compile(r"^[\w.\-]+:[\w.\-]+$")
TEST_NAME = re.compile(r"^[A-Z]+$")
VERSION_NAME = re.compile(r"^[\w.\-]+$")
MSG_EMPTY = "параметр не задан"


@dataclass(frozen=True)
class Settings:
    """Проверенные настройки пользователя."""

    package_name: str
    repo_url: str
    repo_mode: str
    package_version: str
    output_file: str
    ascii_tree: bool
    max_depth: int


def _non_empty(raw):
    """Возвращает значение или поднимает ValueError, если оно пустое."""
    if not raw:
        raise ValueError(MSG_EMPTY)
    return raw


def check_mode(raw, mode):
    """Проверяет режим работы с репозиторием: real или test."""
    value = _non_empty(raw).lower()
    if value not in MODES:
        allowed = ", ".join(MODES)
        raise ValueError(f"допустимо: {allowed}; получено '{raw}'")
    return value


def check_package_name(raw, mode):
    """Проверяет имя пакета: groupId:artifactId или заглавные буквы."""
    value = _non_empty(raw)
    if mode == MODE_TEST:
        pattern, hint = TEST_NAME, "заглавные латинские буквы, например A"
    else:
        pattern, hint = MAVEN_NAME, "формат groupId:artifactId"
    if not pattern.match(value):
        raise ValueError(f"'{raw}' не подходит: {hint}")
    return value


def check_repo_url(raw, mode):
    """Проверяет URL репозитория или путь к файлу тестового репозитория."""
    value = _non_empty(raw)
    if mode == MODE_TEST:
        if not os.path.isfile(value):
            raise ValueError(f"файл тестового репозитория '{value}' не найден")
        return value
    parsed = urlparse(value)
    if parsed.scheme not in HTTP_SCHEMES or not parsed.netloc:
        raise ValueError(f"'{raw}' должен быть URL вида https://host/path")
    return value


def check_version(raw, mode):
    """Проверяет версию пакета; в тестовом режиме она не используется."""
    if mode == MODE_TEST:
        return raw
    value = _non_empty(raw)
    if value.lower() == "latest":
        raise ValueError("'latest' не поддерживается, укажите версию")
    if not VERSION_NAME.match(value):
        raise ValueError(f"'{raw}' содержит недопустимые символы")
    return value


def check_output_file(raw, mode):
    """Проверяет имя SVG-файла и существование его каталога."""
    value = _non_empty(raw)
    if not value.lower().endswith(IMAGE_EXTENSION):
        raise ValueError(f"'{raw}' должен иметь расширение {IMAGE_EXTENSION}")
    folder = os.path.dirname(value) or "."
    if not os.path.isdir(folder):
        raise ValueError(f"каталог '{folder}' не существует")
    return value


def check_ascii_tree(raw, mode):
    """Преобразует значение в логическое (true/false)."""
    value = _non_empty(raw).lower()
    if value in TRUE_VALUES:
        return True
    if value in FALSE_VALUES:
        return False
    raise ValueError(f"'{raw}' должно быть true или false")


def check_max_depth(raw, mode):
    """Проверяет максимальную глубину: целое число не меньше 1."""
    value = _non_empty(raw)
    try:
        depth = int(value)
    except ValueError:
        raise ValueError(f"'{raw}' не является целым числом") from None
    if depth < MIN_DEPTH:
        raise ValueError(f"значение должно быть не меньше {MIN_DEPTH}")
    return depth


CHECKS = (
    ("repo_mode", check_mode),
    ("package_name", check_package_name),
    ("repo_url", check_repo_url),
    ("package_version", check_version),
    ("output_file", check_output_file),
    ("ascii_tree", check_ascii_tree),
    ("max_depth", check_max_depth),
)


def _validate(section):
    """Проверяет все параметры секции и собирает Settings."""
    errors = [f"{name}: неизвестный параметр" for name in section
              if name not in dict(CHECKS)]
    values = {}
    mode = MODE_REAL
    for name, check in CHECKS:
        try:
            values[name] = check(section.get(name, "").strip(), mode)
        except ValueError as exc:
            errors.append(f"{name}: {exc}")
            continue
        if name == "repo_mode":
            mode = values[name]
    if errors:
        raise ConfigError(errors)
    return Settings(**values)


def load_settings(path):
    """Читает INI-файл и возвращает проверенные настройки."""
    parser = configparser.ConfigParser(interpolation=None)
    try:
        loaded = parser.read(path, encoding="utf-8")
    except (configparser.Error, OSError, ValueError) as exc:
        raise ConfigError([f"не удалось прочитать '{path}': {exc}"]) from exc
    if not loaded:
        raise ConfigError([f"файл конфигурации '{path}' не найден"])
    if not parser.has_section(SECTION):
        raise ConfigError([f"в '{path}' нет секции [{SECTION}]"])
    return _validate(parser[SECTION])


def format_settings(settings):
    """Возвращает строки 'ключ = значение' для вывода настроек."""
    return [f"{key} = {value}" for key, value in asdict(settings).items()]
