def main() -> int:
    from docling.cli.tools import app

    app(prog_name="docling-tools")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
