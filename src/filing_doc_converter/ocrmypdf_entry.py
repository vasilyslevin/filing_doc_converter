def main() -> int:
    from ocrmypdf.__main__ import run

    result = run()
    return int(result) if result is not None else 0


if __name__ == "__main__":
    raise SystemExit(main())
