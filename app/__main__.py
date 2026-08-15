"""Allow `python -m app` to rank deals from the terminal."""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
