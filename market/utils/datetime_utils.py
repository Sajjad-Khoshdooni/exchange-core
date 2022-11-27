from datetime import timedelta, datetime

def ceil_date(date, **kwargs):
    secs = timedelta(**kwargs).total_seconds()
    return datetime.fromtimestamp(date.timestamp() + secs - date.timestamp() % secs)

def floor_date(date, **kwargs):
    secs = timedelta(**kwargs).total_seconds()
    return datetime.fromtimestamp(date.timestamp() - date.timestamp() % secs)