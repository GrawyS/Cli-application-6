"""Вывод зависимостей в виде ASCII-дерева (этап 5)."""

BRANCH = "├── "
LAST = "└── "
PIPE = "│   "
SPACE = "    "


def _marker(graph, parent, node, seen):
    """Возвращает пометку узла: цикл, повтор, обрезка или ошибка."""
    if (parent, node) in graph.cycles:
        return " (цикл)"
    if node in seen and graph.edges.get(node):
        return " (см. выше)"
    if node in graph.failed:
        return " (ошибка)"
    if node in graph.truncated:
        return " (...)"
    return ""


def _child_prefix(prefix, connector, is_last):
    """Возвращает отступ для потомков узла."""
    if not connector:
        return prefix
    return prefix + (SPACE if is_last else PIPE)


def _push_children(stack, children, prefix, parent):
    """Кладёт потомков на стек в обратном порядке, сохраняя порядок вывода."""
    if not children:
        return
    final = children[-1]
    for child in reversed(children):
        connector = LAST if child == final else BRANCH
        stack.append((child, prefix, connector, child == final, parent))


def render_tree(graph):
    """Строит ASCII-дерево итеративно и возвращает его как текст."""
    lines, seen = [], set()
    stack = [(graph.root, "", "", True, None)]
    while stack:
        node, prefix, connector, is_last, parent = stack.pop()
        mark = _marker(graph, parent, node, seen)
        lines.append(prefix + connector + node + mark)
        expand = node not in seen and (parent, node) not in graph.cycles
        seen.add(node)
        if expand:
            child_prefix = _child_prefix(prefix, connector, is_last)
            children = graph.edges.get(node, [])
            _push_children(stack, children, child_prefix, node)
    return "\n".join(lines)
