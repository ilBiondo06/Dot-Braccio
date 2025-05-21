
import sys
from registration import initialize_and_connect, configure_devices, synchronize_devices, \
                           start_measurement, stop_measurement_and_logging, show_data, reset_and_cleanup

def run(filter_profile, payload_mode, duration, output_rate, show, output_stream=sys.stdout):
    # reindirizza print() al widget
    import builtins
    print_orig = builtins.print
    def print_to_stream(*args, **kwargs):
        print_orig(*args, **kwargs, file=output_stream)
        output_stream.flush()
    builtins.print = print_to_stream

    xdpcHandler = XdpcHandler()
    try:
        if not initialize_and_connect(xdpcHandler):
            return
        configure_devices(xdpcHandler, filter_profile, output_rate)
        if not synchronize_devices(xdpcHandler):
            return
        start_measurement(xdpcHandler, payload_mode)
        if show:
            show_data(xdpcHandler, duration)
        else:
            time.sleep(duration)
        stop_measurement_and_logging(xdpcHandler)
    finally:
        reset_and_cleanup(xdpcHandler)
    builtins.print = print_orig
