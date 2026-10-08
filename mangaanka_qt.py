"""Launch the primary Qt DDK; the legacy Tk entry point remains available."""
from qt_app.app import main

if __name__ == '__main__':
    raise SystemExit(main())
