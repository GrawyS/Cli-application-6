"""Тесты этапа 5: текст PlantUML и построение SVG."""

import os
import unittest
import zlib
from unittest import mock

from depviz.errors import RenderError, RepositoryError
from depviz.graph import build_graph
from depviz.plantuml import (
    ALPHABET, encode_plantuml, render_svg, save_source, save_svg,
    to_plantuml,
)
from helpers import workdir

SVG = b'<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg"/>'
GROUP = 4


def sample_graph():
    """Граф A -> B, B -> A (цикл), A -> C с обрезкой глубины."""
    table = {"A": ["B", "C"], "B": ["A"], "C": ["D"]}
    return build_graph("A", lambda node: table.get(node, []), 2)


def decode(text):
    """Обратное преобразование encode_plantuml (для проверки)."""
    values = [ALPHABET.index(char) for char in text]
    data = bytearray()
    for start in range(0, len(values), GROUP):
        a, b, c, d = values[start:start + GROUP]
        data += bytes([(a << 2) | (b >> 4),
                       ((b & 0xF) << 4) | (c >> 2),
                       ((c & 0x3) << 6) | d])
    return zlib.decompressobj(-zlib.MAX_WBITS).decompress(bytes(data))


class SourceTest(unittest.TestCase):
    """Текстовое представление графа."""

    def test_structure(self):
        """Диаграмма содержит узлы, рёбра и обрамление."""
        text = to_plantuml(sample_graph())
        self.assertTrue(text.startswith("@startuml"))
        self.assertTrue(text.rstrip().endswith("@enduml"))
        self.assertIn('rectangle "A" as n0 #LightBlue', text)
        self.assertIn("n0 --> n1", text)
        self.assertIn("n0 --> n2", text)

    def test_cycle_edge_highlighted(self):
        """Ребро цикла рисуется красным пунктиром."""
        self.assertIn("n1 -[#red,dashed]-> n0", to_plantuml(sample_graph()))

    def test_truncated_node_marked(self):
        """Не раскрытый из-за глубины узел помечен."""
        self.assertIn("(не раскрыт)", to_plantuml(sample_graph()))

    def test_quotes_escaped(self):
        """Кавычки в имени не ломают синтаксис."""
        graph = build_graph('a"b', lambda node: [], 2)
        self.assertIn("a'b", to_plantuml(graph))


class EncodingTest(unittest.TestCase):
    """Кодирование для сервера PlantUML."""

    def test_reference_vector(self):
        """Совпадение с примером из документации PlantUML."""
        self.assertEqual(
            encode_plantuml("Bob -> Alice : hello"),
            "SyfFKj2rKt3CoKnELR1Io4ZDoSa70000",
        )

    def test_roundtrip(self):
        """Закодированный текст восстанавливается."""
        text = "@startuml\nПривет -> мир\n@enduml"
        self.assertTrue(decode(encode_plantuml(text)).startswith(
            text.encode("utf-8")))


class RenderTest(unittest.TestCase):
    """Выбор способа рендеринга SVG."""

    def test_server_used_without_local_command(self):
        """Без локального plantuml запрашивается сервер."""
        urls = []

        def fetcher(url):
            """Запоминает URL и возвращает SVG."""
            urls.append(url)
            return SVG

        env = {"PLANTUML_CMD": "no-such-plantuml-binary"}
        with mock.patch.dict(os.environ, env):
            self.assertEqual(render_svg("@startuml\n@enduml", fetcher), SVG)
        self.assertIn("/svg/", urls[0])

    def test_server_error(self):
        """Ошибка сервера превращается в RenderError."""
        def fetcher(url):
            """Имитирует недоступный сервер."""
            raise RepositoryError("нет сети")

        env = {"PLANTUML_CMD": "no-such-plantuml-binary"}
        with mock.patch.dict(os.environ, env):
            with self.assertRaises(RenderError):
                render_svg("x", fetcher)

    def test_local_command(self):
        """Локальный plantuml вызывается с -tsvg -pipe."""
        done = mock.Mock(returncode=0, stdout=SVG, stderr=b"")
        with mock.patch("shutil.which", return_value="/bin/plantuml"):
            with mock.patch("subprocess.run", return_value=done) as run:
                self.assertEqual(render_svg("x"), SVG)
        self.assertIn("-tsvg", run.call_args.args[0])

    def test_local_command_failure(self):
        """Ненулевой код возврата plantuml — RenderError."""
        done = mock.Mock(returncode=1, stdout=b"", stderr=b"boom")
        with mock.patch("shutil.which", return_value="/bin/plantuml"):
            with mock.patch("subprocess.run", return_value=done):
                with self.assertRaisesRegex(RenderError, "boom"):
                    render_svg("x")

    def test_not_svg(self):
        """Ответ без <svg отклоняется."""
        done = mock.Mock(returncode=0, stdout=b"oops", stderr=b"")
        with mock.patch("shutil.which", return_value="/bin/plantuml"):
            with mock.patch("subprocess.run", return_value=done):
                with self.assertRaises(RenderError):
                    render_svg("x")


class SaveTest(unittest.TestCase):
    """Запись файлов."""

    def test_save_source_and_svg(self):
        """Файлы .puml и .svg создаются рядом."""
        with workdir() as folder:
            svg_path = os.path.join(folder, "g.svg")
            puml_path = save_source(sample_graph(), svg_path)
            save_svg(sample_graph(), svg_path, renderer=lambda text: SVG)
            self.assertTrue(puml_path.endswith("g.puml"))
            with open(puml_path, encoding="utf-8") as handle:
                self.assertIn("@startuml", handle.read())
            with open(svg_path, "rb") as handle:
                self.assertEqual(handle.read(), SVG)


if __name__ == "__main__":
    unittest.main()
