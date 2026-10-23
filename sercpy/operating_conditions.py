# -*- coding: utf-8 -*-
"""
Created on Thu Oct  8 15:24:12 2026

@author: Adrian Riebel Brummer
"""

from .meteo_profile import MeteoProfile
from .demand_profile import DemandProfile
from typing import Optional
import pandas as pd

class OpCondError(Exception):
    pass

class OperatingConditions:
    """
    Class that provides the operating conditions of a solar thermal system throughout an entire operation year.
    
    It takes a MeteoProfile instance, a DemandProfile instance, and a time step to generate the data that will be provided to the system simulation.
    
    Parameters
    ----------
    
    meteo_profile : :doc:`MeteoProfile </meteo_profile/meteo_profile_class>`
        Object from which the meteorological data (ambient temperature, irradiance, mains water temperature, etc) is extracted.
    
    demand_profile : :doc:`DemandProfile </demand_profile/demand_profile_class>`
        Object from which the demand data (i.e. demanded flowrate, temperature setpoint and inlet temperature of the heat transfer flow) is extracted.
    
    time_step_min : int, optional
        Simulation time step in minutes. Accepted values are: 1, 2, 3, 4, 5, 6, 10, 12, 15, 20, 30, and 60. If not provided, it can be specified later with the method `OperatingConditions.set_time_step( time_step_min )`.
    
    """
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
            
    @property
    def time_step(self):
        "Get the simulation time step in minutes."
        if not self._ready:
            ("OperatingConditions: Time step has not been set. Use the method `OperatingConditions.set_time_step`")
        return self._time_step
    
    @property
    def time_step_min(self):
        "Get the simulation time step in minutes."
        return self.time_step
    
    @property
    def time_steps_per_day(self):
        "Number of time steps per day, according to the current time step."
        if not self._ready:
            ("OperatingConditions: Time step has not been set. Use the method `OperatingConditions.set_time_step`")
        return self._time_steps_per_day
    
    @property
    def time_steps_per_hour(self):
        "Number of time steps per hour, according to the current time step."
        if not self._ready:
            ("OperatingConditions: Time step has not been set. Use the method `OperatingConditions.set_time_step`")
        return self._time_steps_per_hour
    
    def to_df(self):
        """
        Get the entire dataset stored by the `OperatingConditions` instance as a `pandas.DataFrame`.

        Returns
        -------
        `pandas.DataFrame <https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.html>`_
            DataFrame containing the data for all time steps of an entire year. The columns of the DataFrame have the same names as the keys of the dictionaries returned by the method `OperatingConditions.get_conditions`.

        """
        if not self._ready:
            ("OperatingConditions: Time step has not been set. Use the method `OperatingConditions.set_time_step`")
        
        return pd.DataFrame.from_dict( self._effective_profiles )
        
    def set_time_step( self, time_step_min ):
        """
        Set the time step of an `OperatingConditions` instance.
        
        This can be done for:
            
            - `OperatingConditions` instances for which the time step has not been defined previously.
            - `OperatingConditions` instances for which the time step was already defined, in order to re-define the time step, thus reconstructing the profiles that are provided to the simulations.

        Parameters
        ----------
        time_step_min : int
            Time step in minutes. Valid values are: 1, 2, 3, 4, 5, 6, 10, 12, 15, 20, 30, and 60.

        Raises
        ------
        TypeError
            If the time step introduced cannot be interpreted as an integer.
        ValueError
            If the time step introduced is not within the allowed values.

        Returns
        -------
        None.

        """
        
        try:
            assert time_step_min.is_integer()
        except AttributeError:
            raise TypeError(f"OperatingConditions: Argument 'time_step_min' could not be interpreted as a number. Value type: { type( time_step_min ) }.")
        except AssertionError:
            raise ValueError("OperatingConditions: Argument 'time_step_min' must be an integer value.")
        
        time_step_min = int( time_step_min )
        if not time_step_min in [ 1, 2, 3, 4, 5, 6, 10, 12, 15, 20, 30, 60 ]:
            raise ValueError("OperatingConditions.set_time_step: Argument 'time_step_min' must be one of the allowed values: 1, 2, 3, 4, 5, 6, 10, 12, 15, 20, 30, and 60")
        
        self._effective_profiles = { "timestamp": [ self._minutal_profiles[ "timestamp" ][ i ] for i in range( 0, 525600, time_step_min ) ] }
        
        for key in self._minutal_profiles:
            
            if key == "timestamp":
                continue
            
            self._effective_profiles[ key ] = self._minutal_profiles[ key ].reshape(-1, time_step_min).mean(axis=1).astype(float).tolist()
        
        self._time_step = time_step_min
        self._time_steps_per_year = len( self._effective_profiles[ "timestamp" ] )
        assert self._time_steps_per_year%365 == 0
        assert self._time_steps_per_year%8760 == 0
        self._time_steps_per_day = self._time_steps_per_year//365
        self._time_steps_per_hour = self._time_steps_per_year//8760
        
        self._ready = True
            
    def get_conditions( self, time_step_number ):
        """
        Method to retrieve the operating conditions for a specific moment. The instant in time is specified as an index within the yearly profile.
        
        Parameters
        ----------
        time_step_number : int
            Time step number for which the conditions will be returned. The standard numbering goes from 0 to the number of time steps per year minus one. Nevertheless, numbers out of this range are valid as well; in this case, the values returned become cyclic.
        
        Returns
        -------
        dict
            Dictionary containing the values of the system's operating conditions. The keys within the dictionary have the same names as the data returned by the MeteoProfile and the DemandProfile instances.
        
        """
        
        try:
            assert time_step_number.is_integer()
        except AttributeError:
            raise TypeError(f"OperatingConditions: Argument 'time_step_number' could not be interpreted as a number. Value type: { type( time_step_number ) }.")
        except AssertionError:
            raise ValueError("OperatingConditions: Argument 'time_step_number' must be an integer value.")
            
        if not self._ready:
            raise OpCondError("OperatingConditions.get_conditions: Time step has not been set. Use the method `OperatingConditions.set_time_step`.")
        
        time_step_number = int( time_step_number )
        
        time_step_number = time_step_number%self._time_steps_per_year
        
        return { key: float( self._effective_profiles[ key ][ time_step_number ] ) for key in self._effective_profiles }
