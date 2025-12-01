FROM python:3.11

WORKDIR /app

# Installer pandas + pymongo + numpy
RUN pip install pandas pymongo numpy

COPY import_flat.py /app/import_flat.py

CMD ["python", "/app/import_flat.py"]
