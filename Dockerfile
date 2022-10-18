FROM python:3.10-alpine
RUN apk update && apk upgrade \
    && apk add postgresql-client \
        postgresql-dev \
        musl-dev \
        gcc \
        linux-headers \
        gettext-dev

ENV PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=UTF-8

WORKDIR /
ADD ./requirements.txt ./
RUN pip install -r ./requirements.txt
ADD ./ ./
ENTRYPOINT ["/bin/sh", "-c" , "python manage.py collectstatic && python manage.py compilemessages && python manage.py migrate && gunicorn --bind 0.0.0.0:8000 _base.wsgi"]
