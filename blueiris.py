"""
Python service library for talking to a BlueIris Server
Modified from magapp/blueiriscmd
"""
import logging
import hashlib
import json
import requests

import aiohttp
import asyncio

from enum import Enum

UNKNOWN_DICT = {'-1': ''}
UNKNOWN_LIST = [{'-1': ''}]
UNKNOWN_HASH = -1
UNKNOWN_STRING = "noname"

_LOGGER = logging.getLogger(__name__)


class Signal(Enum):
    RED = 0
    YELLOW = 2
    GREEN = 1

    @classmethod
    def has_value(cls, value):
        if isinstance(value, str):
            """We were provided a string, let's check it"""
            return value in cls.__members__
        else:
            """Assume we were given an int corresponding to the value assigned in this class"""
            return any(value == item.value for item in cls)


class PTZCommand(Enum):
    PAN_LEFT = 0
    PAN_RIGHT = 1
    TILT_UP = 2
    TILT_DOWN = 3
    CENTER = HOME = 4
    ZOOM_IN = 5
    ZOOM_OUT = 6
    POWER_50 = 8
    POWER_60 = 9
    POWER_OUTDOOR = 10
    BRIGHTNESS_0 = 11
    BRIGHTNESS_1 = 12
    BRIGHTNESS_2 = 13
    BRIGHTNESS_3 = 14
    BRIGHTNESS_4 = 15
    BRIGHTNESS_5 = 16
    BRIGHTNESS_6 = 17
    BRIGHTNESS_7 = 18
    BRIGHTNESS_8 = 19
    BRIGHTNESS_9 = 20
    BRIGHTNESS_10 = 21
    BRIGHTNESS_11 = 22
    BRIGHTNESS_12 = 23
    BRIGHTNESS_13 = 24
    BRIGHTNESS_14 = 25
    BRIGHTNESS_15 = 26
    CONTRAST_0 = 27
    CONTRAST_1 = 28
    CONTRAST_2 = 29
    CONTRAST_3 = 30
    CONTRAST_4 = 31
    CONTRAST_5 = 32
    CONTRAST_6 = 33
    IR_ON = 34
    IR_OFF = 35
    PRESET_1 = 101
    PRESET_2 = 102
    PRESET_3 = 103
    PRESET_4 = 104
    PRESET_5 = 105
    PRESET_6 = 106
    PRESET_7 = 107
    PRESET_8 = 108
    PRESET_9 = 109
    PRESET_10 = 110
    PRESET_11 = 111
    PRESET_12 = 112
    PRESET_13 = 113
    PRESET_14 = 114
    PRESET_15 = 115
    PRESET_16 = 116
    PRESET_17 = 117
    PRESET_18 = 118
    PRESET_19 = 119
    PRESET_20 = 120

    @classmethod
    def has_value(cls, value):
        if isinstance(value, str):
            """We were provided a string, let's check it"""
            return value in cls.__members__
        else:
            """Assume we were given an int corresponding to the value assigned in this class"""
            return any(value == item.value for item in cls)


class CAMConfig(Enum):
    PAUSE_INDEFINITELY = -1
    PAUSE_CANCEL = 0
    PAUSE_ADD_30_SEC = 1
    PAUSE_ADD_1_MIN = 2
    PAUSE_ADD_1_HOUR = 3

    @classmethod
    def has_value(cls, value):
        if isinstance(value, str):
            """We were provided a string, let's check it"""
            return value in cls.__members__
        else:
            """Assume we were given an int corresponding to the value assigned in this class"""
            return any(value == item.value for item in cls)


LOG_SEVERITY = {
    0: "INFO",
    1: "WARNING",
    2: "ERROR"
}


