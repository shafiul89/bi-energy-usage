import datetime
import logging
import sys
import bi_energy_usage_app.utilities.app_environment as app_env
import bi_energy_usage_app.utilities.app_logging as app_logging
import bi_energy_usage_app.elt.file_processor as file_processor


def main():
    # start logging
    try:
        service_name = app_env.get_env_var_value(app_env.EnvironmentVariableNames.SERVICE_NAME)
        if len(service_name) == 0:
            service_name = 'Energy-Usage-ELT'
        app_logging.start_logging(service_name, 'DEBUG')
    except Exception as e:
        print('Fatal error initialising logging, execution terminated: ' + str(e))
        # todo - send failure notification
        sys.exit(1)

    # top-level error handler to catch any exception not caught by more specific error handlers within the app code
    try:
        # log environment info
        app_env.log_environment()

        # change local working directory
        app_env.set_working_directory()

        # check process enabled
        if app_env.get_env_var_value(app_env.EnvironmentVariableNames.ENABLED) != 'Y':
            logging.info('AWS Parameter CRUK_ENABLED is not set to Y - exiting.')
            sys.exit(0)

        # process data files:  download, minimal transform and upload into S3
        file_processor.process_files()

    except Exception as e:
        logging.error('Unhandled application error.', exc_info=e)
        # todo - send failure notification


if __name__ == '__main__':
    main()
