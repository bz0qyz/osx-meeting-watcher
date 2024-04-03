import yaml
import signal
import sys
import argparse
import psutil
import rumps
import threading
from time import sleep
import paho.mqtt.client as mqtt

APP_CONFIG = {
    "app": {
        "name": "Meeting Watcher",
        "version": "1.0.1",
        "icons": {
            "on": "in_meeting.png",
            "off": "watching.png"
        }
    },
    "mqtt": {
        "host": "",
        "user": "",
        "password": "",
        "publish_topic": ""
    },
    "proc": {
        "zoom.us": ["CptHost", "aomhost"]
    }
}
# Read in the application config file
try:
    with open("config.yaml", "r") as config_file:
        CONFIG = yaml.safe_load(config_file)
        APP_CONFIG.update(CONFIG)
except FileNotFoundError:
    print("Config file not found")
    exit(1)
except yaml.YAMLError as e:
    print(f"Error reading config file: {e}")
    exit(1)
except Exception as e:
    print(f"Error reading config file: {e}")
    exit(1)

argparser = argparse.ArgumentParser(description=f"{APP_CONFIG["app"]["name"]} v{APP_CONFIG["app"]["version"]}")
argparser.add_argument("--version", help="show version", action="version",
                       version=f"{APP_CONFIG["app"]["name"]} v{APP_CONFIG["app"]["version"]}")
argparser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true")
args = argparser.parse_args()


class StatusBarApp(rumps.App):
    def __init__(self, app_config, verbose=False):
        self.app_name = app_config["app"]["name"]
        self.app_version = app_config["app"]["version"]
        self.icon_on = app_config["app"]["icons"]["on"]
        self.icon_off = app_config["app"]["icons"]["off"]
        self.verbose = verbose
        super(StatusBarApp, self).__init__(self.app_name, icon=self.icon_on)
        self.menu = ['Start Watching', 'Stop Watching', 'Toggle Light', 'About']

        self.meeting_watcher = MeetingWatcher(app_config=app_config,
                                              status_callback=self.status_callback,
                                              state_callback=self.state_callback,
                                              verbose=verbose)

        if self.verbose:
            print("StatusBarApp init")
            rumps.debug_mode(True)

        self.template = False
        self.meeting_watcher.publish("0")
        self.start(True)

    def status_callback(self, status):
        if status:
            self.menu['Start Watching'].set_callback(None)
            self.menu['Stop Watching'].set_callback(self.stop)
        else:
            self.menu['Start Watching'].set_callback(self.start)
            self.menu['Stop Watching'].set_callback(None)
    def state_callback(self, state):
        if state:
            self.icon = self.icon_on
            rumps.notification(title=f"{self.app_name}", subtitle=None, message="Meeting in Progress")
        else:
            self.icon = self.icon_off
            rumps.notification(title=f"{self.app_name}", subtitle=None, message="Meeting Competed")

    @rumps.clicked("Toggle Light")
    def toggle_light(self, _):
        if self.meeting_watcher.manual_on:
            self.meeting_watcher.publish("0")
            self.meeting_watcher.manual_on = False
        else:
            self.meeting_watcher.publish("1")
            self.meeting_watcher.manual_on = True
    @rumps.clicked("Start Watching")
    def start(self, _):
        if not self.meeting_watcher.running:
            if self.verbose:
                print("Starting Meeting Watcher")
            self.meeting_watcher.start()

    @rumps.clicked("Stop Watching")
    def stop(self, _):
        if self.meeting_watcher.running:
            if self.verbose:
                print("Stopping Meeting Watcher")
            self.meeting_watcher.stop()

    @rumps.clicked("About")
    def prefs(self, _):
        rumps.alert(f"{self.app_name} v{self.app_version}")

class MeetingWatcher:
    def __init__(self, app_config, status_callback, state_callback, verbose=False):
        self.mqtt_host = app_config["mqtt"]["host"]
        self.mqtt_user = app_config["mqtt"]["user"]
        self.mqtt_password = app_config["mqtt"]["password"]
        self.mqtt_publish_topic = app_config["mqtt"]["publish_topic"]
        self.proc = app_config["proc"]
        self.status_callback = status_callback
        self.state_callback = state_callback
        self.verbose = verbose
        self.meeting_state = False
        self.running = False
        self.manual_on = False

        self.mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.mqttc.username_pw_set(self.mqtt_user, self.mqtt_password)
        self.mqttc.connect(self.mqtt_host)
        self.mqttc.on_connect = self.on_connect
        self.mqttc.on_message = self.on_message
        self.mqttc.subscribe(self.mqtt_publish_topic)
        self.mqttc.loop_start()

    def __payload_to_bool__(self, payload):
        if str(payload) in ["1", "true", "True"]:
            return True
        else:
            return False

    def on_connect(self, client, userdata, flags, reason_code, properties):
        if self.verbose:
            print(f"MQTT Connected with result code: {reason_code}")
        self.mqttc.subscribe(self.mqtt_publish_topic)

    def on_message(self, client, userdata, msg):
        if self.verbose:
            print(f"MQTT Message received: {msg.payload.decode()}")
        self.meeting_state = self.__payload_to_bool__(msg.payload.decode())
        self.state_callback(self.meeting_state)

    def publish(self, message):
        self.mqttc.publish(self.mqtt_publish_topic, message)

    def __run_thread__(self):
        while self.running:
            if self.manual_on:
                sleep(5)
                continue
            if self.verbose:
                print("Meeting Watcher Running")
            self.in_meeting = False
            self.status_callback(True)
            for proc_name, children in self.proc.items():
                for process in psutil.process_iter():
                    if process.name().lower() in proc_name:
                        for child in process.children():
                            if child.name() in children:
                                self.in_meeting = True
                                break
                    if self.in_meeting:
                        break

            if self.in_meeting and not self.meeting_state:
                if self.verbose:
                    print("Meeting in progress")
                self.publish("1")
            elif not self.in_meeting and self.meeting_state:
                if self.verbose:
                    print("Meeting ended")
                self.publish("0")
            sleep(5)

        self.status_callback(False)
        if self.verbose:
            print("Meeting Watcher stopped")

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self.__run_thread__)
        self.thread.start()

    def stop(self):
        self.running = False
def signal_handler(sig, frame):
    if args.verbose:
        print("Exiting")
    rumps.quit_application()
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    app = StatusBarApp(app_config=APP_CONFIG, verbose=args.verbose)
    app.run()


