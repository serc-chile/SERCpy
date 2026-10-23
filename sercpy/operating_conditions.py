# -*- coding: utf-8 -*-
"""
Created on Thu Oct  8 15:24:12 2026

@author: Adrian Riebel Brummer
"""

from .meteo_profile import MeteoProfile
from .demand_profile import DemandProfile
from typing import Optional
import pandas as pd
import numpy as np

class OpCondError(Exception):
    pass

class OperatingConditions:
    """
    Class that provides the operating conditions of a solar thermal system throughout an entire operation year.
    
    It takes a :doc:`MeteoProfile </meteo_profile/meteo_profile_class>` instance, a :doc:`DemandProfile </demand_profile/demand_profile_class>` instance, and a time step to generate the data that will be provided to the system simulation.
    
    Parameters
    ----------
    
    meteo_profile : :doc:`MeteoProfile </meteo_profile/meteo_profile_class>`
        Object from which the meteorological data (ambient temperature, irradiance, mains water temperature, etc) is extracted.
    
    demand_profile : :doc:`DemandProfile </demand_profile/demand_profile_class>`
        Object from which the demand data (i.e. demanded flowrate, temperature setpoint and inlet temperature of the heat transfer flow) is extracted.
    
    time_step_min : int, optional
        Simulation time step in minutes. Accepted values are: 1, 2, 3, 4, 5, 6, 10, 12, 15, 20, 30, and 60. If not provided, it can be specified later with the method `OperatingConditions.set_time_step( time_step_min )`.
    
    include_solar_position : bool, optional
        Whether to include the solar position data in the yearly profiles (`"zenith"`, `"apparent_zenith"`, and `"azimuth"`). This is not necessary for standard simulations carried out by SERCpy, and it may extend initialization time of the object. Therefore, it defaults to False.
    
    Attributes
    ----------
    time_step : int
        Time step length in minutes. It must be established by the user at initialization, or by using the method `OperatingConditions.set_time_step`.
    
    time_step_min : int
        Alias for `time_step`.
    
    time_steps_per_day : int
        Number of time steps per day. E.g. with a 6-minute time step, this value would be `240`.
    
    time_steps_per_hour : int
        Number of time steps per hour. E.g. with a 6-minute time step, this value would be `10`.
        
    Methods
    -------
    get_conditions( time_step_number )
        Get a dictionary with the operating conditions of the system at the instant defined by `time_step_number`. This includes both meteorological- and demand conditions. The number introduced represents an "index" within the yearly profile. Returns: dict.
    
    set_time_step( time_step_min )
        Method to set the simulation time step. It can be used to modify another time step value previously established. Returns: None
        
    to_df()
        Get a `pandas.DataFrame` containing the conditions dataset of the whole simulation year. Returns: `pandas.DataFrame <https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.html>`_.
        
    
    """
    def __init__(
            
            self, *,
            
            meteo_profile: MeteoProfile,
            demand_profile: DemandProfile,
            
            time_step_min: Optional[ int ] = None,
            include_solar_position: Optional[ bool ] = False ):
        
        self._ready = False
        self._include_solar_position = include_solar_position
        
        if not isinstance(meteo_profile, MeteoProfile):
            raise TypeError("OperatingConditions: Argument 'meteo_profile' must be a meteo_profile.MeteoProfile instance.")
        if not isinstance(demand_profile, DemandProfile):
            raise TypeError("OperatingConditions: Argument 'demand_profile' must be a demand_profile.DemandProfile instance.")
        
        meteo_df = meteo_profile.get_conditions()
        
        date_times = pd.DatetimeIndex( meteo_df[ "timestamp" ] )
        
        print( date_times[0] )
        
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
    def time_steps_per_year(self):
        "Number of time steps per year, according to the current time step. It is equivalent to the total length of the dataset stored by the object."
        if not self._ready:
            ("OperatingConditions: Time step has not been set. Use the method `OperatingConditions.set_time_step`")
        return self._time_steps_per_year
        
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
    
    @staticmethod
    def _average_azimuth( azimuth_values ):
        """
        Private static method used to correct the error induced by averaging azimuthal solar position values during a time step in which the sun passes from azimuth = 360° to azimuth = 0°, or viceversa. This corresponds to solar midday in the Southern hemisphere.
        
        Parameters
        ----------
        azimuth_values : array-like
            List of solar azimuthal values with minutal resolution, during one simulation time step. Units: Degree (°).

        Returns
        -------
        float
            Correct average azimuthal value, in degrees (0° to 360°).

        """
        
        azimuth_values_corrected = []
        correction_type = None
        
        assert type( azimuth_values ) in [ list, np.ndarray ] and len( azimuth_values ) >= 1
        
        if len( azimuth_values ) == 1:
            return float( azimuth_values[ 0 ] )
        
        for i in range( len( azimuth_values ) ):
            
            if i == 0:
                azimuth_values_corrected.append( azimuth_values[i] )
                continue
            
            if abs( azimuth_values[i] - azimuth_values[ i - 1] ) > 180:
                if correction_type is not None:
                    raise Exception( "OperatingConditions._average_azimuth: Discontinuity encountered twice." )
                if azimuth_values[i] < azimuth_values[ i - 1 ]:
                    correction_type = 'above_360'
                else:
                    correction_type = 'below_0'
            
            if correction_type is None:
                azimuth_values_corrected.append( azimuth_values[i] )
                continue
            
            if correction_type == 'above_360':
                azimuth_values_corrected.append( 360 + azimuth_values[i] )
            elif correction_type == 'below_0':
                azimuth_values_corrected.append( azimuth_values[i] - 360 )
            else:
                raise Exception( "OperatingConditions._average_azimuth: correction_type unknown." )
        
        avg_value = float( np.mean( azimuth_values_corrected ) )
        
        if avg_value > 360:
            return avg_value - 360
        elif avg_value < 0:
            return 360 + avg_value
        return avg_value
        
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
            
            if ( not self._include_solar_position ) and key in [ "azimuth", "zenith", "apparent_zenith" ]:
                continue
            
            if key == "azimuth":
                self._effective_profiles[ key ] = [ self._average_azimuth( self._minutal_profiles[ key ][ initial_minute : initial_minute + time_step_min ] ) for initial_minute in range( 0, 525600, time_step_min ) ]
            else:
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
            Time step number for which the conditions will be returned. The number is interpreted as an index within the entire yearly profile; thus the standard numbering goes from 0 to the number of time steps per year minus one. Nevertheless, numbers out of this range are valid as well; in this case, the conditions returned become cyclic.
        
        Returns
        -------
        dict
            Dictionary containing the values of the system's operating conditions.
            The keys within the dictionary have the same names as the data returned by the MeteoProfile and the DemandProfile instances.
            **Warning:** The solar position data (zenith and azimuth) is by default ***not*** extracted from the `MeteoProfile` instance, and can therefore not be accessed by sungi this method. To change this, see `inlcude_solar_position` in the initialization arguments of the class.
        
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
        
        result = {}
        
        for key in self._effective_profiles:
            
            if key == "timestamp":
                result[ key ] = self._effective_profiles[ key ][ time_step_number ]
            else:
                result[ key ] = float( self._effective_profiles[ key ][ time_step_number ] )
                
        return result