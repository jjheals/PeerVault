import datetime as dt


def now() -> str: 
    """Returns the current time as a string for debugging."""
    return dt.datetime.now().strftime('%H:%M:%S')