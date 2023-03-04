import numpy
import matplotlib.pyplot as pyplot

from loaders import Temperature, Energy
from loaders import load_heatload_data


def print_heatload_chart(title, heatload_models):
    fig, axis = pyplot.subplots(1, 1)
    xModel = numpy.linspace(-25, 60)
    heatload_models.plot_data(axis)

    yModel = heatload_models.simulation_model(xModel)
    axis.plot(xModel, yModel, color="grey")

    yModel = heatload_models.hvac_sizing_model(xModel)
    axis.plot(xModel, yModel, color="grey")

    axis.set_title(title)
    axis.set_xlabel("Temperature °F")
    axis.set_ylabel("Heat BTU/h")

    designTemp = -6.5
    designload = yModel = heatload_models.hvac_sizing_model(designTemp)
    print(f"{title}: {int(designload)} BTU/h")

    axis.annotate(f"({designTemp:0.1f}°F, {int(designload)} BTUh)", [designTemp,designload],
                  xytext=(0, 20), textcoords='offset points',
                  arrowprops=dict(arrowstyle="->"))
    
    designTemp = -22
    designload = yModel = heatload_models.hvac_sizing_model(designTemp)
    axis.annotate(f"({designTemp:0.1f}°F, {int(designload)} BTUh)", [designTemp,designload],
                  xytext=(0, 20), textcoords='offset points',
                  arrowprops=dict(arrowstyle="->"))
    
    designTemp = 32
    designload = yModel = heatload_models.hvac_sizing_model(designTemp)
    axis.annotate(f"({designTemp:0.1f}°F, {int(designload)} BTUh)", [designTemp,designload],
                  xytext=(0, 20), textcoords='offset points',
                  arrowprops=dict(arrowstyle="->"))

    title = title.replace(" ", "-")
    fig.savefig(f'heatload-{title}.pdf')


heatload_models = load_heatload_data("./data/heatload-basement.txt", (Energy.BTU, Temperature.CELSIUS))
print_heatload_chart("Basement (excluding garage)", heatload_models)

heatload_models = load_heatload_data("./data/heatload-garage.txt", (Energy.BTU, Temperature.CELSIUS))
print_heatload_chart("Garage", heatload_models)

heatload_models = load_heatload_data("./data/heatload-kitchen-and-living-room.txt", (Energy.BTU, Temperature.CELSIUS))
print_heatload_chart("Kitchen and Living Room", heatload_models)

heatload_models = load_heatload_data("./data/heatload-main-office-and-guest.txt", (Energy.BTU, Temperature.CELSIUS))
print_heatload_chart("Office and Guest Room", heatload_models)

heatload_models = load_heatload_data("./data/heatload-L2-bedroom-and-office.txt", (Energy.BTU, Temperature.CELSIUS))
print_heatload_chart("L2 Bedroom and Office", heatload_models)

heatload_models = load_heatload_data("./data/heatload-Balcony-room.txt", (Energy.BTU, Temperature.CELSIUS))
print_heatload_chart("L2 Balcony Room", heatload_models)

heatload_models = load_heatload_data("./data/heatload-spare-room.txt", (Energy.BTU, Temperature.CELSIUS))
print_heatload_chart("L2 Spare Room", heatload_models)

heatload_models = load_heatload_data("./data/heatload-data.txt", (Energy.BTU, Temperature.CELSIUS))
print_heatload_chart("Total Home Heatload", heatload_models)

heatload_models = load_heatload_data("./data/heatload-mainfloor.txt", (Energy.BTU, Temperature.CELSIUS))
print_heatload_chart("Mainfloor", heatload_models)

heatload_models = load_heatload_data("./data/heatload-upstairs.txt", (Energy.BTU, Temperature.CELSIUS))
print_heatload_chart("Second Floor", heatload_models)