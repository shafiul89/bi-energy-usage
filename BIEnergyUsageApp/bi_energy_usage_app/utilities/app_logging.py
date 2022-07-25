import datetime
import bi_energy_usage_app.utilities.app_environment as app_env
import bi_energy_usage_app.utilities.safe_json as safe_json
import json
import logging
import sys
import traceback


def get_exception_attributes(e):
    """
    Get the additional attributes of a Python ExceptionInfo object.

    Parameters
    ----------
    e : The Python ExceptionInfo object.

    Returns
    -------
    dict
        A dictionary containing the exception attributes.
    """
    attribute_names = dir(e)
    attribute_values = {}
    for attribute_name in attribute_names:
        if attribute_name.startswith('_') or attribute_name in ['with_traceback']:
            continue
        if hasattr(e, attribute_name):
            attribute_value = getattr(e, attribute_name)
        elif attribute_name in e.__dict__:
            attribute_value = e.__dict__[attribute_name]
        else:
            continue
        if safe_json.is_safe_json(attribute_value):
            attribute_values[attribute_name] = attribute_value
        else:
            attribute_values[attribute_name] = safe_json.get_safe_json(attribute_value, 8192)
    return attribute_values


def get_safe_json_value(x, max_length: int):
    """
    Get a JSON-safe representation of the specified value/object.

    The specified value/object is tested to see whether it can be converted to JSON.  If it can, the value/object is
    returned unchanged.  If the value/object cannot be converted to JSON, a best-efforts attempt is made to get a JSON
    representation of the object.  This probably won't be perfect, but should be good enough for logging/debugging
    purposes.

    The purpose of returning the original object unchanged is that it can be added to a larger object which later will
    be converted to JSON.  If we always converted the object to JSON now, then we would have encoded-JSON embedded
    inside JSON.  Better to preserve some structure where we can and only resort to embedded JSON as a fallback if
    needed.

    Parameters
    ----------
    x : Any
        The object to check/convert to JSON.
    max_length : int
        The maximum length of the string that is returned when JSON-unsafe values/objects are converted to JSON.

    Returns
    -------
    Any | str
        Either the original object unmodified, or the value/object converted to JSON.
    """
    if safe_json.is_safe_json(x):
        if type(x) is str and len(x) > max_length:
            return x[0: max_length]
        else:
            return x
    else:
        return safe_json.get_safe_json(x, max_length)


class JSONFormatter(logging.Formatter):
    """
    A class to format a log record in JSON.

    The log formatter takes a Python LogRecord produced by the Python logging framework and converts it to a string
    in JSON format.

    This class is intended to be used to generate log records for AWS CloudWatch - and in particular that can be
    analysed by AWS CloudWatch LogInsights.

    For more details of formatter objects, see:  https://docs.python.org/3/library/logging.html#formatter-objects
    """

    # constants
    MAX_LOG_FIELD_LENGTH = 32768

    # init
    def __init__(self, log_name):
        """
        Create a new instance of the JSON log record formatter.

        Parameters
        ----------
        log_name : The name of the log.
        """
        super().__init__()
        self.log_name = log_name
        self.instance = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
        self.log_index = 0

    def format(self, record):
        """
        Format a Python log record in JSON.

        As well as the log message, various additional pieces of information are captured and included in the
        JSON log record that is generated.

        Parameters
        ----------
        record : LogRecord
            The log record produced by the Python logging framework.

        Returns
        -------
        str
            The log record formatted in JSON.
        """
        self.log_index += 1

        log_data = {
            'logName': self.log_name,
            'instance': self.instance,
            'logger': record.name if hasattr(record, 'name') else '-',
            'id': self.log_index,
            'level': record.levelname,
            'atUtc': datetime.datetime.utcfromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S.%f'),
            'event': get_safe_json_value(record.msg, self.MAX_LOG_FIELD_LENGTH)
        }
        if hasattr(record, "args") and record.args is not None and len(record.args) > 0:
            log_data['args'] = get_safe_json_value(record.args, self.MAX_LOG_FIELD_LENGTH)

        if record.exc_info is not None:
            exception_attributes = get_exception_attributes(record.exc_info[1])
            exception_attributes = get_safe_json_value(exception_attributes, 131072)
            exception = {
                'name': record.exc_info[0].__name__,
                'qualname': record.exc_info[0].__qualname__,
                'class': str(record.exc_info[0]),
                'module': record.exc_info[0].__module__,
                'msg': str(record.exc_info[1]),
                'attributes': exception_attributes
            }
            tb = traceback.format_exception(record.exc_info[0], record.exc_info[1], record.exc_info[2])
            exception['traceback'] = get_safe_json_value(tb, self.MAX_LOG_FIELD_LENGTH)
            log_data['exception'] = exception
            record.exc_info = None  # to stop the exception and traceback being printed in the log message as plain text
        if hasattr(record, 'pathname') or hasattr(record, 'filename') or hasattr(record, 'module') or \
                hasattr(record, 'lineno') or hasattr(record, 'funcName'):
            source = {}
            if hasattr(record, 'pathname'):
                source['pathname'] = record.pathname
            if hasattr(record, 'filename'):
                source['filename'] = record.filename
            if hasattr(record, 'module'):
                source['module'] = record.module
            if hasattr(record, 'lineno'):
                source['lineNumber'] = record.lineno
            if hasattr(record, 'funcName'):
                source['funcName'] = record.funcName
            log_data['source'] = source
        log_details = {
            'levelNumber': record.levelno,
            'atUtc': record.created
        }
        if hasattr(record, 'process'):
            log_details['processId'] = record.process
        if hasattr(record, 'processName'):
            log_details['processName'] = record.processName
        if hasattr(record, 'thread'):
            log_details['threadId'] = record.thread
        if hasattr(record, 'threadName'):
            log_details['threadName'] = record.threadName
        if hasattr(record, 'stack_info') and record.stack_info is not None:
            log_details['stack'] = record.stack_info
        log_data['details'] = log_details

        all_attributes = dir(record)
        standard_attributes = ['name', 'msg', 'args', 'asctime', 'levelname', 'levelno', 'pathname', 'filename',
                               'module', 'exc_info', 'exc_text', 'stack_info', 'lineno', 'funcName', 'created', 'msecs',
                               'relativeCreated', 'thread', 'threadName', 'processName', 'process',
                               'message', 'getMessage']
        extra_attributes = [x for x in all_attributes if x not in standard_attributes and not x.startswith('__')]
        if len(extra_attributes) > 0:
            extra = {x: get_safe_json_value(getattr(record, x), self.MAX_LOG_FIELD_LENGTH) for x in extra_attributes}
            log_data['extra'] = extra

        json_data = json.dumps(log_data)
        record.msg = json_data

        return super().format(record)


