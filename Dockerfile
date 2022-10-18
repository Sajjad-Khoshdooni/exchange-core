FROM python:3.10-alpine
RUN apk add --update gettext gcc linux-headers openssh-client
WORKDIR /
ADD ./requirements.txt ./
RUN pip install -r ./requirements.txt
ADD ./ ./
ENTRYPOINT ["/bin/sh", "-c" , "python manage.py collectstatic && python manage.py compilemessages && python manage.py migrate && gunicorn --bind 0.0.0.0:8000 _base.wsgi"]
