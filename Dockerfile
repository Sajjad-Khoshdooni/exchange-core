FROM hub.hamdocker.ir/library/python:3.10
WORKDIR /
ADD ./requirements.txt ./
RUN pip install -r ./requirements.txt
ADD ./ ./
ENTRYPOINT ["/bin/sh", "-c" , "python manage.py collectstatic && python manage.py compilemessages && python manage.py migrate && gunicorn --bind 0.0.0.0:8000 _base.wsgi"]
