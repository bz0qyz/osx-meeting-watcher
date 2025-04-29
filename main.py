import sys
import signal
import argparse
from config import AppConfig
from ui import StatusBarApp

app_config = AppConfig()

# Parse command line arguments
argparser = argparse.ArgumentParser(description=f"{app_config.name} v{app_config.version}")
argparser.add_argument("-c", "--config", help="config file to use", default=None)
argparser.add_argument("--version", help="show version", action="version",
                       version=f"{app_config.name} v{app_config.version}")
argparser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true")
args = argparser.parse_args()

app_config.get_user_config(args.config, args.verbose)
app = None

# from pprint import pprint
# print("----------------------------------------------------")
# pprint(app_config.__dict__)
# print("----------------------------------------------------")
# pprint(app_config.user_config.__dict__)
# print("----------------------------------------------------")

def signal_handler(sig, frame):
    if args.verbose:
        print("Exiting")
    if app:
        app.quit_application()
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    app = StatusBarApp(app_config=app_config)
    app.run()
