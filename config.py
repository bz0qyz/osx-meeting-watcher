import os
import yaml
import shutil

class AppConfig():
    def __init__(self):
        self.name = "Meeting Watcher"
        self.version = "1.1.0"
        self.description = "Watch for Meetings and toggle a binary MQTT topic"
        self.license = "The Unlicense"
        self.identifier = "com.64byte.osx.meeting_watcher"
        self.icons = {
            "meeting": "meeting.png",
            "watching": "watching.png",
            "manual": "manual.png",
        }
        self.verbose = False
        # Get the path of the application
        self.app_path = os.path.dirname(os.path.realpath(__file__))
        # Set the user config path
        self.user_config_path = f"{os.path.expanduser('~')}/.config/meeting_watcher"
        self.user_config_file = None
        self.user_config = UserConfig()

        self.user_config_files =  [
            f"{self.user_config_path}/config.yaml",
            f"{self.app_path}/config.yaml",
            "config.yaml"
        ]

        # Set the icon path if running from source
        if os.path.isdir(f"{self.app_path}/resources"):
            for icon in self.icons:
                self.icons[icon] = f"{self.app_path}/resources/{self.icons[icon]}"

    def get_user_config(self, user_file=None, verbose=False):
        """ Load the user config file """
        self.verbose = verbose
        # Check if the user config directory exists and create it if it doesn't
        if not os.path.exists(f"{self.user_config_path}"):
            os.makedirs(f"{self.user_config_path}")
            shutil.copyfile("config-default.yaml", f"{self.user_config_path}/config.yaml")

        # If a config file is provided in args, add it to the list
        if user_file:
            self.user_config_files.insert(0, user_file)

        # locate the first config file that exists
        for file in self.user_config_files:
            if os.path.exists(file):
                self.user_config_file = file
                break

        if self.verbose:
            print(f"Using config file: {self.user_config_file}")

        if self.user_config_file:
            self.user_config.load(self.user_config_file)



class UserConfig():
    def __init__(self):
        self.ready = False
        self.error = None
        self.mqtt = {
            "host": "localhost",
            "port": 1883,
            "topic": "meeting/watcher",
            "username": None,
            "password": None
        }
        self.watch = {
            "microphone": True,
            "proc": False
        }
        self.options = {
            "notifications": True,
            "watch_interval": 5
        }
        self.proc = {}

    def load(self, user_config_file):
        try:
            with open(f"{user_config_file}", "r") as config_file:
                config = yaml.safe_load(config_file)
        except FileNotFoundError:
            self.error = f"Config file not found {user_config_file}"
        except yaml.YAMLError as e:
            self.error = f"Error reading config file: {e}"
        except Exception as e:
            self.error = f"Error reading config file: {e}"

        if config:
            if "mqtt" in config:
                self.mqtt = config["mqtt"]
            if "watch" in config:
                self.watch = config["watch"]
            if "proc" in config:
                self.proc = config["proc"]
            if "options" in config:
                self.options = config["options"]
            self.ready = True
