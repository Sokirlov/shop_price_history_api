FROM python:3.12-alpine3.22
LABEL authors="sokirlov"

#RUN apt-get update && apt-get install -y locales && \
#    locale-gen en_US.UTF-8 && \
#    apt-get install -y postgresql-client

RUN apk update && \
    apk add --no-cache postgresql-client musl-locales musl-locales-lang

ENV LANG=en_US.UTF-8 \
    LANGUAGE=en_US:en \
    LC_ALL=en_US.UTF-8

#ENV LANG en_US.UTF-8
#ENV LANGUAGE en_US:en
#ENV LC_ALL en_US.UTF-8

RUN pip install --upgrade pip
WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY . /app