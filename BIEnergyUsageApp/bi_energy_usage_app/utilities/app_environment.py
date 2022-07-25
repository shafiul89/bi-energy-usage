import boto3
import logging
import os
from enum import Enum


def is_running_in_container() -> bool:
    """
    Is the code running inside a docker container?

    This function relies on the following line being present in dockerfile:

    ENV RUNNINGINCONTAINER 1

    This approach is based on https://stackoverflow.com/questions/43878953

    Returns
    -------
    bool
        True if the code is running inside a docker container, False otherwise.
    """
    return os.getenv('RUNNINGINCONTAINER') == "1"


def is_running_in_aws() -> bool:
    """
    Is the code running inside an ECS container in AWS?

    This approach is based on
    https://docs.aws.amazon.com/AmazonECS/latest/userguide/task-metadata-endpoint-v4-fargate.html

    Returns
    -------
    bool
        True if the code is running inside an ECS container in AWS, False otherwise.
    """
    metadata_url = os.getenv('ECS_CONTAINER_METADATA_URI_V4')
    return metadata_url is not None and len(metadata_url) > 0


def log_environment():
    """
    Generate logging about the current runtime environment.

    The information logged includes whether the code is running in a container/AWS, the current working directory
    and the current value of all environment variables.  This logging output is intended to help debugging.

    Returns
    -------
    None
        No return value.

    """
    logging.debug('Environment Info:')
    logging.debug(f'Running in container: {is_running_in_container()}')
    running_in_aws = is_running_in_aws()
    logging.debug(f'Running in AWS: {running_in_aws}')
    if running_in_aws:
        # get_caller_identity() does not require credentials
        caller_identity = boto3.client('sts').get_caller_identity()
        logging.debug(f'AWS IAM calling identity retrieved.', {'identity': caller_identity})
    logging.debug(f'Current working directory: {os.getcwd()}')
    log_environment_variables()


def set_working_directory():
    """
    Change the current working directory to the working directory specified in the
    CRUK_WORKING_DIRECTORY environment variable.
    """
    cruk_working_directory = os.getenv('CRUK_WORKING_DIRECTORY', '')
    logging.debug(f'Changing local working directory to {cruk_working_directory}...')
    if len(cruk_working_directory) > 0:
        os.chdir(cruk_working_directory)
    logging.debug(f'Current working directory is now: {os.getcwd()}')


class EnvironmentVariableNames(Enum):
    """
    The set of supported environment variables.
    """
    ENABLED = 1,
    SERVICE_NAME = 2,
    ENVIRONMENT_NAME = 3,
    AWS_ACCESS_KEY_ID = 10,      # for debug use outside of AWS only
    AWS_SECRET_ACCESS_KEY = 11,  # for debug use outside of AWS only
    AWS_SESSION_TOKEN = 12,      # for debug use outside of AWS only
    AWS_S3_BUCKET_NAME = 13,
    DATA_SOURCE_GAS_ROOT_URL = 21,
    DATA_SOURCE_GAS_FILENAMES = 22,
    DATA_SOURCE_ELECTRICITY_ROOT_URL = 23,
    DATA_SOURCE_ELECTRICITY_FILENAMES = 24,
    DELETE_DATA_FILES = 90


def get_env_var_value(env_var: EnvironmentVariableNames) -> str:
    """
    Get the value of an environment variable.

    The environment variables defined in the container/system need to be prefixed with CRUK_ to avoid accidental name
    collisions with existing system environment variables.

    Parameters
    ----------
    env_var : EnvironmentVariableNames
        The environment variable to retrieve the value of.

    Returns
    -------
    str
        The value of the environment variable.
    """
    return os.getenv('CRUK_' + env_var.name, '')


def get_env_var_secret(env_var: EnvironmentVariableNames) -> str:
    """
    Get the value of a sensitive environment variable.

    The secret environment variables defined in the container/system need to be prefixed with CRUK_SECRET_ to both avoid
    accidental name collisions with existing system environment variables and to mark the environment variable as a
    secret - so it is not included in the output of log_environment_variables() and log_environment().

    Parameters
    ----------
    env_var : EnvironmentVariableNames
        The environment variable to retrieve the value of.

    Returns
    -------
    str
        The value of the environment variable.
    """
    return os.getenv('CRUK_SECRET_' + env_var.name, '')


def log_environment_variables():
    """
    Log the current value of all environment variables.

    The output of sensitive environment variables (named CRUK_SECRET_...) are not included in the logging output.

    Returns
    -------
    None
        No return value.
    """
    for name, value in os.environ.items():
        if name.lower().find('secret') >= 0:
            logging.debug(f'ENV: {name} = secret: {len(value)}')
        else:
            logging.debug(f'ENV: {name} = {value}')