def start_logging(log_name: str, level: str):
    """
    Switch on logging, selecting either a JSON log formatter if running in AWS or a simple tabular formatter otherwise.

    This function is intended to be used immediately when an application starts running.

    This function also calls silence_3rd_party_logs() internally.

    Parameters
    ----------
    log_name : str
        The name of the log to be created.
    level : str
        The minimum level of the logs to be captured, one of DEBUG, INFO, WARNING, ERROR or CRITICAL.

    Returns
    -------
    None
    """
    silence_3rd_party_logs()
    if app_env.is_running_in_container():
        logging.basicConfig(level=level)
        logging.getLogger().handlers[0].setFormatter(JSONFormatter(log_name))
    else:
        # format_template = '%(levelname)-10s %(message)s -- in %(filename)s @ line %(lineno)d'
        format_template = '%(filename)-25s @ line %(lineno)-5d  %(levelname)-10s %(message)-150s'
        logging.basicConfig(stream=sys.stdout, level=level, format=format_template)


def silence_3rd_party_logs():
    """
    Silence logging generated by the boto3 and Snowflake python packages.
    """
    # ref: https://github.com/boto/boto3/issues/521
    logging.getLogger('boto3').setLevel(logging.WARNING)
    logging.getLogger('botocore').setLevel(logging.WARNING)
    logging.getLogger('nose').setLevel(logging.WARNING)
    logging.getLogger('s3transfer').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    # mute Snowflake connector logging
    # ref: https://stackoverflow.com/questions/56525319/turning-off-snowflake-db-logging-while-still-keeping-log-level-as-debug
    for name in logging.Logger.manager.loggerDict.keys():
        if 'snowflake' in name:
            logging.getLogger(name).setLevel(logging.WARNING)
            logging.getLogger(name).propagate = False


def format_exception(exc_info):
    """
    Utility function to format an exception info object as string.

    Parameters
    ----------
    exc_info : ExceptionInfo
        The ExceptionInfo object to be formatted.

    Returns
    -------
    str
        The formatted ExceptionInfo object.
    """
    if exc_info is not None:
        exception_type = exc_info[0]
        exception_info = {
            'name': exception_type.__name__,
            'qualname': exception_type.__qualname__,
            'class': str(exception_type),
            'module': exception_type.__module__,
            'msg': str(exc_info[1]),
            'attributes': get_exception_attributes(exc_info[1])
        }
        tb = traceback.format_exception(exception_type, exc_info[1], exc_info[2])
        exception_info['traceback'] = tb
        return exception_info
