FROM python:3.11-slim

WORKDIR /app

# Security: run as non-root
RUN groupadd -r lendiq && useradd -r -g lendiq lendiq

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY pyproject.toml README.md .
COPY src/ src/
RUN pip install -e . --no-deps

COPY . .

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; exit(0 if urllib.request.urlopen('http://localhost:8000/').status == 200 else 1)"

USER lendiq
EXPOSE 8000

CMD ["uvicorn", "lendiql.app:app", "--host", "0.0.0.0", "--port", "8000", "--limit-max-requests", "10000"]
