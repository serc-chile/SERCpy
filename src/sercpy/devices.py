# -*- coding: utf-8 -*-
"""
Created on Wed Oct 14 09:46:22 2026

@author: Adrian Riebel Brummer
"""

from .fluids import FluidState

class Outlet:
    
    @property
    def state(self):
        return self._state
    
    @state.setter
    def state( self, state ):
        if not isinstance(state, FluidState):
            raise TypeError("Outlet: state must be an instance of sercpy.fluids.FluidState.")
        self._state = state
    
    @property
    def flowrate(self):
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
        

class Device:
    
    def __init__( self ):
        self._convergence = False
    
    @property
    def convergence(self):
        return self._convergence
    
    def update_state(self):
        return
    
    def set_convergence_criteria( self, **kwargs ):
        return
    
    def set_connections( self, **kwargs ):
        return
    
    def compute_outputs( self, operating_conditions, iteration_number, **kwargs ):
        return