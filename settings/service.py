import importlib
import os
import pkgutil
from pathlib import Path

from settings.config import BASE_DIR


def import_admin_modules():
    """
    Імпортує всі файли admin.py із заданої директорії рекурсивно.

    :param base_path: Базовий шлях до модуля, наприклад, "my_project".
    :param package_name: Назва пакету, наприклад, "my_project".
    """
    base_path = BASE_DIR
    for module_info in pkgutil.walk_packages([str(base_path)]):
        if "admin" in module_info.name:
            try:
                importlib.import_module(module_info.name)
                print(f"Імпортовано: {module_info.name}")
            except Exception as e:
                print(f"Помилка імпорту {module_info.name}: {e}")


