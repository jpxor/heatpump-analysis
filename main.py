
import numpy
import matplotlib.pyplot as pyplot
from scipy.optimize import curve_fit

import hpcurves
import simulation

from loaders import Energy, Temperature, Duration
from loaders import load_heatload_data, load_location_data


class HeatloadModels:
    def __init__(self, simulation_model, hvac_sizing_model, heatload_data=None, t0=None):
        self.simulation_model = simulation_model
        self.hvac_sizing_model = hvac_sizing_model
        self.heatload_data = heatload_data
        self.t0 = t0
    
    def plot_data(self, axis=None):
        if axis is None:
            axis = pyplot
        temps, btus = zip(*self.heatload_data)
        xData = numpy.array(temps)
        yData = numpy.array(btus)
        axis.scatter(xData, yData, alpha=0.2, c="#3894FF")


# Heat Pump Analysis
def main():

    # Loads location data (average hourly temperature or average daily temperature),
    # Compiles data to determine number of hours spent at each temperature per year
    location_data = load_location_data("./data/location-data.txt", Temperature.CELSIUS, Duration.HOURS)

    # Load heat-load data (BTU or kW) over a set time period at various outdoor temperatures,
    # Builds model to estimate heat-loss per hour in temperature ranges
    heatload_data = load_heatload_data("./data/heatload-data.txt", (Energy.BTU, Temperature.CELSIUS))
    heatload_models = model_heatload_data(heatload_data)

    # Load NEEP data for specific heat-pumps,
    # Compiles data to determine the max/min heat output and COP in temperature ranges,
    heatpumps = hpcurves.load_heatpump_data("./data/heatpump-atw-data.txt")

    # Estimates SCOP and detects possible short-cycling, sorts by highest SCOP
    simulation_results = simulation.run(location_data, heatload_models.simulation_model, heatpumps, volume=16875)

    for result in simulation_results:
        result.print()

    # show top results in a chart
    fig, axis = pyplot.subplots(2, 2, sharey=True, sharex=True)
    xModel = numpy.linspace(-25, 60)

    for i in range(min(4, len(simulation_results))):
        axj = i%2
        axi = int(i/2)
        heatload_models.plot_data(axis[axi][axj])

        res = simulation_results[i]
        res.heatpump.plot_curves(axis[axi][axj])

        yModel = heatload_models.simulation_model(xModel)
        axis[axi][axj].plot(xModel, yModel, color="grey")

        yModel = heatload_models.hvac_sizing_model(xModel)
        axis[axi][axj].plot(xModel, yModel, color="grey")

        axis[axi][axj].set_title(f'{res.heatpump.name} (SCOP={res.SCOP:0.2f})')
        axis[axi][axj].set_xlabel("Temperature °F")
        axis[axi][axj].set_ylabel("Heat BTU/h")

    pyplot.show()
    pyplot.close('all')


# given heat load data (list of (temp,btu) points), runs linear regression / curve fit to
# find a linear model for predicting expected heatloss given outdoor temperature. This can
# used to simulate heat pump performance.
#
# also offsets the heatloss model to find the line that is greater than 98% of data points, this
# represents the max heat output needed, and can be used to size equipment.
def model_heatload_data(heatload_data):
    # x-intercept, where heatload is 0.
    # should be between ~60-68
    # t0 = 60
    linear_func = lambda x,a,t0: a*(t0-x)
    initial_parameters = numpy.array([350.0, 60.0])

    temps, btus = zip(*heatload_data)
    xData = numpy.array(temps)
    yData = numpy.array(btus)
    fittedParameters, _ = curve_fit(linear_func, xData, yData, initial_parameters)

    def calculate_fraction_below_model(x,y, model, params):
        count = 0.0
        for i in range(len(x)):
            if y[i] <= model(x[i], *params):
                count += 1.0
        return count/len(x)

    offset_model = lambda x,a,t,b: linear_func(x,a,t)+b
    offset = 0
    f = calculate_fraction_below_model(xData, yData, offset_model, [*fittedParameters, offset])
    while f < 0.98:
        offset += 350
        f = calculate_fraction_below_model(xData, yData, offset_model, [*fittedParameters, offset])

    return HeatloadModels(
        simulation_model = lambda x: fittedParameters[0]*(fittedParameters[1]-x),
        hvac_sizing_model = lambda x: fittedParameters[0]*(fittedParameters[1]-x) + offset,
        heatload_data=heatload_data,
        t0 = fittedParameters[1]
    )


if __name__ == "__main__":
    main()