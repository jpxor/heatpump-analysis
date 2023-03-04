import re
import sys
import itertools

import locale
locale.setlocale(locale.LC_ALL, '')

import numpy as np
import matplotlib.pyplot as plt

# itertools.pairwise only available in python 3.10 and later
def pairwise(iterable):
    a, b = itertools.tee(iterable)
    next(b, None)
    return zip(a, b)


class PerformancePoint:
    def __init__(self, temperature, input_kw, output_btu):
        self.temperature = temperature
        self.input_kw = input_kw
        self.output_btu = output_btu
        self.runtime = 1.0
        self.backup_heat = 0.0

    def COP(self) -> float:
        if self.input_kw > 0:
            return self.output_btu / (3412.0 * self.input_kw)
        else:
            return 1.0

    def interpolate_temperature(t:float, p0, p1):
        t0 = p0.temperature
        t1 = p1.temperature
        if t0 == t1:
            return None
        np0 = np.array([p0.input_kw, p0.output_btu])
        np1 = np.array([p1.input_kw, p1.output_btu])
        res = np0 + (np1 - np0) * ((t - t0) / (t1 - t0))
        return PerformancePoint(t, res[0], res[1])

    def interpolate_load(q:float, p0, p1):
        q0 = p0.output_btu
        q1 = p1.output_btu
        i0 = p0.input_kw
        i1 = p1.input_kw
        i = i0 + (i1 - i0) * ((q - q0) / (q1 - q0))
        return PerformancePoint(p0.temperature, i, q)

    def with_runtime(self, rt):
        self.runtime = rt
        return self

    def with_backup_heat(self, btu):
        self.backup_heat = btu
        return self

    def plot_point(self, axis=None):
        if axis is None:
            axis = plt
        axis.scatter(self.temperature, self.output_btu+self.backup_heat)

    def pretty_print(self):
        print(f'(t: {self.temperature:0.2f} *F, in: {self.input_kw:0.2f} kW,  out: {int(self.output_btu)} BTU, COP:{self.COP():0.2f})')


class PerformanceCurve:
    sort_key = lambda self, p : p.temperature

    def __init__(self, points = None, is_rated_curve = False):
        self.is_rated_curve = is_rated_curve
        self.points = []
        if points:
            self.points = points
            self.points.sort(key = self.sort_key)

    def add_point(self, point:PerformancePoint):
        self.points.append(point)
        self.points.sort(key = self.sort_key)

    def estimate_performance(self, temperature) -> PerformancePoint:
        if len(self.points) == 0:
            return None
        if len(self.points) < 2:
            sys.exit("error: not enough data points on performance curve (less than 2)")

        # the rated performance points don't always follow a curve
        # that can be extrapulated to lower temperatures, it can
        # result is output and/or COP higher than max possible
        # skewing the results
        if self.is_rated_curve:
            if temperature < self.points[0].temperature:
                return None

        # interpolation should always be safe
        for p0, p1 in pairwise(self.points):
            if temperature <= p1.temperature:
                return PerformancePoint.interpolate_temperature(temperature, p0, p1)

        # and we should be able to extrapolate to higher temperatures if needed
        return PerformancePoint.interpolate_temperature(temperature, self.points[-2],self.points[-1])

    def plot_curve(self, axis=None):
        if axis is None:
            axis = plt
        x = [p.temperature for p in self.points]
        y = [p.output_btu for p in self.points]
        axis.plot(x,y)
    
    def pretty_print(self):
        print(f'pcurve with {len(self.points)} points:')
        for p in self.points:
            p.pretty_print()


class PerformanceCurveSet:
    def __init__(self, curves = None):
        # default curves: min/rated/max
        self.curves = [PerformanceCurve(), PerformanceCurve(is_rated_curve=True), PerformanceCurve()]
        if curves:
            self.curves = curves

    def add_curve(self, curve:PerformanceCurve):
        self.curves.append(curve)

    def estimate_performance(self, temperature, load) -> PerformancePoint:
        get_tpoint = lambda curve: curve.estimate_performance(temperature)
        tpoints = [p for p in map(get_tpoint, self.curves) if p is not None]
        tpoints.sort(key=lambda p: p.output_btu)

        if len(tpoints) == 0:
            sys.exit(f'error: not enough data to estimate performance, need at least one data point at temperature {temperature}')

        # low load cycling
        if load <= tpoints[0].output_btu:
            return tpoints[0].with_runtime(load/tpoints[0].output_btu)
        
        # non modulating?
        if len(tpoints) == 1:
            tpoints[0].with_backup_heat(max(0, load-tpoints[0].output_btu))
        
        # load within modulating output
        for p0, p1 in pairwise(tpoints):
            if load <= p1.output_btu:
                return PerformancePoint.interpolate_load(load, p0, p1)

        # high load, backup heating required
        return tpoints[-1].with_backup_heat(load-tpoints[-1].output_btu)

    def estimate_max_output(self, temperature):
        get_tpoint = lambda curve: curve.estimate_performance(temperature)
        return max([p.output_btu for p in map(get_tpoint, self.curves) if p is not None])

    def estimate_min_output(self, temperature):
        get_tpoint = lambda curve: curve.estimate_performance(temperature)
        return min([p.output_btu for p in map(get_tpoint, self.curves) if p is not None])

    def plot_curves(self, axis=None):
        if axis is None:
            axis = plt
        for curve in self.curves:
            curve.plot_curve(axis)

    def pretty_print(self):
        print(f'pcurve set with {len(self.curves)} curves:')
        for c in self.curves:
            c.pretty_print()


