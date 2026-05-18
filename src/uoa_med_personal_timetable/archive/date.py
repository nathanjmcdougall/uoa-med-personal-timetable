from datetime import datetime


def fixdate2(x):
    dt = datetime.strptime(x, "%d/%m/%Y %I:%M %p")
    x = dt.isoformat()
    return x


def fixdate(x):
    dt = datetime.strptime(x, "%d %b %Y %I:%M %p")
    x = dt.isoformat()
    return x
