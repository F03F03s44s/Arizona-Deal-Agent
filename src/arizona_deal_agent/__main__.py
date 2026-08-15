"""Allow ``python -m arizona_deal_agent``."""

import sys

from .cli import main

sys.exit(main())
