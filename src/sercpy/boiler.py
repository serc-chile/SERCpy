# -*- coding: utf-8 -*-
"""
Created on Thu Nov 19 10:38:19 2026

@author: adria
"""

from .devices import Outlet, Device
from .units import convert_units, get_unit_types
import warnings
import numpy as np

# For fuels, emission factor (EF) is expressed in kg_CO2 / kg_fuel
# For electricity, it is expressed in kg_CO2 / J. WARNING: This value may vary largely
# depending on the technology used by each country to produce electricity
_fuel_database = {
    
    'LPG': {'name': 'Liquefied petroleum gas', 'density': 2.15, 'density_liquid': 537, 'LHV': 45.5e6, 'HHV': 49.3e6, 'EF': 2.98463 }, # liquified petroleum gas
    'NG': {'name': 'Natural gas', 'density': 0.777, 'LHV': 47.1e6, 'HHV': 52.2e6, 'EF': 2.6928 }, # natural gas
    'CH4': {'name': 'Methane', 'density': 0.716, 'LHV': 50.0e6, 'HHV': 55.5e6, 'EF': 2.75 }, # methane
    'C3H8': {'name': 'Propane', 'density': 1.875, 'density_liquid': 498, 'LHV': 46.4e6, 'HHV': 50.4e6, 'EF': 3 }, # propane
    'C4H10': {'name': 'Butane', 'density': 2.51, 'density_liquid': 578, 'LHV': 45.3e6, 'HHV': 49.1e6, 'EF': 3.035 }, # butane
    'DIESEL': {'name': 'Diesel', 'density': 846, 'LHV': 42.6e6, 'HHV': 45.6e6, 'EF': 3.1863 }, # diesel
    'COAL': {'name': 'Coal', 'density': 1300, 'LHV': 29.0e6, 'HHV': 30.2e6, 'EF': 2.44068 }, # bituminous coal
    'BIOMASS': {'name': 'Biomass', 'density': 760*0.9, 'LHV': 14.4e6, 'HHV': 17.6e6, 'EF': 1.7472 }, # biomass
    'FUELOIL5': { 'name':  'Fuel Oil No. 5', 'density': 952, 'LHV': 40.8e6, 'HHV': 43.4e6, 'EF': 3.14 }, # Fuel oil No 5
    'FUELOIL6': { 'name':  'Fuel Oil No. 6', 'density': 985, 'LHV': 40.2e6, 'HHV': 42.5e6, 'EF': 3.14 }  } # Fuel oil No 6

_fuel_alias_dict = {
    
    'LIQUEFIEDPETROLEUMGAS': 'LPG',
    'LIQUIDPETROLEUMGAS': 'LPG',
    'LIQUEFIEDPETROLGAS': 'LPG',
    'LIQUIDPETROLGAS': 'LPG',
    'LIQUEFIEDOILGAS': 'LPG',
    'LIQUIDOILGAS': 'LPG',
    'LPGAS': 'LPG',
    'NATURALGAS': 'NG',
    'METHANE': 'CH4',
    'PROPANE': 'C3H8',
    'BUTANE': 'C4H10',
    'FUELOILN5': 'FUELOIL5',
    'FUELOILNO5': 'FUELOIL5',
    'FO5': 'FUELOIL5',
    'FON5': 'FUELOIL5',
    'FONO5': 'FUELOIL5',
    'FUELOILN6': 'FUELOIL6',
    'FUELOILNO6': 'FUELOIL6',
    'FO6': 'FUELOIL6',
    'FON6': 'FUELOIL6',
    'FONO6': 'FUELOIL6' }

automatic_boiler_allowed_arguments = [
    
    "efficiency",
    "heat_source",
    "heating_value_type",
    "fuel_heating_value",
    "heating_value_units",
    "fuel_density",
    "density_units",
    "fuel_pressure",
    "fuel_pressure_abs",
    "pressure_units",
    "emission_factor",
    "emission_factor_units", ]

