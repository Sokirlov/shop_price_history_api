FROM python:3.12-slim
LABEL authors="sokirlov"

WORKDIR /app
COPY . /app

RUN pip install --upgrade pip
RUN pip install -r requirements.txt
