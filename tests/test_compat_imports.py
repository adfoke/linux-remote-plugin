import importlib


def test_old_package_aliases_new_runtime_module():
    legacy_module = importlib.import_module("linux_remote_plugin.runtime_adapter")
    new_module = importlib.import_module("linux_remote_tool.runtime_adapter")

    assert legacy_module is new_module
