
BTU_TO_KWH = lambda btu: btu/3412.0
BTU_PER_CUFT_F = 0.235 # number of BTU to heat 1 cuft of air by 1 degree F
ENERGY_COST_PER_KWH = 0.13

class SimResults:
    def __init__(self, heatpump):
        self.heatpump = heatpump
        self.name = heatpump.name
        self.low_temp_cutoff = heatpump.low_temp_cutoff
        self.tot_sim_hours = 0
        self.tot_heating_hours = 0
        self.tot_hp_hours = 0
        self.tot_input_kwh = 0
        self.tot_output_btu = 0
        self.tot_backup_heat_btu = 0
        self.SCOP = 0
        self.HSPF = 0
        self.low_COP = 10
        self.high_COP = 0
        self.cycling_hours = 0
        self.cycling_under_50_50_hours = 0
        self.short_cycling_hours = 0

    def print(self):
        tot_output_kwh = BTU_TO_KWH(self.tot_output_btu)
        print("------------------------------")
        print(f"name: {self.name}")
        if self.low_temp_cutoff:
            print(f"Low Temperature Cutoff: {self.low_temp_cutoff}*F")
        print(f"SCOP: {self.SCOP:0.2f}")
        print(f"HSPF: {self.HSPF:0.2f}")
        print(f"COP Range: {self.low_COP:0.2f}-{self.high_COP:0.2f}")
        print(f"Energy Cost: ${ENERGY_COST_PER_KWH * self.tot_input_kwh:0.2f}")
        print(f" > Savings: ${ENERGY_COST_PER_KWH * (tot_output_kwh-self.tot_input_kwh):0.2f}")
        print(f"Total input: {self.tot_input_kwh:0.2f} kWh")
        print(f"Total output: {tot_output_kwh:0.2f} kWh")
        print(f"Fraction backup heat: {100*self.tot_backup_heat_btu/self.tot_output_btu:0.3f}%")
        print(f"Fraction cycling: {100*self.cycling_hours/self.tot_hp_hours:0.2f}%")
        print(f"Fraction under 50/50 cycle: {100*self.cycling_under_50_50_hours/self.tot_hp_hours:0.2f}%")
        print(f"Fraction short-cycling: {100*self.short_cycling_hours/self.tot_hp_hours:0.2f}%")
        
def run(location_data, heatload_model, heatpumps, volume=None):
    results = []
    for heatpump in heatpumps:
        res = SimResults(heatpump)

        # iterate over range of outdoor temperatures, getting number of
        # hours and required BTUs for each
        for temperature,hours in location_data.items():

            btuh = heatload_model(temperature)
            res.tot_sim_hours += hours

            # consider heating only 
            if btuh <= 0:
                continue

            res.tot_heating_hours += hours

            # estimate performance stats at temp+load
            perf = heatpump.estimate_performance(temperature, btuh)
            cop = perf.COP()

            # let aux heating take over if heatpump COP < 1
            if cop < 1:
                perf.input_kw = 0
                perf.output_btu = 0
                perf.backup_heat = btuh
                cop = 1

            res.low_COP = min(res.low_COP, cop)
            res.high_COP = max(res.high_COP, cop)

            if perf.output_btu > 0:
                res.tot_hp_hours += hours

            res.tot_input_kwh += (hours * perf.runtime) * (perf.input_kw + BTU_TO_KWH(perf.backup_heat))
            res.tot_output_btu += (hours * perf.runtime) * (perf.output_btu + perf.backup_heat)
            res.tot_backup_heat_btu += hours * perf.backup_heat
            
            # when min output is higher than load
            if perf.runtime < (55/60):
                res.cycling_hours += hours
            
            # spends less than half the time heating
            if perf.runtime < (30/60):
                res.cycling_under_50_50_hours += hours

            # assume holding setpoint within 1 degree up & down,
            # how long to raise the indoor temperature by 2 degrees?
            # assume short cycle if it takes less than 10 mins.
            tdiff = 2
            if volume and perf.output_btu > btuh:
                nbtus = BTU_PER_CUFT_F * volume * tdiff
                minutes = 60 * (nbtus / (perf.output_btu - btuh))
                if minutes < 10:
                    res.short_cycling_hours += hours
            else:
                # outputs a full hours worth of heat in under 10 min.
                if perf.runtime < (10/60):
                    res.short_cycling_hours += hours

        res.SCOP = BTU_TO_KWH(res.tot_output_btu) / res.tot_input_kwh
        res.HSPF = res.tot_output_btu / (1000*res.tot_input_kwh)
        results.append(res)

    # sort results with highest SCOP first
    results.sort(key=lambda r: r.SCOP, reverse=True)
    return results
