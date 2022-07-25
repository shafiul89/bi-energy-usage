import os
import snowflake.connector
import bi_energy_usage_app.utilities.app_environment as app_env
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization


def get_snowflake_private_key():
    """
    Read an RSA private key from a file.

    Returns
    -------
    bytes
        The serialised bytes of the private key.
    """
    path = os.path.dirname(__file__)
    path = os.path.dirname(path)
    path = os.path.join(path, 'snowflake_rsa_key.p8')

    with open(path, "rb") as key:
        p_key = serialization.load_pem_private_key(
            key.read(),
            password=app_env.get_env_var_secret(app_env.EnvironmentVariableNames.SNOWFLAKE_RSA_KEY_PASSPHRASE).encode(),
            backend=default_backend()
        )
    pkb = p_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption())
    return pkb


def snowflake_read_version():
    """
    Connect to Snowflake and read the Snowflake version number - typically used as a basic connection test.

    Returns
    -------
    str
        The Snowflake version number.
    """
    ctx = snowflake.connector.connect(
        user=app_env.get_env_var_value(app_env.EnvironmentVariableNames.SNOWFLAKE_USERNAME),
        private_key=get_snowflake_private_key(),
        account=app_env.get_env_var_value(app_env.EnvironmentVariableNames.SNOWFLAKE_ACCOUNT_NAME),
    )
    cs = ctx.cursor()
    try:
        cs.execute("SELECT current_version()")
        one_row = cs.fetchone()
        result = str(one_row[0])
    finally:
        cs.close()
    ctx.close()
    return result


def snowflake_load_data(stage_name: str, stage_path: str, file_format_name: str,
                        schema_name: str, table_name: str):
    """
    Load data from the external stage into Snowflake.

    Performs a full reload - the target table is truncated prior to loading.

    Returns
    -------
    None
        No return value.
    """
    ctx = snowflake.connector.connect(
        user=app_env.get_env_var_value(app_env.EnvironmentVariableNames.SNOWFLAKE_USERNAME),
        private_key=get_snowflake_private_key(),
        account=app_env.get_env_var_value(app_env.EnvironmentVariableNames.SNOWFLAKE_ACCOUNT_NAME),
        role=app_env.get_env_var_value(app_env.EnvironmentVariableNames.SNOWFLAKE_ROLE_NAME),
        database=app_env.get_env_var_value(app_env.EnvironmentVariableNames.SNOWFLAKE_DB_NAME),
        warehouse=app_env.get_env_var_value(app_env.EnvironmentVariableNames.SNOWFLAKE_WH_NAME),
        schema=schema_name
    )
    cs = ctx.cursor()
    try:
        # truncate
        cs.execute(f"TRUNCATE TABLE {schema_name}.{table_name};")
        # load
        copy_into_sql = f"""
        COPY INTO {schema_name}.{table_name}
        FROM @{schema_name}.{stage_name}{stage_path} 
        FILE_FORMAT = (FORMAT_NAME = '{schema_name}.{file_format_name}');
        """
        cs.execute(copy_into_sql)
    finally:
        cs.close()
    ctx.close()