class HeatPump:
    def __init__(self, name = "unamed", curve_set=None):
        self.name = name
        self.low_temp_cutoff = None
        self.curves = PerformanceCurveSet()
        if curve_set:
            self.curves = curve_set

    def add_points(self, points):
        if len(points) == 0:
            raise ValueError('no points collected')

        while len(points) > len(self.curves.curves):
            self.curves.add_curve(PerformanceCurve())
        for i in range(len(points)):
            if points[i]:
                self.curves.curves[i].add_point(points[i])

    def estimate_performance(self, temperature, load) -> PerformancePoint:
        if self.low_temp_cutoff and temperature < self.low_temp_cutoff:
            return PerformancePoint(temperature, 0, 0).with_backup_heat(load)
        return self.curves.estimate_performance(temperature, load)

    def plot_curves(self, axis=None):
        if axis is None:
            axis = plt
        # plot NEEP data
        self.curves.plot_curves(axis)
        # plot max extrapolation
        if self.low_temp_cutoff:
            x = [self.low_temp_cutoff, 5]
            y = [self.curves.estimate_max_output(x[0]), self.curves.estimate_max_output(x[1])]
            axis.plot(x,y, color="red")
        # plot min extrapolation
        x = [47, 60]
        y = [self.curves.estimate_min_output(x[0]), self.curves.estimate_min_output(x[1])]
        axis.plot(x,y, color="purple")

    def pretty_print(self):
        print(f'Name: {self.name}')
        print(f'low_temp_cutoff: {self.low_temp_cutoff}')
        self.curves.pretty_print()


def load_heatpump_data(file_path:str):
    heatpumps = []

    # the current heatpump data being loaded
    heatpump = None

    # the set of performance points at min/rated/max
    # for specific temperature
    temperature = None
    outputs = None

    with open(file_path, "r") as file:
        for line in file:

            # comments allowed
            if line.strip().startswith("#"):
                continue

            # this marks the start of data for the next heatpumps
            if line.startswith("name:"):

                if heatpump:
                    heatpumps.append(heatpump)
                    heatpump = None

                name = line.replace("name:", "").strip()
                heatpump = HeatPump(name)
                continue

            # this marks a line with output data for min/rated/max
            # at a specific temperature
            if line.startswith("Heating"):

                if heatpump is None:
                    sys.exit('error: heatpump needs a name. Add: "name: [NAME]" before the NEEP data')

                # the temperature in farenheit immediately follows
                # after white space. Neep data is specified at these
                # temperatures
                as_int = lambda s: int(re.search(r'^-?\d*[\.,]{0,1}\d*', s).group())
                temperature = as_int(line.split()[1])

                # min/rated/max btu outputs are the last three items on the line
                outputs = line.split()[-3:]
                continue

            # this marks a line with power input values for the
            # previously read output loads
            if line.startswith("kW") and outputs is not None:

                # min/rated/max power inputs are the last three items on the line
                inputs = line.split()[-3:]

                # combine with outputs to create perf data points
                points = []
                for btu_str, kw_str in zip(outputs, inputs):
                    try:
                        points.append(PerformancePoint(temperature, locale.atof(kw_str), locale.atof(btu_str)))
                    except:
                        points.append(None)

                # distributes the points to the correct min/rated/max curves
                heatpump.add_points(points)
                outputs = None
                continue

            # this marks a line with powCOPer input values for the
            # previously read output loads. COP is only used if
            # KW input is not present
            if line.startswith("COP") and outputs is not None:

                # COPS are the last three items on the line
                cops = line.split()[-3:]

                # combine with outputs to create perf data points
                points = []
                for btu_str, cop_str in zip(outputs, cops):
                    try:
                        cop = locale.atof(cop_str)
                        btu = locale.atof(btu_str)
                        kw = (btu / 3412.0) / cop
                        points.append(PerformancePoint(temperature, kw, btu))
                    except:
                        points.append(None)

                # distributes the points to the correct min/rated/max curves
                heatpump.add_points(points)
                outputs = None
                continue

            if line.startswith("cutoff:"):
                as_int = lambda s: int(re.search(r'^-?\d*[\.,]{0,1}\d*', s).group())
                heatpump.low_temp_cutoff = as_int(line.replace("cutoff:", "").strip())
                continue

    # and finally append the last heatpump
    if heatpump:
        heatpumps.append(heatpump)

    return heatpumps


def test_load_data() -> int:
    heatpumps = load_heatpump_data("heatpump-data.txt")
    heatpumps[0].plot_curves()
    # heatpumps[1].plot_curves()
    plt.show()
    return 0


def simple_test() -> int:
    print_point = lambda p: print(f'runtime:{p.runtime:.2f},  backup:{p.backup_heat:.2f},  out:{p.output_btu:.2f},  in:{p.input_kw:.2f},  COP:{p.COP():.2f}')

    p0 = PerformancePoint(0,  1,   2*3412)
    p1 = PerformancePoint(10, 2,   4*3412)
    p2 = PerformancePoint(20, 1,   4.5*3412)
    c0 = PerformanceCurve([p0, p1, p2])

    p0 = PerformancePoint(0,  2, 3*3412)
    p1 = PerformancePoint(10, 3, 5*3412)
    p2 = PerformancePoint(20, 3, 6*3412)
    c1 = PerformanceCurve([p0, p1, p2])

    curves = PerformanceCurveSet([c0, c1])
    curves.plot_curves()

    p = curves.estimate_performance(6, 12000)
    print_point(p)
    p.plot_point()

    p = curves.estimate_performance(10, 5*3412)
    print_point(p)
    p.plot_point()

    p = curves.estimate_performance(15, 5*3412)
    print_point(p)
    p.plot_point()

    plt.show()
    return 0


if __name__ == '__main__':
    sys.exit(test_load_data())
