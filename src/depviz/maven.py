"""Прямые зависимости Maven-пакета из POM-файла (этап 2).

Менеджеры пакетов и сторонние библиотеки не используются: POM
скачивается по HTTP и разбирается стандартным XML-парсером.
"""

import re
import urllib.error
import urllib.request
from xml.etree import ElementTree
from dataclasses import dataclass

from depviz.errors import RepositoryError

TIMEOUT_SECONDS = 15
MAX_PARENT_CHAIN = 10
MAX_SUBSTITUTIONS = 10
HTTP_NOT_FOUND = 404
SKIPPED_SCOPES = ("test", "provided", "system", "import")
DEFAULT_SCOPE = "compile"
PLACEHOLDER = re.compile(r"\$\{([^}]+)\}")
RANGE_CHARS = "[]() "
COORDINATE_PARTS = 3


@dataclass
class Dependency:
    """Зависимость, как она записана в POM."""

    group: str
    artifact: str
    version: str
    scope: str
    optional: bool


@dataclass
class Pom:
    """Разобранный POM-файл."""

    group: str
    artifact: str
    version: str
    parent: tuple
    properties: dict
    managed: dict
    dependencies: list


def fetch_bytes(url):
    """Скачивает файл по URL и возвращает его содержимое."""
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT_SECONDS) as reply:
            return reply.read()
    except urllib.error.HTTPError as exc:
        if exc.code == HTTP_NOT_FOUND:
            raise RepositoryError(f"файл не найден (404): {url}") from exc
        raise RepositoryError(f"ошибка HTTP {exc.code}: {url}") from exc
    except OSError as exc:
        raise RepositoryError(f"ошибка сети ({exc}): {url}") from exc


def _strip_namespaces(root):
    """Убирает пространства имён из тегов, чтобы упростить поиск."""
    for element in root.iter():
        if isinstance(element.tag, str):
            element.tag = element.tag.rpartition("}")[2]


def _text(element, path):
    """Возвращает текст вложенного элемента без пробелов или ''."""
    return (element.findtext(path) or "").strip()


def _parse_dependency(element):
    """Создаёт Dependency из элемента <dependency>."""
    return Dependency(
        group=_text(element, "groupId"),
        artifact=_text(element, "artifactId"),
        version=_text(element, "version"),
        scope=_text(element, "scope") or DEFAULT_SCOPE,
        optional=_text(element, "optional").lower() == "true",
    )


def _parse_parent(root):
    """Возвращает (group, artifact, version) родителя или ()."""
    parent = root.find("parent")
    if parent is None:
        return ()
    return (_text(parent, "groupId"), _text(parent, "artifactId"),
            _text(parent, "version"))


def _parse_properties(root):
    """Возвращает словарь <properties> из POM."""
    block = root.find("properties")
    if block is None:
        return {}
    return {child.tag: (child.text or "").strip() for child in block}


def _parse_managed(root):
    """Возвращает версии из <dependencyManagement> по ключу group:artifact."""
    managed = {}
    path = "dependencyManagement/dependencies/dependency"
    for element in root.findall(path):
        dep = _parse_dependency(element)
        if dep.scope != "import" and dep.version:
            managed[f"{dep.group}:{dep.artifact}"] = dep.version
    return managed


def parse_pom(data):
    """Разбирает байты POM-файла в объект Pom."""
    try:
        root = ElementTree.fromstring(data)
    except ElementTree.ParseError as exc:
        raise RepositoryError(f"POM не является корректным XML: {exc}") from exc
    _strip_namespaces(root)
    parent = _parse_parent(root)
    inherited = parent or ("", "", "")
    return Pom(
        group=_text(root, "groupId") or inherited[0],
        artifact=_text(root, "artifactId"),
        version=_text(root, "version") or inherited[2],
        parent=parent,
        properties=_parse_properties(root),
        managed=_parse_managed(root),
        dependencies=[_parse_dependency(e)
                      for e in root.findall("dependencies/dependency")],
    )


def substitute(text, properties):
    """Подставляет ${имя} из словаря свойств (до полного раскрытия)."""
    for _ in range(MAX_SUBSTITUTIONS):
        result = PLACEHOLDER.sub(
            lambda found: properties.get(found.group(1), found.group(0)),
            text,
        )
        if result == text:
            break
        text = result
    return text


def simplify_version(version):
    """Для диапазона версий берёт первую границу, иначе возвращает как есть."""
    if version.lstrip(RANGE_CHARS) == version:
        return version
    bounds = [part.strip(RANGE_CHARS) for part in version.split(",")]
    return next((bound for bound in bounds if bound), "")


def is_runtime(dependency):
    """True, если зависимость попадает в итоговый граф."""
    return not dependency.optional and dependency.scope not in SKIPPED_SCOPES


class MavenRepository:
    """Maven-репозиторий, доступный по HTTP."""

    def __init__(self, base_url, fetcher=fetch_bytes):
        """Запоминает URL репозитория и функцию скачивания файлов."""
        self.base_url = base_url.rstrip("/")
        self.warnings = []
        self._fetch = fetcher
        self._cache = {}

    def pom_url(self, group, artifact, version):
        """Строит URL POM-файла по правилам Maven-репозитория."""
        folder = group.replace(".", "/")
        name = f"{artifact}-{version}.pom"
        return f"{self.base_url}/{folder}/{artifact}/{version}/{name}"

    def load_pom(self, group, artifact, version):
        """Скачивает и разбирает POM (результат кэшируется)."""
        key = (group, artifact, version)
        if key not in self._cache:
            url = self.pom_url(group, artifact, version)
            self._cache[key] = parse_pom(self._fetch(url))
        return self._cache[key]

    def _chain(self, pom):
        """Возвращает [pom, родитель, прародитель, ...]."""
        chain = [pom]
        while pom.parent and len(chain) <= MAX_PARENT_CHAIN:
            try:
                pom = self.load_pom(*pom.parent)
            except RepositoryError as exc:
                self.warnings.append(f"родительский POM недоступен: {exc}")
                break
            chain.append(pom)
        return chain

    def _context(self, pom):
        """Собирает свойства и управляемые версии с учётом родителей."""
        properties, managed = {}, {}
        for item in reversed(self._chain(pom)):
            properties.update(item.properties)
            managed.update(item.managed)
        for prefix in ("project", "pom"):
            properties[f"{prefix}.version"] = pom.version
            properties[f"{prefix}.groupId"] = pom.group
            properties[f"{prefix}.artifactId"] = pom.artifact
        return properties, managed

    def _resolve(self, dep, properties, managed):
        """Возвращает 'group:artifact:version' или None, если версии нет."""
        group = substitute(dep.group, properties)
        artifact = substitute(dep.artifact, properties)
        version = dep.version or managed.get(f"{group}:{artifact}", "")
        version = simplify_version(substitute(version, properties))
        if not version or "${" in version:
            self.warnings.append(
                f"версия {group}:{artifact} не определена, пропущено")
            return None
        return f"{group}:{artifact}:{version}"

    def direct_dependencies(self, node):
        """Возвращает прямые зависимости узла 'group:artifact:version'."""
        parts = node.split(":")
        if len(parts) != COORDINATE_PARTS:
            raise RepositoryError(f"'{node}': нужен формат g:a:version")
        pom = self.load_pom(*parts)
        properties, managed = self._context(pom)
        result = []
        for dep in filter(is_runtime, pom.dependencies):
            resolved = self._resolve(dep, properties, managed)
            if resolved and resolved not in result:
                result.append(resolved)
        return result
