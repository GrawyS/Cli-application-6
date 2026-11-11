"""Тесты этапа 2: разбор POM и получение прямых зависимостей."""

import unittest
import urllib.error
from unittest import mock

from depviz.errors import RepositoryError
from depviz.maven import (
    MavenRepository, fetch_bytes, parse_pom, simplify_version, substitute,
)

NS = 'xmlns="http://maven.apache.org/POM/4.0.0"'
BASE = "https://repo.example.org/maven2"

PARENT = f"""<project {NS}>
  <groupId>org.example</groupId><artifactId>parent</artifactId>
  <version>1</version>
  <properties><lib.version>2.5</lib.version></properties>
  <dependencyManagement><dependencies>
    <dependency><groupId>org.managed</groupId><artifactId>m</artifactId>
      <version>${{lib.version}}</version></dependency>
  </dependencies></dependencyManagement>
</project>"""

APP = f"""<project {NS}>
  <parent><groupId>org.example</groupId><artifactId>parent</artifactId>
    <version>1</version></parent>
  <artifactId>app</artifactId><version>3.0</version>
  <properties><log.version>1.2</log.version></properties>
  <dependencies>
    <dependency><groupId>org.log</groupId><artifactId>log</artifactId>
      <version>${{log.version}}</version></dependency>
    <dependency><groupId>org.managed</groupId><artifactId>m</artifactId>
    </dependency>
    <dependency><groupId>org.self</groupId><artifactId>s</artifactId>
      <version>${{project.version}}</version></dependency>
    <dependency><groupId>org.t</groupId><artifactId>t</artifactId>
      <version>1</version><scope>test</scope></dependency>
    <dependency><groupId>org.o</groupId><artifactId>o</artifactId>
      <version>1</version><optional>true</optional></dependency>
    <dependency><groupId>org.u</groupId><artifactId>u</artifactId>
      <version>${{missing}}</version></dependency>
    <dependency><groupId>org.r</groupId><artifactId>r</artifactId>
      <version>[1.4,2.0)</version></dependency>
  </dependencies>
</project>"""


def make_repository():
    """Создаёт репозиторий с POM-файлами в памяти и счётчиком запросов."""
    files = {
        f"{BASE}/org/example/app/3.0/app-3.0.pom": APP.encode(),
        f"{BASE}/org/example/parent/1/parent-1.pom": PARENT.encode(),
    }
    calls = []

    def fetcher(url):
        """Отдаёт POM из памяти и запоминает запрошенные URL."""
        calls.append(url)
        if url not in files:
            raise RepositoryError(f"файл не найден (404): {url}")
        return files[url]

    return MavenRepository(BASE + "/", fetcher), calls


class ParsingTest(unittest.TestCase):
    """Разбор POM и вспомогательные функции."""

    def test_parse_with_namespace(self):
        """POM с пространством имён разбирается."""
        pom = parse_pom(APP.encode())
        self.assertEqual(pom.artifact, "app")
        self.assertEqual(pom.group, "org.example")
        self.assertEqual(len(pom.dependencies), 7)

    def test_invalid_xml(self):
        """Некорректный XML даёт RepositoryError."""
        with self.assertRaises(RepositoryError):
            parse_pom(b"<project>")

    def test_substitute_nested(self):
        """Свойства раскрываются рекурсивно."""
        props = {"a": "${b}", "b": "7"}
        self.assertEqual(substitute("v${a}", props), "v7")
        self.assertEqual(substitute("${zzz}", props), "${zzz}")

    def test_simplify_version(self):
        """Диапазон версий заменяется первой границей."""
        self.assertEqual(simplify_version("[1.4,2.0)"), "1.4")
        self.assertEqual(simplify_version("[1.0]"), "1.0")
        self.assertEqual(simplify_version("2.1"), "2.1")


class RepositoryTest(unittest.TestCase):
    """Получение прямых зависимостей."""

    def test_pom_url(self):
        """URL строится по правилам Maven."""
        repo, _ = make_repository()
        url = repo.pom_url("org.apache.commons", "commons-lang3", "3.14.0")
        self.assertEqual(
            url,
            BASE + "/org/apache/commons/commons-lang3/3.14.0/"
            "commons-lang3-3.14.0.pom",
        )

    def test_direct_dependencies(self):
        """Версии берутся из свойств, родителя и диапазонов."""
        repo, _ = make_repository()
        deps = repo.direct_dependencies("org.example:app:3.0")
        self.assertEqual(deps, [
            "org.log:log:1.2",
            "org.managed:m:2.5",
            "org.self:s:3.0",
            "org.r:r:1.4",
        ])

    def test_filtered_and_warned(self):
        """test/optional пропускаются, неразрешённые версии — в warnings."""
        repo, _ = make_repository()
        deps = repo.direct_dependencies("org.example:app:3.0")
        self.assertNotIn("org.t:t:1", deps)
        self.assertNotIn("org.o:o:1", deps)
        self.assertEqual(len(repo.warnings), 1)
        self.assertIn("org.u:u", repo.warnings[0])

    def test_pom_cached(self):
        """Повторный запрос не скачивает POM заново."""
        repo, calls = make_repository()
        repo.direct_dependencies("org.example:app:3.0")
        count = len(calls)
        repo.direct_dependencies("org.example:app:3.0")
        self.assertEqual(len(calls), count)

    def test_unknown_package(self):
        """Отсутствующий пакет даёт RepositoryError."""
        repo, _ = make_repository()
        with self.assertRaises(RepositoryError):
            repo.direct_dependencies("org.none:none:1")

    def test_bad_node_format(self):
        """Узел не в формате g:a:v отклоняется."""
        repo, _ = make_repository()
        with self.assertRaises(RepositoryError):
            repo.direct_dependencies("org.none:none")


class FetchTest(unittest.TestCase):
    """Обработка сетевых ошибок."""

    def test_not_found(self):
        """HTTP 404 превращается в понятное сообщение."""
        error = urllib.error.HTTPError("u", 404, "nf", {}, None)
        with mock.patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaisesRegex(RepositoryError, "404"):
                fetch_bytes("https://x/y.pom")

    def test_server_error(self):
        """Другие HTTP-ошибки сообщают код."""
        error = urllib.error.HTTPError("u", 500, "err", {}, None)
        with mock.patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaisesRegex(RepositoryError, "500"):
                fetch_bytes("https://x/y.pom")

    def test_network_down(self):
        """Недоступная сеть превращается в RepositoryError."""
        error = urllib.error.URLError("offline")
        with mock.patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaisesRegex(RepositoryError, "сети"):
                fetch_bytes("https://x/y.pom")


if __name__ == "__main__":
    unittest.main()
