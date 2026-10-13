# -*- coding: utf-8 -*-
"""
Created on Thu Oct  8 15:24:12 2026

@author: Adrian Riebel Brummer
"""

from .meteo_profile import MeteoProfile
from .demand_profile import DemandProfile
from typing import Optional
import pandas as pd
import warnings

class OperatingConditions:
    
    def __init__(
            
            self, *,
            
            meteo_profile: MeteoProfile,
            demand_profile: DemandProfile,
            
            time_step_min: Optional[ int ] = None ):
        
        self._ready = False
        
        if not isinstance(meteo_profile, MeteoProfile):
            raise TypeError("OperatingConditions: Argument 'meteo_profile' must be a meteo_profile.MeteoProfile instance.")
        if not isinstance(demand_profile, DemandProfile):
            raise TypeError("OperatingConditions: Argument 'demand_profile' must be a demand_profile.DemandProfile instance.")
                
        
        meteo_df = meteo_profile.get_conditions()
        
        date_times = pd.DatetimeIndex( meteo_df[ "timestamp" ] )
        
        self._minutal_profiles = { "timestamp": date_times }
        
        for column in meteo_df.columns.tolist():
            
            if column == "timestamp":
                continue
            
            self._minutal_profiles[ column ] = meteo_df[ column ].values
            
        demand_df = demand_profile.get_demand_conditions( date_times )
        
        for column in demand_df.columns.tolist():
            
            self._minutal_profiles[ column ] = demand_df[ column ].values
        
        if time_step_min is not None:
            self.set_time_step( time_step_min )
        
    def set_time_step( self, time_step_min ):
        
        if type( time_step_min ) is not int:
            try:
                time_step_min = int( time_step_min )
                warnings.warn("OperatingConditions.set_time_step: Argument 'time_step_min' was converted to type 'int'.")
            except:
                raise TypeError("OperatingConditions: Argument 'time_step_min' must be convertible to type 'int'.")
        if not time_step_min in [ 1, 2, 3, 4, 5, 6, 10, 12, 15, 20, 30, 60 ]:
            raise ValueError("OperatingConditions.set_time_step: Argument 'time_step_min' must be one of the allowed values: 1, 2, 3, 4, 5, 6, 10, 12, 15, 20, 30, and 60")
        
        self._effective_profiles = { "timestamp": [ self._minutal_profiles[ "timestamp" ][ i ] for i in range( 0, 525600, time_step_min ) ] }
        
        for key in self._minutal_profiles:
            
            if key == "timestamp":
                continue
            
            self._effective_profiles[ key ] = self._minutal_profiles[ key ].reshape(-1, time_step_min).mean(axis=1).astype(float).tolist()
        
        self._ready = True
            
    def get_conditions( self, time_step_number ):
        
        return { key: float( self._effective_profiles[ key ][ time_step_number ] ) for key in self._effective_profiles }
