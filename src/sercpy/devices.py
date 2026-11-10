# -*- coding: utf-8 -*-
"""
Created on Wed Oct 14 09:46:22 2026

@author: Adrian Riebel Brummer
"""

from .fluids import FluidState

class Outlet:
    """
    This very simple class has two concrete goals:
        
        1. To store the conditions of the flow that is leaving a device. These conditions are: its thermodynamic state and its flowrate.
        2. To pass the aforementioned information to the device that receives the flow.
        
    Instances of this class are meant to be attributes of the devices that make up a thermal system. A connection between two devices can be set in the following way:
        
    .. doctest::
        
        >>> from sercpy.solar import SolarField
        >>> from sercpy.heat_exchanger import HeatExchanger
        
        >>> solar_field = SolarField( ... ) #Create SolarField instance
        >>> heat_exchanger = HeatExchanger( ... ) #Create HeatExchanger instance
        
        >>> solar_field.set_connections( inlet = heat_exchanger.outlet_source ) # Connect the outlet of the heat exchanger to the inlet of the solar field
    
    After doing this, `solar_field` will compute its outputs using the flow data extracted from `heat_exchanger.outlet_source`, which is one of the two outlets of `heat_exchanger`.
    
    """
    
    @property
    def state(self):
        "Inste"
        if not hasattr( self, "_state" ):
            raise AttributeError("Outlet: Attribute 'state' has not been defined.")
        return self._state
    
    @state.setter
    def state( self, state ):
        if not isinstance(state, FluidState):
            raise TypeError("Outlet: state must be an instance of sercpy.fluids.FluidState.")
        self._state = state
    
    @property
    def flowrate(self):
        if not hasattr( self, "_flowrate" ):
            raise AttributeError("Outlet: Attribute 'flowrate' has not been defined.")
        return self._flowrate
    
    @flowrate.setter
    def flowrate(self, flowrate):
        try:
            flowrate = float(flowrate)
        except:
            raise TypeError("Outlet: flowrate must be a numeric value.")
        if flowrate < 0:
            raise ValueError(f"Outlet: Flowrate cannot be negative. Flowrate value introduced: {flowrate}")
        self._flowrate = flowrate
        
    @property
    def T(self):
        if not hasattr( self, "_state" ):
            raise AttributeError("Outlet: Attribute 'state' has not been defined.")
        return self._state.T
    
    @property
    def temp(self):
        return self.T
    
    @property
    def h(self):
        if not hasattr( self, "_state" ):
            raise AttributeError("Outlet: Attribute 'state' has not been defined.")
        return self._state.h

class Device:
    
    @property
    def input_convergence(self):
        if hasattr( self, "_convergence" ):
            return self._input_convergence
        return True
    
    @input_convergence.setter
    def input_convergence(self, value):
        try:
            value = bool( value )
        except:
            raise TypeError("Device: convergence must be a boolean value.")
        self._input_convergence = value
    
    def update_state(self):
        return
    
    def set_convergence_criteria( self, **kwargs ):
        return
    
    def set_connections( self, **kwargs ):
        return
    
    def compute_outputs( self, operating_conditions, iteration_number, **kwargs ):
        return
