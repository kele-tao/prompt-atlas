"""Allow ``python -m prompt_atlas``."""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
