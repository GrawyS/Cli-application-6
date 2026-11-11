"""Выбор источника данных о пакетах по настройкам."""

from depviz.config import MODE_TEST
from depviz.maven import MavenRepository
from depviz.testrepo import FileRepository


def open_repository(settings):
    """Возвращает (репозиторий, корневой узел) для заданных настроек."""
    if settings.repo_mode == MODE_TEST:
        repository = FileRepository.from_file(settings.repo_url)
        return repository, settings.package_name
    root = f"{settings.package_name}:{settings.package_version}"
    return MavenRepository(settings.repo_url), root
