FROM python:3.12-slim
LABEL authors="sokirlov"

RUN apk add --no-cache libc6-compat
RUN apk add --no-cache musl-locales musl-locales-lang

RUN pip install --upgrade pip
WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY . /app