import datetime
import logging
import sys
import bi_energy_usage_app.utilities.app_environment as app_env
import bi_energy_usage_app.utilities.app_logging as app_logging


def output_current_time():
    dt = datetime.datetime.now()
    sdt = dt.strftime('%H:%M:%S on %A %d %B %Y')
    logging.info('Hello from the Energy Usage ELT App.')
    logging.info('The current date and time is %s.', sdt, extra={'timezone': str(dt.astimezone().tzinfo)})


def main():
    # start logging
    try:
        service_name = app_env.get_env_var_value(app_env.EnvironmentVariableNames.SERVICE_NAME)
        if len(service_name) == 0:
            service_name = 'bi-energy-usage'
        app_logging.start_logging(service_name, 'DEBUG')
    except Exception as e:
        print('Fatal error initialising logging, execution terminated: ' + str(e))
        # todo - send failure notification
        sys.exit(1)

    # top-level error handler to catch any exception not caught by more specific error handlers within the app code
    try:
        # log environment info
        app_env.log_environment()

        # check process enabled
        if app_env.get_env_var_value(app_env.EnvironmentVariableNames.ENABLED) != 'Y':
            logging.info('AWS Parameter CRUK_ENABLED is not set to Y - exiting.')
            sys.exit(0)

        # same placeholder code for now
        output_current_time()

        # test error
        # raise ValueError('The value is bad.')

    except Exception as e:
        logging.error('Unhandled application error.', exc_info=e)
        # todo - send failure notification


if __name__ == '__main__':
    main()