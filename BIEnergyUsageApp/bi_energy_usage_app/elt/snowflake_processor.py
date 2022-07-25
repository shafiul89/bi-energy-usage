import logging

import bi_energy_usage_app.utilities.snowflake_utilities as snowflake_utilities


def load_snowflake():
    """
    Load data from the S3 bucket into Snowflake, logging any errors.

    Returns
    -------
    None
        No return value.
    """
    try:
        logging.info('Starting Snowflake processing...')
        try_snowflake_load()
        logging.info('Finished Snowflake processing.')
    except Exception as e:
        logging.error(f'Error during Snowflake processing.', exc_info=e)


def try_snowflake_load():
    """
    Load data from the S3 bucket into Snowflake.

    Returns
    -------
    None
        No return value.
    """
    logging.debug('Testing connectivity to Snowflake...')
    version = snowflake_utilities.snowflake_read_version()
    logging.debug(f'Connected to Snowflake version {version}.')
    logging.debug('Loading data into Snowflake...')
    snowflake_utilities.snowflake_load_data(stage_name='S3_STAGE', stage_path='/processed/',
                                            file_format_name='BASIC_CSV',
                                            schema_name='BEIS_LOAD', table_name='ENERGY_USAGE')
    logging.debug('Data load completed.')