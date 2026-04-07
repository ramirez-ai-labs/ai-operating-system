import importlib


def test_packaged_entrypoints_import_cleanly() -> None:
    """Editable-install entrypoints should stay importable in CI and local environments."""
    assert importlib.import_module("apps.api.main")
    assert importlib.import_module("director_os.workflows.weekly_update")
    assert importlib.import_module("brand_os.workflows.content_draft")
