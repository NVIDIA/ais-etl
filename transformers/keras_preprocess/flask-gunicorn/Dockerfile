FROM python:slim

COPY requirements.txt requirements.txt
RUN pip3 install --upgrade -r requirements.txt

COPY app.py app.py

ENV PYTHONUNBUFFERED 1

ENV FLASK_APP=app.py

# Expose Gunicorn port
EXPOSE 80