class BlueIris:

    def __init__(self, user, password, protocol, host, port="", debug=False, logger=_LOGGER):
        """Define an abstract blue iris server."""
        if port != "":
            host = "{}:{}".format(host, port)
        self.url = "{}://{}/json".format(protocol, host)
        self.user = user
        self.password = password
        self.blueiris_session = UNKNOWN_HASH
        self.response = UNKNOWN_HASH
        self._status = UNKNOWN_DICT
        self._camlist = UNKNOWN_LIST
        self._camcodes = []
        self._camnames = []
        self._alertlist = UNKNOWN_LIST
        self._cliplist = UNKNOWN_LIST
        self._profiles = UNKNOWN_LIST
        self._log = UNKNOWN_LIST
        self.session = requests.session()

        self.asession = aiohttp.ClientSession()

        self.debug = debug
        self.logger = logger

        session_info = self.login()
        if self.debug:
            self.logger.info("Session info: {}".format(session_info))
        self._name = session_info.get('system name', UNKNOWN_STRING)
        self._profiles = session_info.get('profiles', UNKNOWN_LIST)
        self._am_admin = session_info.get('admin', False)
        self._ptz_allowed = session_info.get('ptz', False)
        self._clips_allowed = session_info.get('clips', False)
        self._schedules = session_info.get('schedules', UNKNOWN_LIST)
        self._version = session_info.get('version', UNKNOWN_STRING)
        self.update_status()

    def generate_response(self):
        """Update self.username, self.password and self.blueiris_session before calling this."""
        self.response = hashlib.md5(
            "{}:{}:{}".format(self.user, self.blueiris_session, self.password).encode('utf-8')).hexdigest()

    def update_status(self):
        """Run the command to refresh our stored status"""
        self._status = self.cmd("status")

    def update_camlist(self):
        """Run the command to refresh our stored status"""
        self._camlist = self.cmd("camlist")
        self._camcodes = []
        self._camnames = []
        for cam in self._camlist:
            self._camcodes.append(cam.get('optionValue'))
            self._camnames.append(cam.get('optionDisplay'))

    def update_cliplist(self):
        """Run the command to refresh our stored status"""
        self._cliplist = self.cmd("cliplist", {"camera": "index"})

    def update_alertlist(self):
        """Run the command to refresh our stored status"""
        self._alertlist = self.cmd("alertlist", {"camera": "index"})

    def update_log(self):
        """Run the command to refresh our stored log value"""
        self._log = self.cmd("log")

    @property
    def name(self):
        """Return the system name"""
        return self._name

    @property
    def version(self):
        """Return the system version"""
        return self._version

    @property
    def log(self):
        """Return the system log"""
        if self._log == UNKNOWN_LIST:
            self.update_log()
        return self._log

    @property
    def profiles(self):
        """Return the list of profiles"""
        return self._profiles

    @property
    def schedules(self):
        """Return the list of profiles"""
        return self._schedules

    @property
    def cameras(self):
        """Request and return the camera list"""
        if self._camlist == UNKNOWN_LIST:
            self.update_camlist()
        return dict(zip(self._camcodes, self._camnames))

    @property
    def all_alerts(self):
        """Request and return the list of alert pictures"""
        if self._alertlist == UNKNOWN_LIST:
            self.update_alertlist()
        return self._alertlist

    @property
    def all_clips(self):
        """Request and return the list of clips"""
        if self._cliplist == UNKNOWN_LIST:
            self.update_cliplist()
        return self._cliplist

    @property
    def status(self):
        """Return the last known status"""
        if self._status == UNKNOWN_DICT:
            self.update_status()
        return self._status

    @property
    def profile(self):
        """Return the active profile"""
        profile_id = int(self.status.get('profile', -1))
        if profile_id == -1:
            return "Undefined"
        return self._profiles[profile_id]

    @property
    def signal(self):
        """Return the active traffic signal"""
        signal_id = int(self.status.get('signal', -1))
        if signal_id == -1:
            return "Error"
        return Signal(signal_id)

    def set_signal(self, signal):
        """Set the active traffic signal value"""
        if not Signal.has_value(signal):
            self.logger.error("Unable to set signal to unknown value {}. (Use one of {})".format(signal,
                                                                                                 Signal.__members__.keys()))
        else:
            if isinstance(signal, str):
                self.cmd("status", {"signal": Signal.__members__.get(signal)})
            else:
                self.cmd("status", {"signal": signal})

    def set_schedule(self, schedule_name):
        """Set the active schedule"""
        if schedule_name not in self._schedules:
            self.logger.error("Bad schedule name '{}'. (Use one of {})".format(schedule_name, self._schedules))
        else:
            self.cmd("status", {"schedule": schedule_name})

    def set_pofile(self, profile_name):
        """Set the active profile"""
        if profile_name not in self._profiles:
            self.logger.error("Bad profile name '{}'. (Use one of {})".format(profile_name, self._profiles))
        else:
            self.cmd("status", {"profile": profile_name})

    def toggle_schedule_hold(self):
        """Toggle the schedule to run/hold"""
        self.cmd("status", {"schedule": -1})

    def ptz(self, camera_code, ptz_action: int):
        """Execute a PTZ command on a camera"""
        if camera_code not in self._camcodes:
            self.logger.error("Bad camera code '{}'. (Use one of {})".format(camera_code, self._camcodes))
        elif not PTZCommand.has_value(ptz_action):
            self.logger.error("Bad PTZ command {}. (Use one of {})".format(ptz_action, PTZCommand.__members__.keys()))
        else:
            if isinstance(ptz_action, str):
                self.cmd("ptz", {"camera": camera_code, "button": PTZCommand.__members__.get(ptz_action), "updown": 0})
            else:
                self.cmd("ptz", {"camera": camera_code, "button": ptz_action, "updown": 0})

    def trigger(self, camera_code):
        """Trigger the motion sensor on a specific camera"""
        if not self._am_admin:
            self.logger.warning("Need to be admin to run this command! Aborting.")
        elif camera_code not in self._camcodes:
            self.logger.error("Bad camera code '{}'. (Use one of {})".format(camera_code, self._camcodes))
        else:
            self.cmd("trigger", {"camera": camera_code})

    def logout(self):
        """Tell the server we're done with our session."""
        self.cmd("logout")

    def login(self):
        """
        Send hashed username/password to validate session
        Returns system name and dictionary of profiles OR nothing
        """
        r = self.session.post(self.url, data=json.dumps({"cmd": "login"}))
        if r.status_code != 200:
            self.logger.info("Bad response ({}) when trying to contact {}, {}".format(r.status_code, self.url, r.text))
        else:
            self.blueiris_session = r.json()["session"]
            self.generate_response()
            r = self.session.post(self.url,
                                  data=json.dumps(
                                      {"cmd": "login", "session": self.blueiris_session, "response": self.response}))
            if r.status_code != 200 or r.json()["result"] != "success":
                self.logger.info("Bad login {} :{}".format(r.status_code, r.text))
            else:
                return r.json()["data"]

    def cmd(self, cmd, params=None):
        """Post a command to the server"""
        if params is None:
            params = dict()
        args = {"session": self.blueiris_session, "response": self.response, "cmd": cmd}
        args.update(params)

        if self.debug:
            self.logger.debug("Sending command {}: {}".format(cmd, params))

        r = self.session.post(self.url, data=json.dumps(args))
        if r.status_code != 200:
            self.logger.error("Unsuccessful response. {}:{}".format(r.status_code, r.text))
            return dict()

        if self.debug:
            self.logger.info(str(r.json()))

        try:
            return r.json()["data"]
        except KeyError:
            """It's possible that there was no data to be returned. In that case respond 'None'"""
            if r.json()["result"] == "success":
                return "None"
            """Respond with 'Error' in the event we get here and had a bad result"""
            return "Error"

    async def command(self, command, params=None):
        """Post a command to the server"""
        if params is None:
            params = dict()
        args = {"session": self.blueiris_session, "response": self.response, "cmd": command}
        args.update(params)

        if self.debug:
            self.logger.debug("Sending async command: {} {}".format(command, params))


        try:
            async with self.post(args) as rjson:
                resp = await rjson["data"]
                return resp
        except KeyError:
            """It's possible that there was no data to be returned. In that case respond 'None'"""
            self.logger.error("Failed request: {} {}".format(command, args))

    async def post(self, data):
        """Async method that posts json to the Blue Iris server"""
        async with self.asession as session:
            async with session.post(self.url, data=json.dumps(data)) as response:
                if self.debug:
                    self.logger.info("async {} command returned {}".format(json["cmd"], response.status))
                return await response.json()

    def selfTest(self):
        if self.debug:
            self.logger.info("Updating all values")
            self.update_alertlist()
            self.update_camlist()
            self.update_cliplist()
            self.update_log()
            self.update_status()
