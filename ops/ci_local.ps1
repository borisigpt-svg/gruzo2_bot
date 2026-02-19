python -m pip install --upgrade pip
if (Test-Path "requirements.txt") { python -m pip install -r requirements.txt }
python -m pip install ruff
python -m ruff check .
python -m compileall .
