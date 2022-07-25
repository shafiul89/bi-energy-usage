import csv
import gzip
import logging
import os

import bi_energy_usage_app.utilities.app_environment as app_env
import bi_energy_usage_app.utilities.file_downloader as file_downloader
import bi_energy_usage_app.utilities.s3_utilities as s3_utilities


def process_files():
    """
    Download raw data files, create a processed set of files and upload files into the S3 bucket.

    Returns
    -------
    None
        No return value.
    """

    # check gas configuration

    gas_root_url = app_env.get_env_var_value(app_env.EnvironmentVariableNames.DATA_SOURCE_GAS_ROOT_URL)
    gas_filenames = app_env.get_env_var_value(app_env.EnvironmentVariableNames.DATA_SOURCE_GAS_FILENAMES)
    if len(gas_root_url) == 0:
        raise ValueError('The DATA_SOURCE_GAS_ROOT_URL environment variable must be specified.')
    if len(gas_filenames) == 0:
        raise ValueError('The DATA_SOURCE_GAS_FILENAMES environment variable must be specified.')
    gas_filenames = gas_filenames.split('|')

    # check electricity configuration

    electricity_root_url = app_env.get_env_var_value(app_env.EnvironmentVariableNames.DATA_SOURCE_ELECTRICITY_ROOT_URL)
    electricity_filenames = app_env.get_env_var_value(
        app_env.EnvironmentVariableNames.DATA_SOURCE_ELECTRICITY_FILENAMES)
    if len(electricity_root_url) == 0:
        raise ValueError('The DATA_SOURCE_ELECTRICITY_ROOT_URL environment variable must be specified.')
    if len(electricity_filenames) == 0:
        raise ValueError('The DATA_SOURCE_ELECTRICITY_FILENAMES environment variable must be specified.')
    electricity_filenames = electricity_filenames.split('|')

    # ensure working directories exist

    working_directory = os.path.join(os.getcwd(), 'data')
    raw_files_directory = os.path.join(working_directory, 'raw')
    processed_files_directory = os.path.join(working_directory, 'processed')
    for directory_path in [working_directory, raw_files_directory, processed_files_directory]:
        if not os.path.exists(directory_path):
            os.mkdir(directory_path)

    # process gas files
    for gas_filename in gas_filenames:
        process_file(working_directory, 'gas', gas_root_url, gas_filename)

    # process electricity files
    for electricity_filename in electricity_filenames:
        process_file(working_directory, 'electricity', electricity_root_url, electricity_filename)


def process_file(working_directory: str, energy_type: str, root_url: str, filename: str):
    """
    Download a single gas/electricity raw data file, create a processed data file and upload files into the S3 bucket.

    Parameters
    ----------
    working_directory : str
        The directory where files should be created whilst they are being worked on.
    energy_type : str
        Expected values:  gas or electricity
    root_url : str
        The URL of website or website directory where the raw data files can be downloaded from,
        e.g. http://cbailiss.me.uk/energy
    filename : str
        The name of the raw data file to be processed, e.g. Gas2020.csv.gz

    Returns
    -------
    None
        No return value.
    """

    # construct full URL
    file_url = root_url
    if file_url[-1] != '/':
        file_url += '/'
    file_url += filename

    # file paths
    raw_file_path = os.path.join(working_directory, 'raw', filename)
    processed_file_path = os.path.join(working_directory, 'processed', filename)

    # extract year from filename
    x = filename.lower().replace('.gz', '')
    x = os.path.splitext(x)[0]
    x = x.replace('gas', '').replace('electricity', '')
    year = int(x)

    # log entry
    extra = {'x_raw_filename': filename, 'x_file_url': file_url, 'x_year': year,
             'x_raw_file_path': raw_file_path, 'x_processed_file_path': processed_file_path}
    logging.info(f'Processing file {file_url}...', extra=extra)

    # try to process the file
    try:
        try_download_file(file_url, raw_file_path, extra_log_info=extra)
        try_process_file(energy_type, year, raw_file_path, processed_file_path, extra)
        try_upload_file(raw_file_path, 'raw/' + os.path.basename(raw_file_path))
        try_upload_file(processed_file_path, 'processed/' + os.path.basename(processed_file_path))
    except Exception as e:
        logging.error(f'Error processing file {file_url}.', exc_info=e, extra=extra)

    # cleanup enabled
    cleanup_enabled = app_env.get_env_var_value(app_env.EnvironmentVariableNames.DELETE_DATA_FILES)
    cleanup_enabled = cleanup_enabled.upper() == 'Y'

    # cleanup
    if cleanup_enabled:
        try_cleanup_file(raw_file_path)
        try_cleanup_file(processed_file_path)

    # log entry
    logging.info(f'Processed file {file_url}.', extra=extra)


