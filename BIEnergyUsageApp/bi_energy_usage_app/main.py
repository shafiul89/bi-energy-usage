import datetime


def output_current_time():
    dt = datetime.datetime.now()
    s = dt.strftime('%H:%M:%S on %A %d %B %Y')
    print('Hello from the Energy Usage ELT App.')
    print('The current date and time is ' + s + '.')


if __name__ == '__main__':
    output_current_time()
