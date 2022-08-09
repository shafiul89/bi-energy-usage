import bi_energy_usage_app.utilities.app_environment as app_env
import bi_energy_usage_app.utilities.app_logging as app_logging
import boto3
import logging
import bi_energy_usage_app.utilities.safe_json as safe_json
from datetime import datetime


def publish_success_notification(details: str = ''):
    """
    Send a SUCCESS notification message to an SNS topic.

    Parameters
    ----------
    details : str
        The text that will become the body of the notification.

    Returns
    -------
    None
        No return value
    """
    if not app_env.is_running_in_aws():
        return
    subject_line = app_env.get_env_var_value(app_env.EnvironmentVariableNames.ENVIRONMENT_NAME).title()
    subject_line += " SUCCESS"
    dt = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')
    body = f"Process succeeded at {dt} UTC.\r\n"
    if details is not None and len(details) > 0:
        body += f"Details:\r\n{details}.\r\n"

    logging.debug("Sending SNS notification...")
    try:
        client = boto3.client('sns')
        response = client.publish(
            TopicArn=app_env.get_env_var_value(app_env.EnvironmentVariableNames.AWS_SNS_TOPIC_ARN),
            Message=body,
            Subject=subject_line
        )
        logging.debug("SNS notification sent.")
    except Exception as e:
        logging.warning("Error sending notification.", exc_info=e)


def publish_failure_notification(details: str, exc_info):
    """
    Send a FAILED notification message to an SNS topic, optionally including error information

    Parameters
    ----------
    details : str
        The text that become the body of the notification.
    exc_info: Exception/ExceptionInfo
        Error information to be formatted and included in the notification message.

    Returns
    -------
    None
        No return value
    """
    if not app_env.is_running_in_aws():
        return
    subject_line = app_env.get_env_var_value(app_env.EnvironmentVariableNames.ENVIRONMENT_NAME).title()
    subject_line += " FAILED"
    dt = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')
    body = f"Process failed at {dt} UTC.\r\n"
    if details is not None and len(details) > 0:
        body += f"Details:\r\n{details}.\r\n"
    if exc_info is not None:
        body += "Error:\r\n" + safe_json.get_safe_json(app_logging.format_exception(exc_info), 131072)

    logging.debug("Sending SNS notification...")
    try:
        client = boto3.client('sns')
        response = client.publish(
            TopicArn=app_env.get_env_var_value(app_env.EnvironmentVariableNames.AWS_SNS_TOPIC_ARN),
            Message=body,
            Subject=subject_line
        )
        logging.debug("SNS notification sent.")
    except Exception as e:
        logging.warning("Error sending notification.", exc_info=e)
