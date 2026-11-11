"""Диаграмма PlantUML и SVG-изображение графа зависимостей (этап 5)."""

import os
import shlex
import shutil
import subprocess
import zlib

from depviz.errors import RenderError, RepositoryError
from depviz.maven import fetch_bytes

ALPHABET = ("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            "abcdefghijklmnopqrstuvwxyz-_")
COMPRESSION_LEVEL = 9
COMMAND_ENV = "PLANTUML_CMD"
SERVER_ENV = "PLANTUML_SERVER"
DEFAULT_COMMAND = "plantuml"
DEFAULT_SERVER = "https://www.plantuml.com/plantuml"
RENDER_TIMEOUT = 120
ROOT_COLOR = "#LightBlue"
TRUNCATED_COLOR = "#LightGray"
FAILED_COLOR = "#Salmon"


def _node_style(graph, node):
    """Возвращает цвет и пометку узла для диаграммы."""
    if node == graph.root:
        return ROOT_COLOR, ""
    if node in graph.failed:
        return FAILED_COLOR, "\\n(ошибка)"
    if node in graph.truncated:
        return TRUNCATED_COLOR, "\\n(не раскрыт)"
    return "", ""


def _all_nodes(graph):
    """Возвращает все узлы графа в порядке обхода."""
    nodes = list(graph.edges)
    for dependencies in graph.edges.values():
        nodes += [name for name in dependencies if name not in graph.edges]
    return list(dict.fromkeys(nodes))


def to_plantuml(graph):
    """Формирует текст диаграммы PlantUML для графа."""
    aliases = {node: f"n{index}"
               for index, node in enumerate(_all_nodes(graph))}
    lines = ["@startuml", f"title Зависимости {graph.root}",
             "left to right direction", "skinparam shadowing false"]
    for node, alias in aliases.items():
        color, note = _node_style(graph, node)
        label = node.replace('"', "'") + note
        lines.append(f'rectangle "{label}" as {alias} {color}'.rstrip())
    for node, dependencies in graph.edges.items():
        for dependency in dependencies:
            arrow = "-[#red,dashed]->" if (
                node, dependency) in graph.cycles else "-->"
            lines.append(f"{aliases[node]} {arrow} {aliases[dependency]}")
    return "\n".join(lines + ["@enduml", ""])


def _encode_triple(first, second, third):
    """Кодирует три байта четырьмя символами алфавита PlantUML."""
    indexes = (
        first >> 2,
        ((first & 0x3) << 4) | (second >> 4),
        ((second & 0xF) << 2) | (third >> 6),
        third & 0x3F,
    )
    return "".join(ALPHABET[index] for index in indexes)


def encode_plantuml(text):
    """Кодирует текст диаграммы для URL сервера PlantUML (deflate + base64)."""
    packer = zlib.compressobj(
        COMPRESSION_LEVEL, zlib.DEFLATED, -zlib.MAX_WBITS)
    data = packer.compress(text.encode("utf-8")) + packer.flush()
    data += bytes(-len(data) % 3)
    return "".join(_encode_triple(*data[start:start + 3])
                   for start in range(0, len(data), 3))


def _render_local(parts, source):
    """Запускает локальный PlantUML и возвращает SVG."""
    command = parts + ["-tsvg", "-pipe", "-charset", "UTF-8"]
    try:
        done = subprocess.run(
            command, input=source.encode("utf-8"), capture_output=True,
            timeout=RENDER_TIMEOUT, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RenderError(f"не удалось запустить PlantUML: {exc}") from exc
    if done.returncode:
        message = done.stderr.decode("utf-8", "replace").strip()
        raise RenderError(f"PlantUML завершился с ошибкой: {message}")
    return done.stdout


def _render_server(source, fetcher):
    """Запрашивает SVG у сервера PlantUML."""
    server = os.environ.get(SERVER_ENV, DEFAULT_SERVER).rstrip("/")
    url = f"{server}/svg/{encode_plantuml(source)}"
    try:
        return fetcher(url)
    except RepositoryError as exc:
        raise RenderError(f"сервер PlantUML недоступен: {exc}") from exc


def render_svg(source, fetcher=fetch_bytes):
    """Преобразует текст PlantUML в SVG: локально или через сервер."""
    parts = shlex.split(os.environ.get(COMMAND_ENV, DEFAULT_COMMAND))
    if parts and shutil.which(parts[0]):
        data = _render_local(parts, source)
    else:
        data = _render_server(source, fetcher)
    if b"<svg" not in data:
        raise RenderError("PlantUML вернул не SVG-изображение")
    return data


def save_source(graph, svg_path):
    """Сохраняет текст диаграммы рядом с SVG и возвращает путь к нему."""
    path = os.path.splitext(svg_path)[0] + ".puml"
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(to_plantuml(graph))
    return path


def save_svg(graph, svg_path, renderer=render_svg):
    """Рисует граф и записывает SVG-файл."""
    data = renderer(to_plantuml(graph))
    with open(svg_path, "wb") as handle:
        handle.write(data)