def try_download_file(file_url: str, raw_file_path: str, extra_log_info: dict):
    """
    Download a single raw data file.

    Parameters
    ----------
    file_url : str
        The full absolute URL of the raw data file to be downloaded.
    raw_file_path : str
        The full local path where the downloaded raw data file is to be saved.
    extra_log_info : dict
        Additional information to include in logging.

    Returns
    -------
    None
        No return value
    """
    logging.debug(f'Downloading file {file_url} to {raw_file_path}...', extra=extra_log_info)
    file_downloader.download_file(url=file_url, local_file_path=raw_file_path)
    file_size = os.path.getsize(raw_file_path)
    extra_log_info['x_raw_file_size'] = file_size
    logging.debug(f'File downloaded, file size = {file_size} bytes.', extra=extra_log_info)


def try_process_file(energy_type: str, year: int, raw_file_path: str, processed_file_path: str, extra_log_info: dict):
    """
    Create an enriched data file from the specified raw data file.

    Two new columns are added to the data:  EnergyType and Year.

    The column names in the file are also made more consistent/cleaner.

    Parameters
    ----------
    energy_type : str
         Expected values:  gas or electricity
    year : int
        The year the data relates to, e.g. 2019
    raw_file_path : str
        The file path of the raw data file to be processed.
    processed_file_path :
        The file path of the processed data file to be created.
    extra_log_info :
        Additional information to include in logging.
    Returns
    -------
    None
        No return value.
    """
    # input_field_names = ['POSTCODE', 'Number of meters',
    #                      'Consumption (kWh)', 'Mean consumption (kWh)', 'Median consumption (kWh)']
    output_field_names = ['EnergyType', 'Year', 'PostCode', 'MeterCount',
                          'TotalConsumption', 'MeanConsumption', 'MedianConsumption']

    logging.debug(f'Processing file {raw_file_path} to {processed_file_path}...', extra=extra_log_info)

    row_count = 0
    with gzip.open(raw_file_path, mode='rt', encoding='ascii') as fp_raw:
        reader = csv.DictReader(fp_raw)
        with gzip.open(processed_file_path, mode='wt', encoding='UTF8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=output_field_names)
            writer.writeheader()
            for row in reader:
                transformed_row_dict = {
                    'EnergyType': energy_type,
                    'Year': year,
                    'PostCode': row['POSTCODE'],
                    'MeterCount': row['Number of meters'],
                    'TotalConsumption': row['Consumption (kWh)'],
                    'MeanConsumption': row['Mean consumption (kWh)'],
                    'MedianConsumption': row['Median consumption (kWh)']
                }
                writer.writerow(transformed_row_dict)
                row_count += 1

    file_size = os.path.getsize(processed_file_path)
    extra_log_info['x_processed_file_size'] = processed_file_path
    extra_log_info['x_processed_file_rows'] = row_count
    logging.debug(f'File processed, file size = {file_size} bytes, row count = {row_count}.', extra=extra_log_info)


def try_upload_file(local_file_path: str, s3_object_key):
    """
    Upload a file into S3.

    Parameters
    ----------
    local_file_path : str
        The path of the file to upload into S3.
    s3_object_key :
        The key of the object to be created/overwritten in S3.

    Returns
    -------
    None
        No return value.
    """
    logging.debug(f'Uploading file {local_file_path} to S3 at {s3_object_key}.')
    s3_bucket_name = app_env.get_env_var_value(app_env.EnvironmentVariableNames.AWS_S3_BUCKET_NAME)
    s3_utilities.upload_file(local_file_path, s3_bucket_name, s3_object_key)
    logging.debug(f'Uploaded file {local_file_path} to S3 at {s3_object_key}.')


def try_cleanup_file(file_path):
    """
    Attempt to clean-up (i.e. delete) the specified file.

    Parameters
    ----------
    file_path : str
        The path of the file that is to be deleted.

    Returns
    -------
    None
        No return value.
    """
    try:
        logging.debug(f'Deleting file {file_path}...')
        if os.path.exists(file_path):
            os.remove(file_path)
        logging.debug(f'Deleted file {file_path}.')
    except Exception as e:
        logging.warning(f'Error deleting file {file_path}.', exc_info=e)
