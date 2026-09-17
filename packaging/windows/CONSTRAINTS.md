# Windows packaging constraints

`constraints-windows.txt` records the dependency versions used for the Windows application bundle. It is intentionally not applied to ordinary macOS or Linux development installs.

The Windows packaging workflow installs `packaging/windows/requirements-build.txt`. That file references the constraints and includes the project with its `full` and `dev` extras, so both application and build dependencies are resolved under the same Windows-only pins.

## Refreshing the constraints

1. Create a clean Python 3.12 virtual environment on Windows.
2. Temporarily install the project without the old constraints: `python -m pip install -e ".[full,dev]"` and `python -m pip install -r packaging/windows/requirements-build.txt --no-deps`.
3. Review the resolved versions with `python -m pip freeze` and update the curated direct and critical runtime pins in `constraints-windows.txt`. Keep Transformers on the version required by the project and keep Torch and Torchvision on a documented compatible pair.
4. Recreate the clean environment and install normally with `python -m pip install -r packaging/windows/requirements-build.txt`.
5. Run `python -m pip check`, `ruff check .`, and `pytest`.
6. Run `packaging/windows/build.ps1` and verify both packaged executables with the existing smoke checks.
7. Commit constraint changes only after the Windows package workflow succeeds.

Do not copy these pins into `pyproject.toml` unless they are required on every supported platform. The constraints exist to make the Windows binary reproducible without restricting normal macOS and Linux dependency resolution.
