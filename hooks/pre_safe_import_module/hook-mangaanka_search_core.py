"""Expose live pure modules to Analysis; runtime loader enforces live priority."""
import os


def pre_safe_import_module(api):
    api.append_package_path(os.environ.get(
        'MANGAANKA_PLUGIN_PATH', r'C:\MangaNana-Dev\MangaNana-calibre'))
