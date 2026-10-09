import sys

from .app import main, selftest

if "--selftest" in sys.argv[1:]:
    raise SystemExit(selftest())
raise SystemExit(main())
