FROM hub.hamdocker.ir/library/python:3.10
RUN apt update && apt -y install gettext
WORKDIR /app
ADD ./requirements.txt ./
RUN pip install -r ./requirements.txt
ADD ./ ./
RUN python manage.py compilemessages
CMD python manage.py migrate && gunicorn --workers 5 --bind 0.0.0.0:8000 _base.wsgi
