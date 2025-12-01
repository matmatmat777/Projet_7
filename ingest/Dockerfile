FROM python:3.11-slim

WORKDIR /app

# Dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Code
COPY ingest_nested.py .

# Commande par défaut
CMD ["python", "ingest_nested.py"]
