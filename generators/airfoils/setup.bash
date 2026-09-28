if [ ! -d ".venv" ]; then
  python -m venv .venv
fi

source .venv/Scripts/activate

if [ ! -f "requirements.txt" ]; then
  echo "requirements.txt not found; skipping dependency installation." >&2
else
  python -m pip install --upgrade pip >/dev/null 2>&1 || true
  python -m pip install -r requirements.txt
fi
