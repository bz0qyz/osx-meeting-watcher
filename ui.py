import rumps
from watch import MeetingWatcher
class StatusBarApp(rumps.App):
    def __init__(self, app_config):
        self.app_name = app_config.name
        self.app_version = app_config.version
        self.icon_manual = app_config.icons["manual"]
        self.icon_watching = app_config.icons["watching"]
        self.icon_meeting = app_config.icons["meeting"]
        self.verbose = app_config.verbose
        self.notifications = app_config.user_config.options["notifications"]
        self.status = True
        self.state = False

        # Initialize the rumps.App
        super(StatusBarApp, self).__init__(self.app_name, icon=self.icon_watching)
        self.menu = ['Start Watching', 'Stop Watching', 'Toggle Light', 'About']
        self.menu['Start Watching'].icon = self.icon_watching
        self.menu['Stop Watching'].icon = self.icon_manual
        self.menu['Toggle Light'].icon = self.icon_meeting

        # self.settings_window = rumps.Window(
        #     title="Settings",
        #     message=f"Configure {self.app_name} ",
        #     ok="Save",
        #     cancel="Cancel",
        #     dimensions=(320, 160)
        # )
        # self.settings_window.icon = self.icon_watching

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
        if self.state and self.notifications:
            rumps.notification(
                title=f"{self.app_name}",
                subtitle=None,
                message="Meeting in Progress"
            )
        elif not self.state and self.notifications:
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
            self.__update_icon__()

    # @rumps.clicked("Settings")
    # def settings(self, _):
    #     self.settings_window.run()

    @rumps.clicked("About")
    def prefs(self, _):
        rumps.alert(f"{self.app_name} v{self.app_version}")
