from source_doc_converter import subprocess_utils


def test_background_kwargs_default_non_windows() -> None:
    kwargs = subprocess_utils.background_subprocess_kwargs()
    assert isinstance(kwargs, dict)


def test_background_kwargs_include_hidden_flags_on_windows(monkeypatch) -> None:
    monkeypatch.setattr(subprocess_utils.os, "name", "nt")
    monkeypatch.setattr(subprocess_utils.subprocess, "CREATE_NO_WINDOW", 134217728, raising=False)
    monkeypatch.setattr(subprocess_utils.subprocess, "STARTF_USESHOWWINDOW", 1, raising=False)
    monkeypatch.setattr(subprocess_utils.subprocess, "SW_HIDE", 0, raising=False)

    class StartupInfo:
        def __init__(self) -> None:
            self.dwFlags = 0
            self.wShowWindow = 5

    monkeypatch.setattr(subprocess_utils.subprocess, "STARTUPINFO", StartupInfo, raising=False)

    kwargs = subprocess_utils.background_subprocess_kwargs()

    assert kwargs["creationflags"] == 134217728
    assert kwargs["startupinfo"].dwFlags & 1
    assert kwargs["startupinfo"].wShowWindow == 0
