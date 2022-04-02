# AppDaemon-Climate

_AppDaemon app for [HACS](https://github.com/custom-components/hacs)._

## What is this?

This is an appdaemon app that controls your theromstat via Homeassisant. This appp has the ability to target specific areas of your house and prioritize them depending on the time of day.

## Installation

Download the `hacs` directory from inside the `apps` directory here to your local `apps` directory, then add the configuration to enable the `hacs` module.

## Features

* Switch between A/C and Heat based on the current indoor temperature vs the current outdoor temperature.

* Prioritize different areas of your house based on time of day

* Allow for adjustments to "actual" temperature to achieve desired temperature

## App configuration

The configuration is broken into 4 parts.

1. AD Configuration
1. Single required application parameters
1. Sensor/target area configuration
1. Temperature preferences

Any "key" in the `inside_temperature_sensors` configuration must map to a target area in `preferences`.

```yaml
climate:
  module: climate
  class: Climate
  thermostat: climate.kitchen
  weather_sensor: sensor.dark_sky_temperature
  mode_switching_enabled: input_boolean.enable_climate_mode_switching
  max_temperature: input_number.max_temperature
  min_temperature: input_number.min_temperature
  climate_temperature_difference: input_number.climate_temperature_difference
  inside_temperature_sensors:
    basement:
      sensors:
          - sensor.basement_bedroom_temperature
          - sensor.game_room_temperature
    main:
      sensors:
          - sensor.kitchen_temperature
          - sensor.living_room_temperature
    top:
      sensors:
          - sensor.masterbed_room_temperature
          - sensor.kids_room_temperature
  open_close_sensors:
    - binary_sensor.front_door
    - binary_sensor.living_room_window
  climate_off_timeout: "00:30:00"
  preferences:
    morning:
      input_time: input_datetime.morning
      input_temperature: input_number.morning_temp
      target_area: top
    daytime:
      input_time: input_datetime.daytime_time
      input_temperature: input_number.daytime_temp
      target_area: main
    evening:
      input_time: input_datetime.evening
      input_temperature: input_number.evening_temp
      target_area: basement
    bedtime:
      input_time: input_datetime.bedtime
      input_temperature: input_number.bedtime_temp
      target_area: top
```

| key | optional | type | default | description |
| --- | --- | --- | --- | --- |
| `module` | False | string | | The module name of the app. |
| `class` | False | string | | The name of the Class. |
| `thermostat` | False | string | | The climate entity to control. |
| `max_temperature` | True | int | 80 | The max temperature that would ever be set. |
| `min_temperature` | True | int | 60 | The min temperature that would ever be set. |
| `mode_switching_enabled` | True | boolean | False | If true, then the app will switch between heat and A/C to acheive the desired temperature  |
| `weather_sensor` | False | string | | A sensor that provides the current outdoor temperature. |
| `inside_temperature_sensors` | False | string | | Sensors that provide temperature data about different areas. |
| `preferences` | False | string | |  Target area configuration |
