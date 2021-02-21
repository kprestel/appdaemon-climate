import datetime
from dataclasses import dataclass
from typing import Dict

import appdaemon.plugins.hass.hassapi as hass


@dataclass
class Preferences:
    input_time: str
    input_temperature: str
    target_area: str

    @classmethod
    def from_args(cls, prefs: Dict[str, Dict[str, str]]) -> Dict[str, "Preferences"]:
        ret = {}
        for k, v in prefs.items():
            ret[k] = cls(**v)
        return ret


class Climate(hass.Hass):
    """Hacs class."""

    def initialize(self):
        self.thermostat = self.args["thermostat"]

        self.prefs = Preferences.from_args(self.args["preferences"])
        self.log(self.prefs)
        self.time_pref = self.create_pref_time_dict()
        self._outside_temperature_sensor = self.args["weather_sensor"]
        self.run_minutely(self.temperature_check, datetime.time(0, 0, 0))

    @property
    def outside_temperature(self) -> float:
        return float(self.get_state(self._outside_temperature_sensor))

    def temperature_check(self, kwargs):
        self.log("Checking temperature")
        pref = self.nearest(self.time_pref.keys(), self.get_now())
        preference = self.time_pref.get(pref)
        self.log(f"using preference: {preference}")
        self._set_temp(preference)

    def _set_temp(self, preference: Preferences):
        temp = self.get_state(preference.input_temperature)
        current_outside_temp = self.outside_temperature
        current_state = self.get_state(self.thermostat)
        thermostat_temp = self.get_state(
            self.thermostat, attribute="current_temperature"
        )
        sensors = self.args.get("inside_temperature_sensors", {})
        current_temps = {}
        for k, v in sensors.items():
            temps = []
            for x in v["sensors"]:
                inside_temp = self.get_state(x)
                try:
                    temps.append(float(inside_temp))
                except ValueError:
                    self.log(f"could not parse {inside_temp}")

            if temps:
                current_temps[k] = sum(temps) / len(temps)
                self.log(f"Current temperature: {k} {current_temps[k]}")

        target_area = preference.target_area

        if target_area in current_temps:
            adj_temp = current_temps[target_area] + sensors.get(target_area).get(
                "adjustment", 0
            )
            self.log(
                f"Target area: {target_area} adjusted temperature: {adj_temp}, actual: {current_temps[target_area]}"
            )
        else:
            adj_temp = thermostat_temp

        self.log(
            f"adj_temp: {adj_temp}, current_indoor_temp: {thermostat_temp}, current_outside_temp: {current_outside_temp}"
        )

        if adj_temp > current_outside_temp:
            mode = "heat"
        else:
            mode = "cool"

        if current_state != mode:
            self.log("Changing climate mode")
            self.call_service(
                "climate/set_hvac_mode", hvac_mode=mode, entity_id=self.thermostat
            )

        self.log(
            f"Current Temp Outside: {current_outside_temp}, current indoor temp: {thermostat_temp} setting indoor temp to: {temp}, using mode: {mode}"
        )
        self.call_service(
            "climate/set_temperature", entity_id=self.thermostat, temperature=temp
        )

    def nearest(self, items, pivot):
        date_items = [
            datetime.datetime.combine(datetime.date.today(), x, tzinfo=pivot.tzinfo)
            for x in items
        ]
        date_items = [x for x in date_items if x < pivot]
        return min(date_items, key=lambda x: abs(x - pivot)).time()

    def create_pref_time_dict(self) -> Dict[datetime.time, Preferences]:
        ret = {}
        for val in self.prefs.values():
            state = self.get_state(val.input_time)
            try:
                ret[self.parse_time(state, aware=True)] = val
            except TypeError:
                self.log(f"Error parsing: {state}")

        return ret
