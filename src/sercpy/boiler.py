# -*- coding: utf-8 -*-
"""
Created on Thu Nov 19 10:38:19 2026

@author: adria
"""

from .devices import Outlet
from .core import Energy_Sources_Database

automatic_boiler_allowed_arguments = [
    
    "efficiency",
    "heat_source",
    "condensation_boiler" ]

class AutomaticBoiler( Device ):
    """
    Model for a boiler that automatically heats a flow to
    a desired setpoint temperature.
    
    It has a constant efficiency.
    
    Both conventional boilers and condenstation boilers are supported.
    The difference between those models is that, for condensation boilers,
    the efficiency is computed considering the higher heating value (HHV)
    of the fuel.
    
    Available heat sources are:
        
        - Liquefied Petroleum Gas
        - Natural Gas
        - Methane
        - Propane
        - Butane
        - Diesel
        - Coal
        - Biomass
        - Electricity
    
    Parameters
    ----------
    heat_source : str
        One of the supported heat sources listed above.
        
    efficiency : float
        Float in the range 0.05 - 0.99 defining the global thermal efficiency of the heater.
    
    condensation_boiler : bool, optional
        Boolean value defining whether the heater is a condensation heater, i.e.,
        whether the water present in the combustion gases is condensed to increase
        the amount of energy extracted from them.
    
    
    """
    
    def __init__(self, heat_source, efficiency, condensation_boiler = False ):
        
        if heat_source is None:
            raise TypeError("AutomaticBoiler: Argument 'heat_source' cannot be None.")
        if efficiency is None:
            raise TypeError("AutomaticBoiler: Argument 'efficiency' cannot be None.")
        if condensation_boiler is None:
            raise TypeError("AutomaticBoiler: Argument 'condensation_boiler' cannot be None.")
        
        heat_source_corrected = self._validate_argument("heat_source", heat_source)
        efficiency = self._validate_argument("efficiency", efficiency)
        condensation_boiler = self._validate_argument("condensation_boiler", condensation_boiler)
        
        if heat_source_corrected != "ELECTRICITY" and condensation_boiler:
            self._heating_value = Energy_Sources_Database[ heat_source_corrected ][ 'HHV' ]
            self._condensation_boiler = True
        elif heat_source_corrected == "ELECTRICITY":
            self._heating_value = None
            self._condensation_boiler = False
        else:
            self._heating_value = Energy_Sources_Database[ heat_source_corrected ][ 'LHV' ]
            self._condensation_boiler = False
        
        self._heat_source = heat_source
        self._efficiency = efficiency
        
    @property
    def heat_source(self):
        return self._heat_source
    
    @property
    def efficiency(self):
        return self._efficiency
    
    @property
    def condensation_boiler(self):
        return self._condensation_boiler
    
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
            if not (value >= 0.05 and value <= 0.99):
                raise ValueError("AutomaticBoiler: Argument 'efficiency' must be in the range 0.05 <= efficiency <= 0.99.")
                
        if argument_name == "heat_source":
            try:
                value = str(value)
            except:
                raise TypeError("AutomaticBoiler: Argument 'heat_source' must be convergible to type 'str'.")
            value_upper = value.upper()
            if not value_upper in Energy_Sources_Database:
                raise ValueError(f"AutomaticBoiler: Argument 'heat_source' (value: {value}) not recognized.")
            value = value_upper
            
        if argument_name == "condensation_boiler":
            if not (value == True or value == False):
                raise TypeError("AutomaticBoiler: Argument 'condensation_boiler' must be a boolean value.")
            value = bool(value)
            
        return value
    
    def compute_outputs( operating_conditions, time_step_number ):
        
        