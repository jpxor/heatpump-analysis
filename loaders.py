import re
import sys
from enum import Enum

class Temperature(Enum):
    CELSIUS = 1
    FAHRENHEIT  = 2
    HDD60 = 3 # heating-degree-days with 60F base temperature
    HDD65 = 4 # heating-degree-days with 65F base temperature

    @classmethod
    def to_celsius(cls, f):
        return (f - 32.0) * (5.0/9.0)

    @classmethod
    def to_fahrenheit(cls, c):
        return c * (9.0/5.0) + 32.0

class Duration(Enum):
    HOURS = 1
    DAYS = 2

    @classmethod
    def to_hours(cls, d):
        return d * 24.0

class Energy(Enum):
    WH = 0
    KWH = 1
    BTU = 2
    KBTU = 3

    @classmethod
    def to_hours(cls, d):
        return d * 24.0

# heatload data is expected to be line-separated pairs of floats. units are specified as
# a Tuple containing an Energy enum and Temperature enum matching the order of the data
def load_heatload_data(file_path:str, data_spec:tuple):
    data_points = []

    get_energy = None
    if isinstance(data_spec[0], Energy):
        get_energy = lambda t: t[0]
    if isinstance(data_spec[1], Energy):
        get_energy = lambda t: t[1]

    get_temperaure = None
    if isinstance(data_spec[0], Temperature):
        get_temperaure = lambda t: t[0]
    if isinstance(data_spec[1], Temperature):
        get_temperaure = lambda t: t[1]

    if not get_energy or not get_temperaure:
        print(data_spec)
        sys.exit("heatload data incorrectly specified: need energy and temperature")

    convertEnergy = lambda btu: btu
    if get_energy(data_spec) == Energy.WH:
        convertEnergy = lambda wh: wh / 3.412
    if get_energy(data_spec) == Energy.KWH:
        convertEnergy = lambda wh: wh / 3412.0
    if get_energy(data_spec) == Energy.KBTU:
        convertEnergy = lambda kbtu: kbtu * 1000.0

    convertTemperature = lambda f: f
    if get_temperaure(data_spec) == Temperature.CELSIUS:
        convertTemperature = lambda c: Temperature.to_fahrenheit(c)
    if get_temperaure(data_spec) == Temperature.HDD60:
        convertTemperature = lambda hdd60: 60-hdd60
    if get_temperaure(data_spec) == Temperature.HDD65:
        convertTemperature = lambda hdd65: 65-hdd65

    # splits lines on whitespace and commas
    line_splitter = re.compile(r'\s|,')

    with open(file_path, "r") as file:
        for line in file:
            datum_str = line_splitter.split(line.strip())
            if len(datum_str) != 2:
                print(datum_str)
                sys.exit("unexpected data point: need energy and temperature per line")

            datum = ( float(datum_str[0]), float(datum_str[1]) )
            temperature = convertTemperature(get_temperaure(datum))
            # heatload_mapping[temperature] = convertEnergy(get_energy(datum))
            data_points.append((temperature, convertEnergy(get_energy(datum))))

    return data_points


# location data is expected to be a series of floats separated by line or space or comma
def load_location_data(file_path:str, unit:Temperature, duration:Duration):
    temperatures = init_temperature_mapping()

    # convert all temperatures to fahrenheit
    converter = lambda f: f
    if unit == Temperature.CELSIUS:
        converter = lambda c : Temperature.to_fahrenheit(c)
    if unit == Temperature.HDD60:
        converter = lambda hdd60: 60-hdd60
    if unit == Temperature.HDD65:
        converter = lambda hdd65: 65-hdd65

    # normalize count to number of hours
    counter = lambda h: h
    if duration == Duration.DAYS:
        counter = lambda d: Duration.to_hours(d)

    # splits lines on whitespace and commas
    line_splitter = re.compile(r'\s|,')

    with open(file_path, "r") as file:
        for line in file:
            for temp_str in line_splitter.split(line):
                if temp_str:
                    temp = converter(float(temp_str.strip()))
                    bucket = int(temp + 0.5)
                    if bucket in temperatures:
                        temperatures[bucket] += counter(1)

    return temperatures


def init_temperature_mapping():
    temperatures_map = {}
    for t in range(-40,120):
        temperatures_map[t] = 0
    return temperatures_map

