import os
import subprocess


def background_subprocess_kwargs() -> dict[str, object]:
    kwargs: dict[str, object] = {}
    if os.name != "nt":
        return kwargs

    creationflags = int(getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if creationflags:
        kwargs["creationflags"] = creationflags
    startupinfo_class = getattr(subprocess, "STARTUPINFO", None)
    if startupinfo_class is not None:
        startupinfo = startupinfo_class()
        startf_use_show_window = int(getattr(subprocess, "STARTF_USESHOWWINDOW", 0))
        startupinfo.dwFlags |= startf_use_show_window
        startupinfo.wShowWindow = int(getattr(subprocess, "SW_HIDE", 0))
        kwargs["startupinfo"] = startupinfo
    return kwargs
