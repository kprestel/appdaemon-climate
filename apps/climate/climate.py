from asyncio.log import logger
import datetime
from dataclasses import dataclass
from typing import Dict, Iterable, List

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
        try:
            self.thermostat = self.args["thermostat"]
        except KeyError:
            self.log("missing required argument: thermostat")
            raise

        try:
            self.prefs = Preferences.from_args(self.args["preferences"])
        except KeyError:
            self.log("missing required argument: preferences")
            raise

        self.log(f"preferences: {self.prefs}")
        self.time_pref = self.create_pref_time_dict()

        try:
            self._outside_temperature_sensor = self.args["weather_sensor"]
        except KeyError:
            self.log("missing required argument: weather_sensor")
            raise

        self.run_minutely(self.temperature_check, datetime.time(0, 0, 0))
        self.open_close_sensors = self.args.get("open_close_sensors", {})
        self.log(f"open_close_sensors: {self.open_close_sensors}")
        for sensor in self.open_close_sensors:
            self.listen_state(callback=self.open_close_callback, entity_id=sensor)
        self.climate_off_timeout = self.parse_time(self.args.get("climate_off_timeout", "00:30:00"))

    @property
    def outside_temperature(self) -> float:
        return float(self.get_state(self._outside_temperature_sensor))

    @property
    def max_temperature(self) -> int:
        try:
            return int(float(self.get_state(self.args.get("max_temperature"))))
        except Exception as e:
            self.log("Error getting max temp, using default of 80", e)
            return 80

    @property
    def min_temperature(self) -> int:
        try:
            return int(float(self.get_state(self.args.get("min_temperature"))))
        except Exception:
            self.log("Error getting min temp. Using default of 55")
            return 55

    @property
    def thermostat_temperature(self) -> int:
        return int(self.get_state(
            self.thermostat, attribute="current_temperature"
        ))

    @property
    def mode_switching_enabled(self) -> bool:
        try:
            return bool(self.get_state(self.args.get("mode_switching_enabled")))
        except Exception as e:
            self.log("Error getting mode switching option, defaulting to false.", e)
            return False

    @property
    def climate_temperature_difference(self) -> int:
        try:
            return int(float(self.get_state(self.args.get("input_number.climate_temperature_difference", 0))))
        except Exception:
            self.log("Unable to parse input_number.climate_temperature_difference", level="WARNING")
            return 0
   
    @property
    def inside_temperature_sensors(self) -> Dict[str, Dict[str, List[str]]]:
        return self.args.get("inside_temperature_sensors", {})

    def get_temperature_sensors(self) -> Iterable[str]:
        for d in self.inside_temperature_sensors.values():
            for sensor in d.values():
                yield from sensor

    def open_close_callback(self, entity, attribute, old, new, kwargs):
        self.log(f"Running open_close_callback, new: {new}, old: {old}, entity: {entity}")
        if old == new:
            return

        if new == "open" or new == "on":
            self.turn_off_climate()
        elif new == "closed" or new == "off":
            self.turn_on_climate()
        else:
            self.log(f"Unknown state: {new}")

    def turn_off_climate(self, kwargs=None):
        self.log("Turning climate off")
        self.call_service("climate/turn_off", entity_id=self.thermostat)
        self.run_in(self.turn_on_climate, self.open_close_callback)

    def turn_on_climate(self, kwargs=None):
        self.log("Turning climate on")
        self.call_service("climate/turn_on", entity_id=self.thermostat)

    def temperature_check(self, kwargs):
        self.log("Checking temperature")
        pref = self.nearest(self.time_pref.keys(), self.get_now())
        preference = self.time_pref.get(pref)
        self.log(f"using preference: {preference}")
        self._set_temp(preference)

    def _set_temp(self, preference: Preferences):
        temp_to_set = float(self.get_state(preference.input_temperature))
        current_outside_temp = self.outside_temperature
        current_state = self.get_state(self.thermostat)
        thermostat_temp = self.thermostat_temperature
        sensors = self.args.get("inside_temperature_sensors", {})
        current_temps = self.get_current_temperatures(sensors)
        target_area = preference.target_area

        if target_area in current_temps:
            target_area_temp = current_temps[target_area]
            self.log(
                f"Target area: {target_area} actual: {current_temps[target_area]}"
            )
        else:
            self.log("Target area not currently in current temperatures")
            target_area_temp = thermostat_temp

        # temp_to_set = self.get_adjusted_temp(temp_to_set, thermostat_temp, current_temps, target_area)

        if temp_to_set > self.max_temperature:
            self.log(f"temp: {temp_to_set} was too high, using max temperature: {self.max_temperature}")
            temp_to_set = self.max_temperature
        elif temp_to_set < self.min_temperature:
            self.log(f"temp: {temp_to_set} was too low, using min temperature: {self.min_temperature}")
            temp_to_set = self.min_temperature
        else:
            self.log(f"temp_to_set: {temp_to_set} within temperature boundaries")

        self.log(
            f"adj_temp: {temp_to_set}, thermostat_temp: {thermostat_temp}, current_outside_temp: {current_outside_temp}"
        )

        if target_area_temp > current_outside_temp and target_area_temp < temp_to_set:
            mode = "heat"
        else:
            mode = "cool"

        self.log(f"Current mode: {current_state}, desired mode: {mode}")

        if mode == "cool" and self.min_temperature == temp_to_set and self.mode_switching_enabled and current_state == "heat":
            self.log(f"Changing climate mode from {current_state} to {mode}")
            self.call_service(
                "climate/set_hvac_mode", hvac_mode=mode, entity_id=self.thermostat
            )

        if current_state != mode and self.mode_switching_enabled:
            self.log(f"Changing climate mode from {current_state} to {mode}")
            self.call_service(
                "climate/set_hvac_mode", hvac_mode=mode, entity_id=self.thermostat
            )

        self.log(
            f"Current Temp Outside: {current_outside_temp}, current indoor temp: {target_area_temp} setting indoor temp to: {temp_to_set}, using mode: {mode}"
        )
        self.call_service(
            "climate/set_temperature", entity_id=self.thermostat, temperature=temp_to_set
        )

    def get_adjusted_temp(self, temp_to_set, thermostat_temp, current_temps, target_area):
        try:
            adjustment = thermostat_temp - current_temps[target_area]
        except KeyError:
            self.log(
                f"Could not find target area: {target_area} in current temperatures"
            )
            adjustment = 0

        temp_to_set += adjustment

        return temp_to_set

    def get_current_temperatures(self, sensors):
        current_temps = {}
        for k, v in sensors.items():
            temps = []
            for x in v["sensors"]:
                inside_temp = self.get_state(x)
                if not inside_temp:
                    logger.warn(f"{inside_temp} was {inside_temp} which cannot be parsed.")
                    continue

                try:
                    temps.append(float(inside_temp))
                except (ValueError, TypeError):
                    self.log(f"could not parse {inside_temp}")

            if temps:
                current_temps[k] = sum(temps) / len(temps)
                self.log(f"Current temperature: {k} {current_temps[k]}")
        return current_temps

    def nearest(self, items, pivot):
        date_items = [
            datetime.datetime.combine(datetime.date.today(), x, tzinfo=pivot.tzinfo)
            for x in items
        ]
        date_items = [x for x in date_items if x < pivot]
        if not date_items:
            return min(items)
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
