"""Исключения приложения."""


class ConfigError(Exception):
    """Ошибки конфигурации: хранит список сообщений по параметрам."""

    def __init__(self, messages):
        """Сохраняет список сообщений об ошибках."""
        super().__init__("; ".join(messages))
        self.messages = list(messages)


class RepositoryError(Exception):
    """Ошибка получения данных о пакете из репозитория."""


class RenderError(Exception):
    """Ошибка построения изображения графа."""
