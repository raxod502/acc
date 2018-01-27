import datetime

def json_serializer(obj):
    if isinstance(obj, datetime.date):
        return obj.strftime("%Y-%m-%d")
    if isinstance(obj, datetime.datetime):
        return obj.strftime("%Y-%m-%d %H:%M:%S%z")
    raise TypeError("Object of type '{}' is not JSON serializable".format(type(obj)))
