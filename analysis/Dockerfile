FROM python:3.11

WORKDIR /app

COPY query_polars.py /app/query_polars.py

RUN pip install polars

CMD ["python", "query_polars.py"]
