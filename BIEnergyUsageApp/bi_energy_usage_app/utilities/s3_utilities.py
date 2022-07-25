import bi_energy_usage_app.utilities.app_environment as app_env
import boto3
import botocore.exceptions


def get_boto3_session():
    """
    Authenticate with AWS to create a new boto3 session.

    If the current code is running inside AWS, then the boto3 session will use the AWS credentials of the running
    AWS service instance, e.g. the task role for docker containers running in ECS.

    If the current code is running outside AWS, then the boto3 session will use credentials from the following
    environment variables:  CRUK_AWS_ACCESS_KEY_ID, CRUK_AWS_SECRET_ACCESS_KEY, CRUK_AWS_SESSION_TOKEN

    Returns
    -------
    boto3.session.Session
        A new boto3 session object that can be used to interact with the AWS S3 service.
    """
    if app_env.is_running_in_aws():
        return boto3.Session()
    else:
        return boto3.Session(
            aws_access_key_id=app_env.get_env_var_value(app_env.EnvironmentVariableNames.AWS_ACCESS_KEY_ID),
            aws_secret_access_key=app_env.get_env_var_value(app_env.EnvironmentVariableNames.AWS_SECRET_ACCESS_KEY),
            aws_session_token=app_env.get_env_var_value(app_env.EnvironmentVariableNames.AWS_SESSION_TOKEN)
        )


def does_s3_file_exist(bucket_name: str, object_key: str) -> bool:
    """
    Does an object with the specified object_key exist in the specified S3 bucket?

    Parameters
    ----------
    bucket_name : str
        The name of the bucket to search.
    object_key :
        The key of the object to search for in the specified bucket.

    Returns
    -------
    bool
        True if an object exists in the specified bucket with the specified object key, False otherwise.
    """
    try:
        session = get_boto3_session()
        s3 = session.client('s3')
        s3.get_object(Bucket=bucket_name, Key=object_key)
        return True
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            return False
        else:
            raise


def upload_file(local_file_path: str, bucket_name: str, object_key: str):
    """
    Upload a local file into an S3 bucket.

    Parameters
    ----------
    local_file_path : str
        The path of the local file to upload.
    bucket_name :
        The name of the S3 bucket to upload the file into.
    object_key :
        The key of the object to be created/overwritten in the S3 bucket.

    Returns
    -------
    None
        No return value.
    """
    session = get_boto3_session()
    s3 = session.client('s3')
    s3.upload_file(Filename=local_file_path, Bucket=bucket_name, Key=object_key)


def download_file(local_file_path: str, bucket_name: str, object_key: str):
    """
    Download a file from an S3 bucket.

    Parameters
    ----------
    local_file_path : str
        The path of the local file to create/overwrite.
    bucket_name :
        The name of the S3 bucket to download the file from.
    object_key :
        The key of the object to be downloaded in the S3 bucket.

    Returns
    -------
    None
        No return value.
    """
    session = get_boto3_session()
    s3 = session.client('s3')
    s3.download_file(Filename=local_file_path, Bucket=bucket_name, Key=object_key)


def upload_str(file_data: str, bucket_name: str, object_key: str):
    """
    Upload a string into an S3 bucket.

    Parameters
    ----------
    file_data : str
        The data to upload.
    bucket_name :
        The name of the S3 bucket to upload the data into.
    object_key :
        The key of the object to be created/overwritten in the S3 bucket.

    Returns
    -------
    None
        No return value.
    """
    session = get_boto3_session()
    s3 = session.client('s3')
    s3.put_object(Body=file_data.encode('utf-8'), Bucket=bucket_name, Key=object_key)
