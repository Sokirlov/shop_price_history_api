FROM python:3.12-slim
LABEL authors="sokirlov"

RUN apt-get install -y postgresql-client
RUN pip install --upgrade pip
WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY . /app