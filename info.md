## App configuration

```yaml
climate:
  module: climatge
  class: Climate
  thermostat: climate.kitchen
  weather_sensor: sensor.dark_sky_temperature
  mode_switching_enabled: true
  inside_temperature_sensors:
    basement:
      sensors:
          - sensor.basement_bedroom_temperature
          - sensor.game_room_temperature
      adjustment: -5
    main:
      sensors:
          - sensor.kitchen_temperature
          - sensor.living_room_temperature
      adjustment: 3
    top:
      sensors:
          - sensor.masterbed_room_temperature
          - sensor.kids_room_temperature
  preferences:
    morning:
      time: input_datetime.morning
      temperature: input_number.morning_temp
      target_area: top
    daytime:
      time: input_datetime.daytime_time
      temperature: input_number.daytime_temp
      target_area: main
    evening:
      time: input_datetime.evening
      temperature: input_number.evening_temp
      target_area: basement
    bedtime:
      time: input_datetime.bedtime
      temperature: input_number.bedtime_temp
      target_area: top
```

| key | optional | type | default | description |
| --- | --- | --- | --- | --- |
| `module` | False | string | | The module name of the app. |
| `class` | False | string | | The name of the Class. |
| `thermostat` | False | string | | The climate entity to control. |
| `mode_switching_enabled` | True | boolean | False | If true, then the app will switch between heat and A/C to acheive the desired temperature  |
| `weather_sensor` | False | string | | A sensor that provides the current outdoor temperature. |
| `inside_temperature_sensors` | False | string | | Sensors that provide temperature data about different areas. |
| `preferences` | False | string | |  Target area configuration |

