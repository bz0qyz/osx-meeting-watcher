import threading
import psutil
from time import sleep
import paho.mqtt.client as mqtt
class MeetingWatcher:
    def __init__(self, app_config, status_callback, state_callback):
        self.verbose = app_config.verbose
        self.error = None
        self.watch_interval = app_config.user_config.options["watch_interval"]

        # MQTT Config values
        self.mqtt_host = app_config.user_config.mqtt["host"]
        if "publish_topic" in app_config.user_config.mqtt:
            self.mqtt_publish_topic = app_config.user_config.mqtt["publish_topic"]
        else:
            self.mqtt_publish_topic = "meeting/watcher"
        if "port" in app_config.user_config.mqtt:
            self.mqtt_port = app_config.user_config.mqtt["port"]
        else:
            self.mqtt_port = 1883
        if "user" in app_config.user_config.mqtt:
            self.mqtt_user = app_config.user_config.mqtt["user"]
        else:
            self.mqtt_user = None
        if "password" in app_config.user_config.mqtt:
            self.mqtt_password = app_config.user_config.mqtt["password"]
        else:
            self.mqtt_password = None
        if hasattr(app_config.user_config, "proc"):
            self.proc = app_config.user_config.proc
        else:
            self.proc = {}
        if "microphone" in app_config.user_config.watch:
            self.watch_mic = app_config.user_config.watch["microphone"]
        else:
            self.watch_mic = True
        if "proc" in app_config.user_config.watch:
            self.watch_proc = app_config.user_config.watch["proc"]
        else:
            self.watch_proc = False
        self.status_callback = status_callback
        self.state_callback = state_callback

        self.meeting_state = False
        self.connected = False
        self.running = False
        self.manual_on = False

        self.mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.mqttc.username_pw_set(self.mqtt_user, self.mqtt_password)
        try:
            self.mqttc.connect(self.mqtt_host, self.mqtt_port, 10)
            self.mqttc.on_connect = self.on_connect
            self.connected = True
            self.mqttc.on_message = self.on_message
            self.mqttc.subscribe(self.mqtt_publish_topic)
            self.mqttc.loop_start()
        except Exception as e:
            if self.verbose:
                print(f"Error connecting to MQTT: {e}")

        if self.verbose:
            if self.watch_mic:
                print("Watching Microphone")
            if self.watch_proc:
                print("Watching Processes")


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

    def __watch_proc__(self):
        if not self.watch_proc:
            return False
        for proc_name, children in self.proc.items():
            for process in psutil.process_iter():
                if process.name().lower() in proc_name:
                    for child in process.children():
                        if child.name() in children:
                            if self.verbose:
                                print(f"Found {proc_name()}->{child} process running")
                            return True
        return False

    def __watch_mic__(self):
        if not self.watch_mic:
            return False

        import AVFoundation
        import CoreAudio
        import struct
        mic_ids = {
            mic.connectionID(): mic
            for mic in AVFoundation.AVCaptureDevice.devicesWithMediaType_(
                AVFoundation.AVMediaTypeAudio
            )
        }
        opa = CoreAudio.AudioObjectPropertyAddress(
            CoreAudio.kAudioDevicePropertyDeviceIsRunningSomewhere,
            CoreAudio.kAudioObjectPropertyScopeGlobal,
            CoreAudio.kAudioObjectPropertyElementMaster
        )
        for mic_id in mic_ids:
            response = CoreAudio.AudioObjectGetPropertyData(mic_id, opa, 0, [], 4, None)
            # print('Mic', mic_ids[mic_id], 'active:', bool(struct.unpack('I', response[2])[0]))
            if bool(struct.unpack('I', response[2])[0]):
                if self.verbose:
                    print(f"Microphone {mic_ids[mic_id]} is active")
                return True
        return False

    def __run_thread__(self):
        while self.running:
            if self.manual_on:
                sleep(self.watch_interval)
                continue
            if self.verbose:
                print("Meeting Watcher Running")
            self.in_meeting = False
            self.status_callback(True)
            if self.__watch_mic__():
                self.in_meeting = True
            if self.__watch_proc__():
                self.in_meeting = True

            if self.in_meeting and not self.meeting_state:
                if self.verbose:
                    print("Meeting in progress")
                self.publish("1")
            elif not self.in_meeting and self.meeting_state:
                if self.verbose:
                    print("Meeting ended")
                self.publish("0")
            sleep(self.watch_interval)

        self.status_callback(False)
        if self.verbose:
            print("Meeting Watcher stopped")

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self.__run_thread__)
        self.thread.start()

    def stop(self):
        self.running = False