class AutomaticBoiler( Device ):
    """
    Model for a boiler that automatically adjusts 
    its power to heat a flow to
    a desired setpoint temperature.
    
    It has a constant thermal efficiency.
    
    Several widely used fuels (and electricity)
    are supported as heat sources.
    If the boiler to be modeled uses a fuel
    that is not supported, the user can
    introduce the fuel's features manually
    through the initialization parameters of the class.
    
    Supported heat sources are:
        
        - Electricity
        - Liquefied petroleum gas (alias: LPG)
        - Natural gas (alias: NG)
        - Methane (alias: CH4)
        - Propane (alias: C3H8)
        - Butane (alias: C4H10)
        - Diesel
        - Fuel Oil No. 5 (alias: Fuel oil 5)
        - Fuel Oil No. 6 (alias: Fuel oil 6)
        - Coal
        - Biomass
        
    The user must also keep in mind that, in the case of electricity, no default
    emission factor is available. Therefore, if the parameter `emission_factor`
    is left unspecified for boilers that use electricty, emissions will not be
    computed.
    
    Parameters
    ----------
    efficiency : float
        Thermal efficiency of the boiler. Its value must be >= 0.01 (i.e. 1%).
        It can be larger than one if it is defined using the lower heating
        value (LHV) of the fuel as reference
        (see the argument `heating_value_type`).
    
    heat_source : str
        One of the supported heat sources listed above. If not provided
        (or if the string provided does not correspond to one of the supported heat sources),
        the features of the fuel can be specified with the parameters below.

    heating_value_type : str, optional
        String defining whether the higher- or the lower heating value of
        the supported fuel introduced through the argument `heat_source` is used
        to define the efficiency of the bolier (argument `efficiency`).
        For the higher heating value, accepted strings are `"H"`, `"high"`,
        `"higher"`, and `"HHV"`. For the lower heating value,
        accepted strings are `"L"`, `"low"`, `"lower"`, `"LHV"`. If not provided,
        this parameter defaults to `"LHV"`.
    
    fuel_heating_value : float
        Heating value of the fuel used by the boiler. If `heat_source` is not
        specified, this parameter is mandatory. If a supported fuel is introduced
        through `heat_source` and `fuel_heating_value` is also provided, the value
        specified in `fuel_heating_value` overrides the one used
        by default.
    
    heating_value_units : str
        Units in which `fuel_heating_value` is being
        specified. See :doc:`Units </units/units>`.
        The units introduced can have the form 'energy/mass' or 'energy/volume'.
        The latter option is only possible if the fuel's density is known, either by
        introducing it through `fuel_density` or by introducing a supported fuel
        through the argument `heat_source`. If not specified, this parameter
        defaults to `"J/kg"`
    
    fuel_density : float
        Density of the fuel used by the boiler.
        This parameter is never mandatory.
        However, if no supported fuel is introduced
        through `heat_source` and this parameter
        is not specified either, density will be unknown.
        The effect of this is that
        the fuel's heating value cannot
        be introduced in terms of 'energy / volume',
        and the fuel's emission factor cannot
        be introduced in terms of 'CO2 mass / fuel volume'.
        If a supported fuel is introduced
        through `heat_source` and `fuel_density`
        is also provided, the value
        specified in `fuel_density` overrides the one used
        by default.
    
    density_units : str
        Units in which `fuel_heating_value` is being
        specified. See :doc:`Units </units/units>`.
    
    fuel_pressure : float or str
        Manometric (i.e. relative) pressure at which
        the fuel's volumetric consumption is measured.
        It is used to compute the fuel's density so that consumption in terms
        of volume can be converted to consumption in terms of mass.
        This parameter only makes a difference for the following gasoues fuels:
        LPG, NG, Methane, Propane, Butane. If `fuel_density` is provided by the user,
        this parameter is ignored. This parameter can also have the string value `"l"`,
        which means that volumetric consumption is measured for liquefied gas
        (i.e., the density of liquefied gas is considered). This only applies to
        LPG, Propane, and Butane. An alternative to this parameter is `fuel_pressure_abs`.
        If none of these two parameters is provided, it is assumed that volumetric consumption
        is measured at atmospheric pressure. This is true for many consumption meters, which
        automatically convert the volume measured to the volume the gas would have at
        standard temperature and pressure conditions.
    
    fuel_pressure_abs : float
        Same effect as `fuel_pressure`. The difference is that this parameter is
        interpreted aas the absolute gas pressure (not relative). Only one of
        the two parameters can be specified.
    
    pressure_units : str
        Units in which `fuel_pressure` or `fuel_pressure_abs` is being specified.
        See :doc:`Units </units/units>`. If not provided, this parameter defaults
        to `"Pa"`.
    
    emission_factor : float
        Value that defines the ratio between the
        emissions produced by the boiler's
        operation and its consumption.
        For boilers that use electricity, this parameter
        **must** be provided in order for the boiler to compute its
        emissions. There is no default value for the emission factor
        associated to electric energy because
        this value is highly dependent on the
        technology used by energy producers.
        For the other supported heat sources (fuels) there are default
        emission factors. That value can be
        overriden by specifying this parameter.
    
    emission_factor_units : str
        Units in which `emission_factor` is being specified.
        For boilers that use electricity, the units must have the form
        `CO2_mass/electric_energy`, e.g. `kg/kWh`.
        For fuels, it can be defined in three different
        ways: **(1)** CO2 mass per fuel mass;
        **(2)** CO2 mass per fuel volume; and
        **(3)** CO2 mass per fuel-equivalent energy.
        In the latter case, the equivalence
        between fuel and energy is computed with the
        heating value of the fuel.
    
    """
    
    def __init__(self, *,
                 
                 efficiency,
                 heat_source = None,
                 heating_value_type = None,
                 fuel_heating_value = None,
                 heating_value_units = None,
                 fuel_density = None,
                 density_units = None,
                 fuel_pressure = None,
                 fuel_pressure_abs = None,
                 pressure_units = None,
                 emission_factor = None,
                 emission_factor_units = None ):
        
        if efficiency is None:
            raise TypeError( "AutomaticBoiler: Argument 'efficiency' cannot be None." )
        
        self._efficiency = self._validate_argument( "efficiency", efficiency )
        
        heat_source_corrected = self._validate_argument( "heat_source", heat_source )
        
        emission_factor = self._validate_argument("emission_factor", emission_factor)
        emission_factor_units = self._validate_argument("emission_factor_units", emission_factor_units)
        
        if heat_source_corrected in [ 'E', 'ELEC', 'ELECTRICITY' ]:
            
            if self._efficiency > 1:
                raise ValueError("AutomaticBoiler: Argument 'efficiency' must be <= 1.")
            
            self._heat_source = 'Electricity'
            self._fuel_heating_value = None
            self._fuel_density = None
            
            if emission_factor is not None:
                if emission_factor_units is not None:
                    try:
                        self._emission_factor = convert_units(emission_factor, emission_factor_units, "kg/J")
                    except:
                        raise ValueError( f"AutomaticBoiler: Argument 'emission_factor_units' is not valid (value provided: {emission_factor_units}). For electricity, emission factor must have units with the form 'mass / energy'" )
                else:
                    self._emission_factor = emission_factor
                self._emission_factor_units = 'kg/J'
            else:
                self._emission_factor = None
                self._emission_factor_units = None
                
            self.outlet = Outlet()
            return
        
        heating_value_type = self._validate_argument("heating_value_type", heating_value_type )
        fuel_heating_value = self._validate_argument("fuel_heating_value", fuel_heating_value )
        heating_value_units = self._validate_argument("heating_value_units", heating_value_units )
        fuel_density = self._validate_argument("fuel_density", fuel_density )
        density_units = self._validate_argument("density_units", density_units )
        fuel_pressure = self._validate_argument("fuel_pressure", fuel_pressure )
        fuel_pressure_abs = self._validate_argument("fuel_pressure_abs", fuel_pressure_abs )
        pressure_units = self._validate_argument("pressure_units", pressure_units )
        emission_factor = self._validate_argument("emission_factor", emission_factor )
        emission_factor_units = self._validate_argument("emission_factor_units", emission_factor_units )
        
        known_fuel = ( heat_source_corrected in _fuel_database or
                       heat_source_corrected in _fuel_alias_dict   )
        
        if not known_fuel:
            
            if self._efficiency > 1:
                raise ValueError("AutomaticBoiler: Argument 'efficiency' must be <= 1.")
            
            self._heat_source = heat_source
            
            if fuel_heating_value is None:
                raise TypeError("AutomaticBoiler: No valid 'heat_source' was provided. Hence, 'fuel_heating_value' must be provided.")
                
            if fuel_density is None:
                warnings.warn("AutomaticBoiler: Fuel density is unknown. Boiler consumption cannot be processed or obtained in terms of volume or volumetric flowrate.")
                self._fuel_density = None
            else:
                if density_units is not None:
                    try:
                        self._fuel_density = convert_units( fuel_density, density_units, 'kg/m3' )
                    except:
                        raise ValueError( f"AutomaticBoiler: Argument 'density_units' is not valid  (value provided: {density_units}). Density must have units with the form 'mass / volume'")
                else:
                    self._fuel_density = fuel_density
                
            if heating_value_units is not None:
                try:
                    heating_value_unit_types = get_unit_types( heating_value_units )
                except:
                    raise ValueError(f"AutomaticBoiler: Argument 'heating_value_units' is not valid. Units provided: {heating_value_units}.")
                if not heating_value_unit_types in [ 'energy / mass', 'energy / volume' ]:
                    raise ValueError("AutomaticBoiler: Argument 'heating_value_units' must be a string representing units with the form 'energy / mass' or 'energy / volume'")
                if heating_value_unit_types == 'energy / volume' and self._fuel_density is None:
                    raise TypeError("AutomaticBoiler: Argument 'heating_value_units' has the form 'energy / volume'. In order for this format to be allowed, the density of the fuel must be provided.")
                self._fuel_heating_value = convert_units( fuel_heating_value, heating_value_units, 'J/kg', density = self._fuel_density )
            else:
                self._fuel_heating_value = fuel_heating_value
            
            if emission_factor is not None:
                if emission_factor_units is not None:
                    try:
                        emission_factor_unit_types = get_unit_types( emission_factor_units )
                    except:
                        raise ValueError(f"AutomaticBoiler: Argument 'emission_factor_units' is not valid. Units provided: {emission_factor_units}.")
                    if not emission_factor_unit_types in [ 'mass / mass', 'mass / volume', 'mass / energy' ]:
                        raise ValueError("AutomaticBoiler: Argument 'emission_factor_units' must be a string representing units with one of the allowed forms: 'mass / mass', 'mass / volume', or 'mass / energy'")
                    if emission_factor_unit_types == 'mass / volume' and self._fuel_density is None:
                        raise TypeError("AutomaticBoiler: Argument 'emission_factor_units' has the form 'mass / volume'. In order for this format to be allowed, the density of the fuel must be provided.")
                    if emission_factor_unit_types == 'mass / energy':
                        emission_factor_mass_per_energy_SI_units = convert_units( emission_factor, emission_factor_units, 'kg/J' )
                        emission_factor_kg_per_kg = emission_factor_mass_per_energy_SI_units * self._heating_value
                    else:
                        emission_factor_kg_per_kg = convert_units( emission_factor, emission_factor_units, 'kg/kg', density = self._density )
                    self._emission_factor = emission_factor_kg_per_kg
                else:
                    self._emission_factor = emission_factor
            else:
                self._emission_factor = None
                
            self.outlet = Outlet()
            return
        
        try:
            heat_source_data = _fuel_database[ heat_source_corrected ]
        except KeyError:
            heat_source_data = _fuel_database[ _fuel_alias_dict[ heat_source_corrected ] ]
            
        self._heat_source = heat_source_data[ 'name' ]
        
        if fuel_heating_value is None:
            if heating_value_type is None or heating_value_type == 'LHV':
                self._fuel_heating_value = heat_source_data[ 'LHV' ]
                max_efficiency = float( np.round( heat_source_data[ 'HHV' ] / heat_source_data[ 'LHV' ] - 1e-3, 4 ) )
                if self._efficiency > max_efficiency:
                    raise ValueError(f"AutomaticBoiler: Argument 'efficiency' must be <= {max_efficiency}.")
            else:
                if self._efficiency > 1:
                    raise ValueError("AutomaticBoiler: Argument 'efficiency' must be <= 1.")
                self._fuel_heating_value = heat_source_data[ 'HHV' ]
        
        if fuel_density is not None:
            if density_units is not None:
                try:
                    self._fuel_density = convert_units( fuel_density, density_units, 'kg/m3' )
                except:
                    raise ValueError( f"AutomaticBoiler: Argument 'density_units' is not valid  (value provided: {density_units}). Density must have units with the form 'mass / volume'")
            else:
                self._fuel_density = fuel_density
        elif fuel_pressure is not None and self._heat_source in [ 
                
                'Liquefied petroleum gas',
                'Natural gas',
                'Methane',
                'Propane',
                'Butane', ]:
            
            if fuel_pressure_abs is not None:
                raise TypeError("AutomaticBoiler: Only one of the arguments 'fuel_pressure' and 'fuel_pressure_abs' must be provided.")
            if fuel_pressure == 'l':
                if self._heat_source in [ 'Natural gas', 'Methane', ]:
                    raise ValueError("AutomaticBoiler: Liquefied state (defined by fuel_pressure = 'l') is not supported for methane and natural gas.")
                self._fuel_density = heat_source_data[ 'density_liquid' ]
            else:
                if not fuel_pressure >= 0:
                    raise ValueError("AutomaticBoiler: Argument 'fuel_pressure' must be larger than zero.")
                if pressure_units is not None:
                    try:
                        fuel_pressure = convert_units( fuel_pressure, pressure_units, 'Pa' )
                    except:
                        raise ValueError("AutomaticBoiler: Pressure units provided are not valid (argument 'pressure_units').")
                fuel_pressure_abs = fuel_pressure + 101325
                self._fuel_density = heat_source_data[ 'density' ] * fuel_pressure_abs / 101325
            
        elif fuel_pressure_abs is not None and self._heat_source in [ 
                
                'Liquefied petroleum gas',
                'Natural gas',
                'Methane',
                'Propane',
                'Butane', ]:
            
            if fuel_pressure_abs == 'l':
                if self._heat_source in [ 'Natural gas', 'Methane', ]:
                    raise ValueError("AutomaticBoiler: Liquefied state (defined by fuel_pressure_abs = 'l') is not supported for methane and natural gas.")
                self._fuel_density = heat_source_data[ 'density_liquid' ]
            else:
                if pressure_units is not None:
                    try:
                        fuel_pressure_abs = convert_units( fuel_pressure_abs, pressure_units, 'Pa' )
                    except:
                        raise ValueError("AutomaticBoiler: Pressure units provided are not valid (argument 'pressure_units').")
                if not fuel_pressure_abs >= 100000:
                    raise ValueError(f"AutomaticBoiler: Absolute fuel pressure (argument 'fuel_pressure_abs') must be equivalent to more than 1 bar (i.e. 100000 Pa). Value obtained: {fuel_pressure_abs} Pa.")
                self._fuel_density = heat_source_data[ 'density' ] * fuel_pressure_abs / 101325
                
        else:
            self._fuel_density = heat_source_data[ 'density' ]
        
        if fuel_heating_value is not None:
            if self._efficiency > 1:
                raise ValueError("AutomaticBoiler: Argument 'efficiency' must be <= 1.")
            if heating_value_units is not None:
                try:
                    heating_value_unit_types = get_unit_types( heating_value_units )
                except:
                    raise ValueError(f"AutomaticBoiler: Argument 'heating_value_units' is not valid. Units provided: {heating_value_units}.")
                if not heating_value_unit_types in [ 'energy / mass', 'energy / volume' ]:
                    raise ValueError("AutomaticBoiler: Argument 'heating_value_units' must be a string representing units with the form 'energy / mass' or 'energy / volume'")
                self._fuel_heating_value = convert_units( fuel_heating_value, heating_value_units, 'J/kg', density = self._fuel_density )
            else:
                self._fuel_heating_value = fuel_heating_value
        
        if emission_factor is not None:
            if emission_factor_units is not None:
                try:
                    emission_factor_unit_types = get_unit_types( emission_factor_units )
                except:
                    raise ValueError(f"AutomaticBoiler: Argument 'emission_factor_units' is not valid. Units provided: {emission_factor_units}.")
                if not emission_factor_unit_types in [ 'mass / mass', 'mass / volume', 'mass / energy' ]:
                    raise ValueError("AutomaticBoiler: Argument 'emission_factor_units' must be a string representing units with one of the allowed forms: 'mass / mass', 'mass / volume', or 'mass / energy'")
                if emission_factor_unit_types == 'mass / energy':
                    emission_factor_mass_per_energy_SI_units = convert_units( emission_factor, emission_factor_units, 'kg/J' )
                    emission_factor_kg_per_kg = emission_factor_mass_per_energy_SI_units * self._heating_value
                else:
                    emission_factor_kg_per_kg = convert_units( emission_factor, emission_factor_units, 'kg/kg', density = self._density )
                self._emission_factor = emission_factor_kg_per_kg
            else:
                self._emission_factor = emission_factor
        else:
            self._emission_factor = heat_source_data[ 'EF' ]
            
        self.outlet = Outlet()
    
    @property
    def heat_source(self):
        return self._heat_source
    
    @property
    def consumption_units(self):
        pass
    
    @property
    def efficiency(self):
        return self._efficiency
    
    @property
    def condensing_boiler(self):
        return self._condensing_boiler
        
    def demand_to_consumption( self, state_in = None, state_set = None, flowrate = None, demanded_power = None, consumption_units = None ):
        
        if state_in is not None and state_set is not None and flowrate is not None:
            demanded_power = max([  flowrate*( state_set.h - state_in.h ) , 0 ] )
        else:
            if demanded_power is None:
                raise ValueError("AutomaticBoiler.demand_to_consumption: Not enough data was provided to compute the consumption.")
        
        consumption = demanded_power / self._efficiency
        
        if self._heat_source != 'Electricity':
            consumption = consumption / self._fuel_heating_value
            
        # if self._emission_factor_units
        
        return consumption
    
    def compute_outputs(self, operating_conditions, iteration_numer ):
        
        pass
    
    @staticmethod
    def _validate_argument( argument_name, value ):
        """
        Private method to confirm that a certain argument provided by the user matches the expected type and other restrictions such as range, in the case of numeric values.
        
        In some cases, this method modifies the argument so that it matches the expected format.
        
        Parameters
        ----------
        argument_name : str
            Name to identify the argument.
        value : any
            Argument value.
        
        Raises
        ------
        ValueError
            Any discrepancy between the expected value and the value provided.
        
        Returns
        -------
        value : any
            Processed value. In most cases, the value returned is the same as the input.
        
        """
        
        if type(argument_name) is not str:
            raise TypeError("SolarField._validate_argument: Argument 'argument_name' must be a string.")
        
        if not argument_name in automatic_boiler_allowed_arguments:
            raise ValueError( f"SolarField: '{argument_name}' is not a valid argument." )
        
        if value is None:
            return None
        
        if argument_name == "efficiency":
            try:
                value = float( value )
            except:
                raise TypeError("AutomaticBoiler: Argument 'efficiency' must be convertible to 'float'.")
            if not value >= 0.01:
                raise ValueError("AutomaticBoiler: Argument 'efficiency' must be >= 0.01.")
        
        if argument_name == "heat_source":
            try:
                value = str(value)
            except:
                raise TypeError("AutomaticBoiler: Argument 'heat_source' must be convergible to type 'str'.")
            value = str( value ).upper().translate(str.maketrans( '', '', ' -_.%' ) )
        
        if argument_name == "heating_value_type":
            
            try:
                value = str(value)
            except:
                raise TypeError("AutomaticBoiler: Argument 'heating_value_type' must be convertible to string.")
            value = value.upper()
            if not value in [ 'L', 'LOW', 'LOWER', 'LHV', 'H', 'HIGH', 'HIGHER', 'HHV' ]:
                raise ValueError("AutomaticBoiler: Argument 'heating_value_type' must be one of the values: 'l', 'low', 'lower', 'lhv', 'h', 'high', 'higher', 'hhv'.")
            if value in [ 'L', 'LOW', 'LOWER', 'LHV' ]:
                value = 'LHV'
            else:
                assert value in [ 'H', 'HIGH', 'HIGHER', 'HHV' ]
                value = 'HHV'
            
        if argument_name in [
                
                "fuel_heating_value" ,
                "fuel_density",
                "emission_factor", ]:
            
            try:
                value = float( value )
            except:
                raise TypeError(f"AutomaticBoiler: Argument '{argument_name}' must be convertible to float.")
            if not value > 0:
                raise ValueError(f"AutomaticBoiler: Argument '{argument_name}' must be larger than zero.")
                
        if argument_name in [
                
                "fuel_pressure",
                "fuel_pressure_abs", ]:
            
            if type( value ) is str and value == 'l':
                return value
            
            try:
                value = float( value )
            except:
                raise TypeError(f"AutomaticBoiler: Argument '{argument_name}' must be convertible to float. The string 'l' is also allowed for liquefied gases.")
        
        if argument_name in [ 
                
                 "heating_value_units",
                 "density_units",
                 "pressure_units",
                 "emission_factor_units",
                
                ]:
            
            try:
                value = str(value)
            except:
                raise TypeError(f"AutomaticBoiler: Argument '{argument_name}' must be convertible to string.")
        
        return value
    
    def compute_outputs( operating_conditions, time_step_number ):
        
        pass