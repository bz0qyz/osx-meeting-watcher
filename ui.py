import rumps
import sqlite3
from watch import MeetingWatcher
from logger import LogEntry
import time
import threading

class Timer:
    def __init__(self, app):
        self.app = app
        self._start_time = None
        self._elapsed = 0.0
        self.thread = None

    def __update_app__(self):
        while self.running and self.app.meeting_watcher.running:
            self.app.title = self.elapsed_str
            # print("updating timer")
            time.sleep(1)


    def start(self):
        """Start or resume the timer."""
        if self._start_time is None:
            self._start_time = time.monotonic()
            self.thread = threading.Thread(target=self.__update_app__)
            self.thread.start()

    def stop(self, reset=False):
        """Stop/pause the timer and record elapsed time."""
        if self._start_time is not None:
            self._elapsed += time.monotonic() - self._start_time
            self._start_time = None
            self.thread = None
            if reset:
                self.reset()

    def reset(self):
        """Reset the timer to zero (stopped)."""
        self._start_time = None
        self._elapsed = 0.0

    @property
    def elapsed(self):
        """Return the total elapsed time in seconds."""
        if self._start_time is not None:
            return self._elapsed + (time.monotonic() - self._start_time)
        return self._elapsed

    @property
    def running(self):
        return self._start_time is not None

    @property
    def elapsed_str(self):
        """Return elapsed time as HH:MM:SS."""
        total_seconds = int(self.elapsed)
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}"


class StatusBarApp(rumps.App):
    def __init__(self, app_config):
        self.app_name = app_config.name
        self.app_version = app_config.version
        self.icon_manual = app_config.icons["manual"]
        self.icon_watching = app_config.icons["watching"]
        self.icon_meeting = app_config.icons["meeting"]
        self.verbose = app_config.verbose
        self.log_db_file = app_config.log_db_file
        self.log_entries = ""
        self.notifications = app_config.user_config.options["notifications"]
        self.status = True
        self.state = False
        self.meeting_timer = Timer(app=self)

        # Initialize the rumps.App
        super(StatusBarApp, self).__init__(self.app_name, icon=self.icon_watching)
        self.menu = ['Start Watching', 'Stop Watching', 'Toggle Light', 'Meeting Log', 'About']
        self.menu['Start Watching'].icon = self.icon_watching
        self.menu['Stop Watching'].icon = self.icon_manual
        self.menu['Toggle Light'].icon = self.icon_meeting

        # Throw an error if the user config is not ready
        if not app_config.user_config.ready:
            if app_config.verbose:
                print(f"User config not ready. {app_config.user_config.error}")
            rumps.alert(f"User config not ready. Exiting\nDetails:\n{app_config.user_config.error}")
            rumps.quit_application()

        self.meeting_watcher = MeetingWatcher(app_config=app_config,
                                              status_callback=self.status_callback,
                                              state_callback=self.state_callback
                                              )
        if not self.meeting_watcher.connected:
            rumps.alert(f"Error connecting to MQTT host: {self.meeting_watcher.mqtt_host}:{self.meeting_watcher.mqtt_port}")
            rumps.quit_application()

        if self.verbose:
            print("StatusBarApp init")
            rumps.debug_mode(True)

        self.template = False
        self.meeting_watcher.publish("0")
        self.start(True)

    def __get_log_entries__(self):
        log_entries = ""
        conn = sqlite3.connect(self.log_db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT id, start_time, end_time, duration FROM log ORDER BY end_time DESC")
        rows = cursor.fetchall()
        conn.close()
        for row in rows:
            entry = LogEntry(row)
            if entry.start_time is None:
                continue
            log_entries += f"{entry.meeting_date} — {entry.meeting_duration}\n"

        return log_entries

    def __update_icon__(self):
        """ Update the icon based on the status and state """
        if self.state and self.icon != self.icon_meeting:
            self.icon = self.icon_meeting
        elif not self.state:
            if self.status and self.icon != self.icon_watching:
                self.icon = self.icon_watching
            elif not self.status and self.icon != self.icon_manual:
                self.icon = self.icon_manual

    def stop(self, _):
        rumps.quit_application()
        self.meeting_timer.stop(reset=True)
        self.title = None

    def status_callback(self, status):
        self.status = status
        self.__update_icon__()
        if status:
            self.menu['Start Watching'].set_callback(None)
            self.menu['Stop Watching'].set_callback(self.stop)
        else:
            self.menu['Start Watching'].set_callback(self.start)
            self.menu['Stop Watching'].set_callback(None)

    def state_callback(self, state):
        self.state = state
        self.__update_icon__()
        if self.state:
            self.meeting_timer.start()
            if self.notifications:
                rumps.notification(
                    title=f"{self.app_name}",
                    subtitle=None,
                    message="Meeting in Progress"
                )
        elif not self.state:
            self.meeting_timer.stop(reset=True)
            if self.notifications:
                rumps.notification(
                    title=f"{self.app_name}",
                    subtitle=None,
                    message="Meeting Competed"
                )

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
            self.__update_icon__()

    @rumps.clicked("Stop Watching")
    def stop(self, _):
        if self.meeting_watcher.running:
            if self.verbose:
                print("Stopping Meeting Watcher")
            self.meeting_watcher.stop()
            self.meeting_timer.stop()
            self.state = False
            self.__update_icon__()

    @rumps.clicked("Meeting Log")
    def settings(self, _):
        log_window = rumps.Window(
            title="Meeting Log",
            default_text=self.__get_log_entries__(),
            ok="Close",
            cancel=None,
            dimensions=(400, 200)
        )
        log_window.icon = self.icon_watching
        log_window.run()

    @rumps.clicked("About")
    def prefs(self, _):
        rumps.alert(f"{self.app_name} v{self.app_version}")
