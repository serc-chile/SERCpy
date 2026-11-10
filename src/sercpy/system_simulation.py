# -*- coding: utf-8 -*-
"""
Created on Tue Oct 27 15:44:20 2026

@author: adria
"""

class IterationsCounter:
    def __init__(self):
        self._it = 0
        
    @property
    def it(self):
        return self._it
    
    def iterate(self):
        self._it += 1
        
    def reset(self):
        self._it = 0

class Simulation:
    
    def __init__( self, *,
                 
                 solar_thermal_system,
                 operating_conditions,
                 iterations_counter,
                 max_iterations = 100 ):
        
        self._solar_thermal_system = solar_thermal_system
        self._operating_conditions = operating_conditions
        self._iterations_counter = IterationsCounter()
        self._max_iterations = max_iterations
        
    def compute_time_step( self ):
        
        self._iterations_counter.reset()
        
        while self._iterations_counter.it < self._max_iterations:
            
            