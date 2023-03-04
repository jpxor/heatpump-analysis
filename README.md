# heatpump-analysis
## using data to size and select a heat pump with highest SCOP

Rough python script, welcoming of any improvements to accuracy/correctness

``` python
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
```
