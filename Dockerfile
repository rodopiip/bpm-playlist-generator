FROM python:3.12.6-slim-bookworm

COPY app.py /app.py
COPY static /static
COPY templates /templates
COPY requirements.txt /requirements.txt

RUN pip install -r /requirements.txt

CMD ["gunicorn", "-b", "0.0.0.0:8888", "app:app"]