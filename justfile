alias fmt := format
format:
  ruff format
  ruff check --fix-only --unsafe-fixes --select A,E,F,UP,B,SIM,I .
