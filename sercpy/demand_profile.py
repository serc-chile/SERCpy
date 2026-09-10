# -*- coding: utf-8 -*-
"""
Created on Mon Aug 17 11:18:03 2026

@author: adria
"""

from typing import Optional
import pandas as pd
import warnings
import numpy as np
from datetime import datetime
from . import profiles_app
from timeit import default_timer
from types import SimpleNamespace
from .core import (
    
    SHIPcalError,
    UnitConversionError,
    convert_units,
    weekday_names,
    month_days,
    monthly_cummulated_days,
    month_names,
    mean_squared_error,
    Energy_Sources_Database,
    
    )
from .config import default_year
from scipy.optimize import minimize, Bounds

demand_cluster_coefficients = { 0: {"m_h": -0.015442188, "b_h": 1.085192073, "m_w": -0.007095331, "b_w": 1.060986187, "T_hl": 2.9 },
                                1: {"m_h": -0.05875924, "b_h": 1.469535126, "m_w": -0.013263421, "b_w": 0.677907865, "T_hl": 17.4 },
                                2: {"m_h": -0.095984753, "b_h": 1.771938814, "m_w": -0.012756454, "b_w": 0.406994714, "T_hl": 16.4 },
                                3: {"m_h": -0.17801625, "b_h": 2.540402509, "m_w": -0.0214766, "b_w": 0.521041029, "T_hl": 12.9 } }

def compute_monthly_demand( **kwargs ):
    
    return

def translate_utc(utc_based_tz):
    if type(utc_based_tz) is not str:
        raise ValueError("Function translate_utc: input must be a string.")
    if not utc_based_tz.startswith("UTC"):
        return utc_based_tz
    if utc_based_tz in [ "UTC", "UTC-0", "UTC+0", "UTC-00:00", "UTC+00:00" ]:
        return "Etc/GMT"
    try:
        if "+" in utc_based_tz:
            GMT_sign = "-"
            offset = utc_based_tz.split("+")[1]
        if "-" in utc_based_tz:
            GMT_sign = "+"
            offset = utc_based_tz.split("-")[1]
        if ":" in offset:
            offset = int( offset.split(":")[0] )
        else:
            offset = int( offset )
        if GMT_sign == "-":
            assert offset <= 14
        else:
            assert offset <= 12
        return "Etc/GMT" + GMT_sign + str(offset)
    
    except:
        raise SHIPcalError("UTC-based timezone could not be translated to Etc/GMT")
        
def time_to_half_hours(time_string):
    
    try:
        assert type(time_string) is str and ":" in time_string
        hours = int(time_string.split(":")[0])
        minutes = int(time_string.split(":")[1])
        assert hours >= 0 and hours <= 24 and minutes in [0,30] and not ( hours == 24 and minutes == 30 )
        result = 2*hours + 1*(minutes == 30)
    except:
        raise ValueError("Function time_to_minute: input must be a string with format 'hh:mm', with 'hh' from '00' to '24' and 'mm' equal to '00' or '30'. '24:30' is not allowed.")
    return result
        
DemandProfile_accepted_args = [
    
    "T_in_profile",
    "T_set_profile",
    "flowrate_profile",
    "fluid",
    "fluid_cp",
    "fluid_density",
    "pressure",
    
    "op_start",
    "op_end",
    "op_start_saturday",
    "op_end_saturday",
    "op_start_sunday",
    "op_end_sunday",
    
    "peak_demand_ratio_saturday",
    "peak_demand_ratio_sunday",
    
    "daily_demand_ratio_saturday",
    "daily_demand_ratio_sunday",
    
    "daily_demand_profile",
    "daily_demand_profile_saturday",
    "daily_demand_profile_sunday",
    
    "daily_demand_profiles",
    "weekly_demand_profile",
    
    "weekly_demand_factors",
    
    "monthly_heat_demand",
    "heat_demand_units",
    
    "monthly_hot_fluid_demand",
    "hot_fluid_demand_units",
    
    "monthly_consumption",
    "heat_source",
    "consumption_units",
    "heater_efficiency",
    "heat_source_heating_value",
    "heat_source_density",
    
    "monthly_production",
    
    "T_set",
    "T_in",
    
    "Tamb_dependence",
    "Tamb_dependence_mode",
    "Tamb_profile",
    
    "smooth_Tamb_profile",
    "year"
    
    ]


class DemandProfile:
    
    """
    Class that computes, stores, and provides the thermal demand of a heating system throughout an entire operation year..

    It allows the user to introduce custom daily demand profiles with time resolutions as small as 30 minutes.
    
    This class also takes into account the dependence of the demanded power on the ambient temperature, also being capable of determining that degree of dependence based on the monthly heat demand provided by the user.

    Parameters
    ----------
    fluid : str, optional
        Working fluid name. Accepted values: 'water', 'air', 'therminol 66'.
    fluid_cp : float, optional
        Specific heat capacity of the working fluid (J/kg K). Needed if the parameter 'fluid' is not specified.
    fluid_density : float, optional
        Density of the working fluid (kg/m3). Needed if the parameter 'fluid' is not specified.
    T_set : float or list of float
        Setpoint of the heating system (°C). It can be a floating point value or a list of 12 values (one per month). Range: 25 <= T_set <= 150.
    T_in : float or list of float
        Setpoint of the heating system (°C). It can be a floating point value or a list of 12 values (one per month). Range: 2 <= T_set <= 130.
    monthly_heat_demand : list of float, optional
        List of values >= 0, representing the heat demand of the thermal load in each month of the year.
    heat_demand_units : str, optional
        Energy units used for the list ``monthly_heat_demand``. Only needed if that parameter is specified. Any of the following energy units is valid: ``'kWh'``, ``'MWh'``, ``'J'``, ``'kJ'``, ``'MJ'``, ``'BTU'``, ``'kBTU'``, ``'MBTU'``.
        
    monthly_consumption : float, optional
        Similar to ``monthly_heat_demand``. This parameter can be used to automatically compute the monthly heat demand from consumption of heat sources such as fuels and electricity.
    heat_source : str, optional
        Name of the heat source. Needed if the heat demand is computed from ``monthly_consumption``. Not needed if the user manually specifies the parameters ``heat_source_heating_value`` and ``heat_source_density``. Accepted values (upper cases as well): ``'electricity'``, ``'lpg'``, ``'ng'``, ``'methane'``, ``'propane'``, ``'butane'``, ``'diesel'``, ``'coal'``, ``'biomass'``.
    consumption_units : str, optional
        Needed if ``monthly_consumption`` is specified instead of ``monthly_heat_demand``. For electricity, energy units are accepted: ``'kWh'``, ``'MWh'``, ``'J'``, ``'kJ'``, ``'MJ'``, ``'BTU'``, ``'kBTU'``, ``'MBTU'``. For fuels, mass and volume units are accepted: ``'kg'``, ``'ton'``, ``'lb'``, ``'m3'``, ``'L'``, ``'gal'``, ``'ft3'``.
    heater_efficiency : float, optional
        Heater efficiency as a decimal floating point number (e.g. 80% efficiency must be specified as 0.8). Needed only if ``monthly_consumption`` is specified instead of ``monthly_heat_demand``.
    heat_source_heating_value : float, optional
        Heating value of the heat source (fuel). Not needed if a valid ``heat_source`` is provided. Considered only if ``monthly_consumption`` is specified instead of ``monthly_heat_demand``.
    heat_source_density : float, optional
        Density of the heat source (fuel). Not needed if a valid ``heat_source`` is provided. Considered only if ``monthly_consumption`` is specified instead of ``monthly_heat_demand``.
        
    daily_demand_profile : list of float, optional
        List of floating point values with length 48, 24, or a divisor of 24. It represents how thermal demand gets distributed throughout a 24-hour period (from 00:00 to 24:00), with time resolution depending on the length of the list. The values within the list have no meaningful units; the total energy demand gets distributed throughout the day proportionally to the values of the list.
    daily_demand_profile_saturday : list of float, optional
        Special daily demand profile for saturday. This parameter is only considered if ``daily_demand_profile`` is specified. The format required is the same as for ``daily_demand_profile``. If not specified, saturday is assumed to have the same profile as week days (given by the parameter ``daily_demand_profile``).
    daily_demand_profile_sunday : list of float, optional
        Special daily demand profile for sunday. This parameter is only considered if ``daily_demand_profile`` is specified. The format required is the same as for ``daily_demand_profile``. If not specified, the behavior depends on whether ``daily_demand_profile_saturday`` was specified. If it was specified, sunday is assumed to have no demand at all. If it was not specified, all days are assumed to have the same profile, defined by the parameter ``daily_demand_profile``.
    daily_demand_ratio_saturday : float, optional
        Ratio between the total daily demand on saturdays and the total daily demand on a week day.
    daily_demand_ratio_sunday : float, optional
        Ratio between the total daily demand on sundays and the total daily demand on a week day.
    peak_demand_ratio_saturday : float, optional
        Ratio between the peak demand on saturdays and the peak on a week day. If specified, this parameter overrides ``daily_demand_ratio_saturday``.
    peak_demand_ratio_sunday : float, optional
        Ratio between the peak demand on sundays and the peak on a week day. If specified, this parameter overrides ``daily_demand_ratio_sunday``..
    weekly_demand_factors : list of float, optional
        List of seven values defining the relative total daily demand of each day of the week, starting on monday. If specified, this parameter overrides the four "ratio" parameters just described.
    daily_demand_profiles : list of list of float, optional
        List of seven daily demand profiles; one for each day of the week, starting on monday see ``daily_demand_profile``. It must be specified along with ``weekly_demand_factors``.
    weekly_demand_profile : list of float, optional
        Demand profile encompassing an entire week. It is equivalent to concatenating seven daily demand profiles of the same length, where the values of all profiles have a comparable scale.
    op_start : str, optional
        Operation start time. It must be a string with the format "hh:mm", going from `"00:00"` to "23:30". The "minutes" part of the time (i.e. the string "mm") must be either "00" or "30". This parameter must be provided along with ``op_end``. Its use is and alternative to specifying demand profiles. It will be ignored if any of the parameters ``daily_demand_profile``, ``daily_demand_profiles``, or ``weekly_demand_profile`` is specified.
    op_end : str, optional
        Operation end time. It must be a string with the format "hh:mm", going from `"00:00"` to "23:30". The "minutes" part of the time (i.e. the string "mm") must be either "00" or "30". This parameter must be provided along with ``op_start``. Its use is and alternative to specifying demand profiles. It will be ignored if any of the parameters ``daily_demand_profile``, ``daily_demand_profiles``, or ``weekly_demand_profile`` is specified..
    op_start_saturday : str, optional
        DESCRIPTION.
    op_end_saturday : str, optional
        DESCRIPTION.
    op_start_sunday : str, optional
        DESCRIPTION.
    op_end_sunday : str, optional
        DESCRIPTION.
    monthly_production : list of float, optional
        DESCRIPTION.
    Tamb_profile : list of float, optional
        DESCRIPTION.
    Tamb_dependence : float, optional
        DESCRIPTION.
    smooth_Tamb_profile : bool, optional
        DESCRIPTION.
    year : int, optional
        DESCRIPTION.
    **kwargs : dict, optional
        DESCRIPTION.

    Attributes
    ----------
    ATTRIBUTE_NAME : TYPE
        DESCRIPTION.

    Notes
    -----
    NOTES, if needed.

    Examples
    --------
    EXAMPLES, if needed.
    """
    
    def __init__(
            
            self, 
            *,
            
            fluid: Optional[ str ] = None,
            fluid_cp: Optional[ float ] = None,
            fluid_density: Optional[ float ] = None,
            
            T_set: float | list[float],
            T_in: float | list[float],
            
            monthly_heat_demand: Optional[ list[float] ] = None,
            heat_demand_units: Optional[ str ] = None,
            
            monthly_consumption: Optional[ list[float] ] = None,
            consumption_units: Optional[ str ] = None,
            heater_efficiency: Optional[ float ] = None,
            heat_source: Optional[ str ] = None,
            heat_source_heating_value: Optional[ float ] = None,
            heat_source_density: Optional[ float ] = None,
            
            daily_demand_profile: Optional[ list[float] ] = None,
            daily_demand_profile_saturday: Optional[ list[float] ] = None,
            daily_demand_profile_sunday: Optional[ list[float] ] = None,
            
            daily_demand_ratio_saturday: Optional[ float ] = None,
            daily_demand_ratio_sunday: Optional[ float ] = None,
            peak_demand_ratio_saturday: Optional[ float ] = None,
            peak_demand_ratio_sunday: Optional[ float ] = None,
            
            weekly_demand_factors: Optional[ list[float] ] = None,
            
            daily_demand_profiles: Optional[ list[list[float]] ] = None,
            weekly_demand_profile: Optional[ list[float] ] = None,
            
            op_start: Optional[ str ] = None,
            op_end: Optional[ str ] = None,
            op_start_saturday: Optional[ str ] = None,
            op_end_saturday: Optional[ str ] = None,
            op_start_sunday: Optional[ str ] = None,
            op_end_sunday: Optional[ str ] = None,
            
            monthly_production: Optional[ list[float] ] = None,
            
            Tamb_profile: Optional[ list[float] ] = None,
            Tamb_dependence: Optional[ float ] = None,
            
            
            smooth_Tamb_profile: Optional[ bool ] = None,
            year: Optional[ int ] = None,
            
            **kwargs,
            
            ):
        
        
        
        self._monthly_T_set = self.validate_argument("T_set", T_set)
        self._monthly_T_in = self.validate_argument("T_in", T_in)
        if self._monthly_T_set is None or self._monthly_T_in is None:
            raise ValueError("Class DemandProfile: Arguments T_set and T_in must be provided.")
        
        self._fluid = self.validate_argument("fluid", fluid)
        if self._fluid == "WATER":
            self._fluid_cp = 4184
            self._fluid_density = 1000
        elif self._fluid == "AIR":
            self._fluid_cp = 1050
            self._fluid_density = 1.204
        elif self._fluid == "THERMINOL_66":
            self._fluid_cp = 2
            self._fluid_density = 920
        if fluid_cp is not None:
            self._fluid_cp = self.validate_argument("fluid_cp", fluid_cp)
        if fluid_density is not None:
            self._fluid_density = self.validate_argument("fluid_density", fluid_density)
            
        if self._fluid_cp is None or self._fluid_density is None:
            raise ValueError("Class DemandProfile: 'fluid_cp' and 'fluid_density' must be provided, either directly or indirectly through the working fluid's name." )
            
        if weekly_demand_profile is not None:
            weekly_demand_profile = self.validate_argument("weekly_demand_profile", weekly_demand_profile)
            self._weekly_demand_profile = self._extend_profile(weekly_demand_profile, 48*7)
            
        elif daily_demand_profiles is not None:
            self._daily_demand_profiles = self.validate_argument("daily_demand_profiles", daily_demand_profiles)
            self._weekly_demand_factors = self.validate_argument("weekly_demand_factors", weekly_demand_factors)
            self._week_constructor_1()
            
        elif daily_demand_profile is not None:
            
            self._daily_demand_profile = self.validate_argument("daily_demand_profile", daily_demand_profile)
            self._daily_demand_profile_saturday = self.validate_argument("daily_demand_profile_saturday", daily_demand_profile_saturday)
            self._daily_demand_profile_sunday = self.validate_argument("daily_demand_profile_sunday", daily_demand_profile_sunday)
            self._weekly_demand_factors = self.validate_argument("weekly_demand_factors", weekly_demand_factors)
            self._daily_demand_ratio_saturday = self.validate_argument("daily_demand_ratio_saturday", daily_demand_ratio_saturday)
            self._peak_demand_ratio_saturday = self.validate_argument("peak_demand_ratio_saturday", peak_demand_ratio_saturday)
            self._daily_demand_ratio_sunday = self.validate_argument("daily_demand_ratio_sunday", daily_demand_ratio_sunday)
            self._peak_demand_ratio_sunday = self.validate_argument("peak_demand_ratio_sunday", peak_demand_ratio_sunday)
            self._week_constructor_2()
            
        elif op_start is not None:
            
            self._op_start = self.validate_argument("op_start", op_start)
            self._op_end = self.validate_argument("op_end", op_end)
            self._op_start_saturday = self.validate_argument("op_start_saturday", op_start_saturday)
            self._op_end_saturday = self.validate_argument("op_end_saturday", op_end_saturday)
            self._op_start_sunday = self.validate_argument("op_start_sunday", op_start_sunday)
            self._op_end_sunday = self.validate_argument("op_end_sunday", op_end_sunday)
            self._weekly_demand_factors = self.validate_argument("weekly_demand_factors", weekly_demand_factors)
            self._daily_demand_ratio_saturday = self.validate_argument("daily_demand_ratio_saturday", daily_demand_ratio_saturday)
            self._peak_demand_ratio_saturday = self.validate_argument("peak_demand_ratio_saturday", peak_demand_ratio_saturday)
            self._daily_demand_ratio_sunday = self.validate_argument("daily_demand_ratio_sunday", daily_demand_ratio_sunday)
            self._peak_demand_ratio_sunday = self.validate_argument("peak_demand_ratio_sunday", peak_demand_ratio_sunday)
            self._week_constructor_3()
            
        else:
            self._weekly_demand_profile = [ [ 1 ]*48*7 ]
            
        if Tamb_dependence is not None:
            self._Tamb_dependence_mode = "manual"
            self._Tamb_dependence = self.validate_argument("Tamb_dependence", Tamb_dependence)
        else:
            self._Tamb_dependence_mode = "auto"
            
        self._monthly_heat_demand = self.validate_argument("monthly_heat_demand", monthly_heat_demand)
        if heat_demand_units is not None:
            self._heat_demand_units = self.validate_argument("heat_demand_units", heat_demand_units)
        else:
            warnings.warn("Class DemandProfile: 'monthly_heat_demand' argument was provided but no 'heat_demand_units'. Joule is assumed as default.")
            self._heat_demand_units = 'J'
                
        self._monthly_production = self.validate_argument("monthly_production", monthly_production)
        self._Tamb_profile = self.validate_argument("Tamb_profile", Tamb_profile)
            
        if smooth_Tamb_profile is not None:
            self._smooth_Tamb_profile = self.validate_argument( "smooth_Tamb_profile", smooth_Tamb_profile )
        else:
            self._smooth_Tamb_profile = True
            
        if year is not None:
            self._year = self.validate_argument( "year", year )
        else:
            self._year = default_year
            
        self.compute_yearly_profiles()
        
    @staticmethod
    def consumption_to_thermal_demand(
            
            energy_source_consumption,
            consumption_units,
            energy_source_name = None,
            goal_units = 'J',
            heater_efficiency = 1,
            HV_type = 'LHV',
            fuel_density = None,
            fuel_HV = None
            
            ):
        try:
            heater_efficiency = float( heater_efficiency )
            assert heater_efficiency > 0
        except:
            ValueError("DemandProfile.consumption_to_thermal_demand: heater_efficiency must be a value > 0 convertible to type 'float'.")
        if energy_source_name is not None:
            try:
                energy_source_name = str(energy_source_name)
                energy_source_name = energy_source_name.upper()
            except:
                raise ValueError("DemandProfile.consumption_to_thermal_demand: energy_source_name must be None or a variable convertible to string.")
        energy_source_unknown = energy_source_name is not None and ( not energy_source_name in Energy_Sources_Database )
        if energy_source_name == "ELECTRICITY":
            try:
                energy_source_consumption = float( energy_source_consumption )
                return heater_efficiency*convert_units(energy_source_consumption, consumption_units, goal_units)
            except:
                try:
                    energy_source_consumption = [ float(value) for value in energy_source_consumption ]
                    return heater_efficiency*convert_units(energy_source_consumption, consumption_units, goal_units)
                except:
                    raise ValueError("DemandProfile.consumption_to_thermal_demand: energy_source_consumption must be either a value convertible to float, or a list of values convertible to float.")
        if fuel_HV is not None and fuel_density is not None:
            try:
                fuel_HV = float( fuel_HV )
            except:
                raise ValueError("DemandProfile.consumption_to_thermal_demand: fuel_HV must be None or a value convertible to float.")
            try:
                fuel_density = float( fuel_density )
            except:
                raise ValueError("DemandProfile.consumption_to_thermal_demand: fuel_density must be None or a value convertible to float.")
        elif fuel_density is not None:
            try:
                fuel_density = float( fuel_density )
            except:
                raise ValueError("DemandProfile.consumption_to_thermal_demand: fuel_density must be None or a value convertible to float.")
            if energy_source_name is None:
                raise ValueError("DemandProfile.consumption_to_thermal_demand: Energy source not identified. Heating value must be provided manually.")
            elif energy_source_unknown:
                raise ValueError("DemandProfile.consumption_to_thermal_demand: Energy source name unknown. Heating value must be provided manually.")
            if not HV_type in [ 'LHV', 'HHV' ]:
                raise ValueError("DemandProfile.consumption_to_thermal_demand: HV_type must be one of the strings: 'LHV' and 'HHV'.")
            if HV_type == 'LHV':
                fuel_HV = Energy_Sources_Database[ energy_source_name ][ 'LHV' ]
            else:
                try:
                    fuel_HV = Energy_Sources_Database[ energy_source_name ][ 'HHV' ]
                except KeyError:
                    warnings.warn(f"DemandProfile.consumption_to_thermal_demand: No higher heating value registered for the fuel specified: {energy_source_name}. Using lower heating value instead.")
                    fuel_HV = Energy_Sources_Database[ energy_source_name ][ 'LHV' ]
        elif fuel_HV is not None:
            try:
                fuel_HV = float(fuel_HV)
            except:
                raise ValueError("DemandProfile.consumption_to_thermal_demand: fuel_HV must be None or a value convertible to float.")
            if energy_source_name is None or energy_source_unknown:
                try:
                    assert consumption_units in [ 'kg', 'ton', 'lb' ]
                except:
                    raise ValueError("DemandProfile.consumption_to_thermal_demand: Energy source unidentified. Density must either be provided, or consumption must be specified in mass units: 'kg', 'ton', 'lb'.")
                fuel_density = None
            else:
                fuel_density = Energy_Sources_Database[ energy_source_name ][ 'density' ]
        else:
            if not energy_source_name in Energy_Sources_Database:
                raise ValueError("DemandProfile.consumption_to_thermal_demand: Either a valid energy source must be provided, or heating value and density must be provided manually.")
            if not HV_type in [ 'LHV', 'HHV' ]:
                raise ValueError("DemandProfile.consumption_to_thermal_demand: HV_type must be one of the strings: 'LHV' and 'HHV'.")
            if HV_type == 'LHV':
                fuel_HV = Energy_Sources_Database[ energy_source_name ][ 'LHV' ]
            else:
                try:
                    fuel_HV = Energy_Sources_Database[ energy_source_name ][ 'HHV' ]
                except KeyError:
                    warnings.warn(f"DemandProfile.consumption_to_thermal_demand: No higher heating value registered for the fuel specified: {energy_source_name}. Using lower heating value instead.")
                    fuel_HV = Energy_Sources_Database[ energy_source_name ][ 'LHV' ]
            fuel_density = Energy_Sources_Database[ energy_source_name ][ 'density' ]
        
        try:
            energy_source_consumption = float( energy_source_consumption )
        except TypeError:
            try:
                energy_source_consumption = [ float(value) for value in energy_source_consumption ]
            except TypeError:
                raise ValueError("DemandProfile.consumption_to_thermal_demand: energy_source_consumption must be either a value convertible to float, or a list of values convertible to float.")
        
        if type( energy_source_consumption ) is float:
            if energy_source_consumption < 0:
                raise ValueError("DemandProfile.consumption_to_thermal_demand: energy_source_consumption must be >= 0.")
            try:
                energy_source_consumption = convert_units(energy_source_consumption, consumption_units, 'kg', density = fuel_density)
            except UnitConversionError:
                raise ValueError("DemandProfile.consumption_to_thermal_demand: Units provided are not valid.")
            return heater_efficiency*fuel_HV*energy_source_consumption
        
        elif type( energy_source_consumption ) is list:
            if any( [ value < 0 for value in energy_source_consumption ] ):
                raise ValueError("DemandProfile.consumption_to_thermal_demand: value within list energy_source_consumption must be >= 0.")
            try:
                energy_source_consumption = [ convert_units(value, consumption_units, 'kg', density = fuel_density) for value in energy_source_consumption  ]
            except UnitConversionError:
                raise ValueError("DemandProfile.consumption_to_thermal_demand: Units provided are not valid.")
            return [ heater_efficiency*fuel_HV*value for value in energy_source_consumption ]
        
        raise Exception("DemandProfile.consumption_to_thermal_demand: Unknown error.")
    
    def _week_constructor_1( self, ):
        
        daily_demand_profiles = self.get_attribute( "daily_demand_profiles" )
        weekly_demand_factors = self.get_attribute( "weekly_demand_factors" )
        
        if daily_demand_profiles is None or weekly_demand_factors is None:
            raise KeyError("Class DemandProfile: Arguments 'daily_demand_profiles' and 'weekly_demand_factors' are needed for constructor 2.")
        
        daily_demand_profiles = [ self._extend_profile( profile, 48 ) for profile in daily_demand_profiles  ]
        
        weekly_demand_profile = [  ]
        for i in range(len(daily_demand_profiles)):
            profile_sum = sum( daily_demand_profiles[i] )
            if profile_sum == 0:
                weekly_demand_profile = weekly_demand_profile + [ 0 ]*48
            else:
                scale_factor = weekly_demand_factors[i]
                weekly_demand_profile = weekly_demand_profile + [ scale_factor*value/profile_sum for value in daily_demand_profiles[i] ]
            
        self._weekly_demand_profile = weekly_demand_profile
            
    def _week_constructor_2(self):
        
        daily_demand_profile = self.get_attribute( "daily_demand_profile" )
        daily_demand_profile_saturday = self.get_attribute( "daily_demand_profile_saturday" )
        daily_demand_profile_sunday = self.get_attribute( "daily_demand_profile_sunday" )
        weekly_demand_factors = self.get_attribute( "weekly_demand_factors" )
        daily_demand_ratio_saturday = self.get_attribute( "daily_demand_ratio_saturday" )
        peak_demand_ratio_saturday = self.get_attribute( "peak_demand_ratio_saturday" )
        daily_demand_ratio_sunday = self.get_attribute( "daily_demand_ratio_sunday" )
        peak_demand_ratio_sunday = self.get_attribute( "peak_demand_ratio_sunday" )
        
        if daily_demand_profile is None:
            raise KeyError("Class DemandProfile: Argument 'daily_demand_profile' is needed for constructor 3.")
        daily_demand_profile = self._extend_profile(daily_demand_profile, 48)
        
        if daily_demand_profile_saturday is not None:
            special_profile_saturday = True
            daily_demand_profile_saturday = self._extend_profile(daily_demand_profile_saturday, 48)
        else:
            special_profile_saturday = False
            
        if daily_demand_profile_sunday is not None:
            special_profile_sunday = True
            daily_demand_profile_sunday = self._extend_profile(daily_demand_profile_sunday, 48)
        else:
            special_profile_sunday = False
        
        daily_demand_profiles = []
        for i in range(5):
            daily_demand_profiles.append( daily_demand_profile.copy() )
        
        if weekly_demand_factors is not None:
            if special_profile_saturday:
                daily_demand_profiles.append( daily_demand_profile_saturday.copy() )

                if ( not special_profile_sunday ) and weekly_demand_factors[6] > 0:
                    raise ValueError("Class DemandProfile: Condition not compatible: (1) special daily profile for saturday is provided, (2) no profile for sunday is provided, (3) factor for sunday in 'weekly demand factor' is greater than zero.")
                if special_profile_sunday:
                    daily_demand_profiles.append( daily_demand_profile_sunday.copy() )
                else:
                    daily_demand_profiles.append( [ 0 ]*48 )
            elif special_profile_sunday:
                daily_demand_profiles.append( daily_demand_profile.copy() )
                daily_demand_profiles.append( daily_demand_profile_sunday.copy() )
            else:
                daily_demand_profiles.append( daily_demand_profile.copy() )
                daily_demand_profiles.append( daily_demand_profile.copy() )
            self._daily_demand_profiles = daily_demand_profiles
            self._week_constructor_1()
            return
        
        weekly_demand_factors = [ 1 ]*5
        
        if special_profile_saturday:
            if daily_demand_ratio_saturday is None and peak_demand_ratio_saturday is None:
                raise ValueError("Class DemandProfile: Condition not compatible: A special daily demand profile was provided for saturday and no production factor was provided through (1) 'daily_demand_ratio_saturday', (2) 'peak_demand_ratio_saturday', or (3) 'weekly_demand_factors'.")
            if peak_demand_ratio_saturday is not None:
                if daily_demand_ratio_saturday is not None:
                    warnings.warn( "Class DemandProfile: Parameter 'daily_demand_ratio_saturday' overriden by 'peak_demand_ratio_saturday'." )
                daily_demand_ratio_saturday = self._peak_to_daily_demand_ratio(daily_demand_profile, daily_demand_profile_saturday, peak_demand_ratio_saturday)
            daily_demand_profiles.append( daily_demand_profile_saturday.copy() )
            weekly_demand_factors.append( daily_demand_ratio_saturday )
            if special_profile_sunday:
                if daily_demand_ratio_sunday is None and peak_demand_ratio_sunday is None:
                    raise ValueError("Class DemandProfile: Condition not compatible: A special daily demand profile was provided for sunday and no production factor was provided through (1) 'daily_demand_ratio_sunday', (2) 'peak_demand_ratio_sunday', or (3) 'weekly_demand_factors'.")
                if peak_demand_ratio_sunday is not None:
                    if daily_demand_ratio_sunday is not None:
                        warnings.warn( "Class DemandProfile: Parameter 'daily_demand_ratio_sunday' overriden by 'peak_demand_ratio_sunday'." )
                    daily_demand_ratio_sunday = self._peak_to_daily_demand_ratio(daily_demand_profile, daily_demand_profile_sunday, peak_demand_ratio_sunday)
                daily_demand_profiles.append( daily_demand_profile_sunday.copy() )
                weekly_demand_factors.append( daily_demand_ratio_sunday )       
            else:
                if daily_demand_ratio_sunday is not None and daily_demand_ratio_sunday > 0:
                    raise ValueError("Class DemandProfile: Condition not compatible: (1) special daily profile for saturday is provided, (2) no profile for sunday is provided, (3) argument 'daily_demand_ratio_sunday' is greater than zero.")
                elif peak_demand_ratio_sunday is not None and peak_demand_ratio_sunday > 0:
                    raise ValueError("Class DemandProfile: Condition not compatible: (1) special daily profile for saturday is provided, (2) no profile for sunday is provided, (3) argument 'peak_demand_ratio_sunday' is greater than zero.")
                daily_demand_profiles.append( [ 0 ]*48 )
                weekly_demand_factors.append( 0 )
        elif special_profile_sunday:
            daily_demand_profiles.append( daily_demand_profile.copy() )
            if daily_demand_ratio_saturday is not None:
                weekly_demand_factors.append( daily_demand_ratio_saturday )
            elif peak_demand_ratio_saturday is not None:
                weekly_demand_factors.append( peak_demand_ratio_saturday )
            else:
                weekly_demand_factors.append( 1 )
            if daily_demand_ratio_sunday is None and peak_demand_ratio_sunday is None:
                raise ValueError("Class DemandProfile: Condition not compatible: A special daily demand profile was provided for sunday and no production factor was provided through (1) 'daily_demand_ratio_sunday', (2) 'peak_demand_ratio_sunday', or (3) 'weekly_demand_factors'.")
            if peak_demand_ratio_sunday is not None:
                if daily_demand_ratio_sunday is not None:
                    warnings.warn( "Class DemandProfile: Parameter 'daily_demand_ratio_sunday' overriden by 'peak_demand_ratio_sunday'." )
                daily_demand_ratio_sunday = self._peak_to_daily_demand_ratio(daily_demand_profile, daily_demand_profile_sunday, peak_demand_ratio_sunday)
            daily_demand_profiles.append( daily_demand_profile_sunday.copy() )
            weekly_demand_factors.append( daily_demand_ratio_sunday )   
        else:
            daily_demand_profiles.append( daily_demand_profile.copy() )
            daily_demand_profiles.append( daily_demand_profile.copy() )
            if daily_demand_ratio_saturday is not None or peak_demand_ratio_saturday is not None:
                if peak_demand_ratio_saturday is not None:
                    if daily_demand_ratio_saturday is not None:
                        warnings.warn( "Class DemandProfile: Parameter 'daily_demand_ratio_saturday' overriden by 'peak_demand_ratio_saturday'." )
                    daily_demand_ratio_saturday = self._peak_to_daily_demand_ratio(daily_demand_profile, daily_demand_profile_saturday, peak_demand_ratio_saturday)
                weekly_demand_factors.append( daily_demand_ratio_saturday )
                if daily_demand_ratio_sunday is not None or peak_demand_ratio_sunday is not None:
                    if peak_demand_ratio_sunday is not None:
                        if daily_demand_ratio_sunday is not None:
                            warnings.warn( "Class DemandProfile: Parameter 'daily_demand_ratio_sunday' overriden by 'peak_demand_ratio_sunday'." )
                        daily_demand_ratio_sunday = self._peak_to_daily_demand_ratio(daily_demand_profile, daily_demand_profile_sunday, peak_demand_ratio_sunday)                    
                    weekly_demand_factors.append( daily_demand_ratio_sunday )
                else:
                    weekly_demand_factors.append( 0 )
            elif daily_demand_ratio_sunday is not None or peak_demand_ratio_sunday is not None:
                weekly_demand_factors.append( 1 )
                if peak_demand_ratio_sunday is not None:
                    if daily_demand_ratio_sunday is not None:
                        warnings.warn( "Class DemandProfile: Parameter 'daily_demand_ratio_saturday' overriden by 'peak_demand_ratio_saturday'." )
                    daily_demand_ratio_sunday = self._peak_to_daily_demand_ratio(daily_demand_profile, daily_demand_profile_sunday, peak_demand_ratio_sunday)
                weekly_demand_factors.append( daily_demand_ratio_sunday )
            else:
                weekly_demand_factors.append( 1 )
                weekly_demand_factors.append( 1 )
                
        self._daily_demand_profiles = daily_demand_profiles
        self._weekly_demand_factors = weekly_demand_factors
        self._week_constructor_1()
    
    def _week_constructor_3(self):
        
        op_start = self.get_attribute( "op_start" )
        op_end = self.get_attribute( "op_end" )
        op_start_saturday = self.get_attribute( "op_start_saturday" )
        op_end_saturday = self.get_attribute( "op_end_saturday" )
        op_start_sunday = self.get_attribute( "op_start_sunday" )
        op_end_sunday = self.get_attribute( "op_end_sunday" )
        weekly_demand_factors = self.get_attribute( "weekly_demand_factors" )
        peak_demand_ratio_saturday = self.get_attribute( "peak_demand_ratio_saturday" )
        daily_demand_ratio_saturday = self.get_attribute( "daily_demand_ratio_saturday" )
        peak_demand_ratio_sunday = self.get_attribute( "peak_demand_ratio_sunday" )
        daily_demand_ratio_sunday = self.get_attribute( "daily_demand_ratio_sunday" )
        
        if op_start is None or op_end is None:
            raise ValueError("Class DemandProfile: 'op_start' and 'op_end' are necessary for week constructor 3.")
        
        start_step_week = time_to_half_hours( op_start )
        end_step_week = time_to_half_hours( op_end )
        
        if start_step_week == end_step_week:
            raise ValueError("Class DemandProfile: 'op_end' must be different from 'op_start'.")
        
        if op_start_saturday is not None:
            
            if op_end_saturday is None:
                raise ValueError("Class DemandProfile: Argument 'op_end_saturday' must be provided along with 'op_start_saturday'.")
                
            start_step_saturday = time_to_half_hours( op_start_saturday )
            end_step_saturday = time_to_half_hours( op_end_saturday )
            
            
            if start_step_saturday == end_step_saturday:
                raise SHIPcalError("Class DemandProfile: Argument 'op_end_saturday' must be different from 'op_start_saturday'.")
                
            if op_start_sunday is not None:
                if op_end_sunday is None:
                    raise ValueError("Class DemandProfile: Argument 'op_end_sunday' must be provided along with 'op_start_sunday'.")
                    
                start_step_sunday = time_to_half_hours( op_start_sunday )
                end_step_sunday = time_to_half_hours( op_end_sunday )
                
                if start_step_sunday == end_step_sunday:
                    raise ValueError("Class DemandProfile: Argument 'op_end_sunday' must be different from 'op_start_sunday'.")
                    
            else:
                start_step_sunday = None
                end_step_sunday = None
            
        elif op_start_sunday is not None:
            
            start_step_saturday = start_step_week
            end_step_saturday = end_step_week
            
            if op_end_sunday is None:
                raise ValueError("Class DemandProfile: Argument 'op_end_sunday' must be provided along with 'op_start_sunday'.")
                
            start_step_sunday = time_to_half_hours( op_start_sunday)
            end_step_sunday = time_to_half_hours( op_end_sunday )
            
            if start_step_sunday == end_step_sunday:
                raise ValueError("Class DemandProfile: Argument 'op_end_sunday' must be different from 'op_start_sunday'.")
            
        else:
            
            start_step_saturday = start_step_week
            end_step_saturday = end_step_week
            
            start_step_sunday = start_step_week
            end_step_sunday = end_step_week
            
        daily_demand_profiles = [ [ 0 ]*48 for i in range( 7 ) ]
        
        # Function to compute the operation time based on the starting step and on the ending step
        # It return the number of "half hours" of operation, taking into account the possibility of 
        # operation from one day to another.
        def compute_operation_time( start_step, end_step ):
            if start_step < end_step:
                return end_step - start_step
            else:
                return 48 - start_step + end_step
        
        for day in range(7):
            
            if any( [ day == 6 and start_step_sunday is None,
                      day == 5 and start_step_saturday is None, 
                      day < 5 and start_step_week is None ] ):
                
                continue
            
            start_step = None
            end_step = None
            daily_demand_ratio = None
            peak_demand_ratio = None
            
            if day in [ 5, 6 ]:
                
                if day == 5:
                    start_step = start_step_saturday
                    end_step = end_step_saturday
                    daily_demand_ratio = daily_demand_ratio_saturday
                    peak_demand_ratio = peak_demand_ratio_saturday
                
                if day == 6:
                    start_step = start_step_sunday
                    end_step = end_step_sunday
                    daily_demand_ratio = daily_demand_ratio_sunday
                    peak_demand_ratio = peak_demand_ratio_sunday
                    
                if weekly_demand_factors is not None:
                    daily_demand_ratio = weekly_demand_factors[ day ]
                    peak_demand_ratio = daily_demand_ratio*compute_operation_time( start_step_week, end_step_week )/compute_operation_time(start_step, end_step)
                    
                elif peak_demand_ratio is None:
                    
                    if daily_demand_ratio is not None:
                        peak_demand_ratio = daily_demand_ratio*compute_operation_time( start_step_week, end_step_week )/compute_operation_time(start_step, end_step)
                        
                    else:
                        peak_demand_ratio = 1
                
            else:
                start_step = start_step_week
                end_step = end_step_week
                if weekly_demand_factors is not None:
                    daily_demand_ratio = weekly_demand_factors[ day ]
                    peak_demand_ratio = daily_demand_ratio
                else:
                    peak_demand_ratio = 1
                
            if start_step < end_step:
                daily_demand_profiles[ day ][ start_step : end_step ] = [ peak_demand_ratio ]*( end_step - start_step )
            else:
                if day == 6:
                    daily_demand_profiles[ day ][ start_step : 48 ] = [ peak_demand_ratio ]*( 48 - start_step )
                    daily_demand_profiles[ 0 ][ :end_step ] = [ peak_demand_ratio ]*end_step
                else:
                    daily_demand_profiles[ day ][ start_step : 48 ] = [ peak_demand_ratio ]*( 48 - start_step )
                    daily_demand_profiles[ day + 1 ][ :end_step ] = [ peak_demand_ratio ]*end_step
        
        self._weekly_demand_profile = list( np.concatenate( daily_demand_profiles ).astype(float) )
    
    @staticmethod
    def validate_argument(argument_name, value):
        
        if type(argument_name) is not str:
            raise ValueError("DemandProfile.validate_attribute: Argument 'argument_name' must be a string.")
        
        if not argument_name in DemandProfile_accepted_args:
            raise TypeError(f"Class DemandProfile: Unexpected argument name: {argument_name}")
        
        if value is None:
            return None
            
        if argument_name in [ "op_start",
                              "op_end",
                              "op_start_saturday",
                              "op_end_saturday",
                              "op_start_sunday",
                              "op_end_sunday" ]:
            try:
                assert type(value) is str and ':' in value
                hours = int( value.split(':')[0] )
                minutes = int( value.split(':')[1] )
                assert hours >= 0 and hours <= 24 and minutes in [0, 30] and not (hours == 24 and minutes == 30)
            except:
                raise ValueError(f"Class DemandProfile: {argument_name} must be a string with format 'hh:mm', with 'hh' from '00' to '24' and 'mm' equal to '00' or '30'. '24:30' is not allowed.")
        
        if argument_name in [
                "T_in_profile",
                "T_set_profile",
                "flowrate_profile" ]:
            try:
                value = list(value)
                assert len(value) == 8760*60
                value = [ float(v) for v in value ]
                assert all( [ v >=  0 for v in value ] )
            except:
                raise ValueError(f"Class DemandProfile: {argument_name} must be a list of values convertible to type 'float', with length {8760*60}. The values must be >= 0.")
        
        if argument_name in [
                "peak_demand_ratio_saturday",
                "peak_demand_ratio_sunday",
                "daily_demand_ratio_saturday",
                "daily_demand_ratio_sunday" ]:
            try:
                value = float(value)
                assert value >= 0
            except:
                raise ValueError(f"Class DemandProfile: {argument_name} must be a value >= 0 convertible to type 'float'.")
                
        if argument_name in [
                "daily_demand_profile",
                "daily_demand_profile_saturday",
                "daily_demand_profile_sunday" ]:
            
            try:
                value = list(value)
                assert len( value ) in [1,2,3,4,6,8,12,24,48]
                value = [ float( v ) for v in value ]
                assert all( [ v >= 0 for v in value ] )
            except:
                raise ValueError(f"Class DemandProfile: {argument_name} must be a list of values >= 0 convertible to type 'float'. Its length must be within the values: 1, 2, 3, 4, 6, 8, 12, 24, and 48.")
        
        if argument_name == "daily_demand_profiles":
            
            try:
                value = list(value)
                assert len( value ) == 7
                value = [ list( profile ) for profile in value ]
            except:
                raise ValueError("Class DemandProfile: Argument 'daily_demand_profiles' must be a list of seven lists." )
            
            try:
                value = [ [ float( v ) for v in profile ] for profile in value ]
            except:
                raise ValueError("Class DemandProfile: The values inside the lists inside 'daily_demand_profiles' must be convertible to type 'float'." )
                
            try:
                assert len( value[ 0 ] ) in [ 1, 2, 3, 4, 6, 8, 12, 24, 48 ] and all( [ len( value[ i ] ) == len( value[ 0 ] ) for i in range( 1, len( value ) ) ] )
            except:
                raise ValueError("Class DemandProfile: The lists within the list 'daily_demand_profiles' must have a length within the allowed values: 1, 2, 3, 4, 6, 8, 12, 24, and 48. All lists must have the same length." )
            
            try:
                assert all( [ all( [ v >= 0 for v in profile ] ) ] for profile in value )
                assert sum( [ sum( profile ) for profile in value ] ) > 0
            except:
                raise ValueError("Class DemandProfile: All values within the argument 'daily_demand_profiles' must be >= 0. At least one of the values must be larger than zero.")
        
        if argument_name == "weekly_demand_profile":
            
            try:
                value = list(value)
                value = [ float( v ) for v in value ]
                assert (48*7)%len(value) == 0
            except:
                raise ValueError("Class DemandProfile: Argument '' must be a list of values convertible to type 'float', whose length must be a divisor of 336, or 336 itself.")
        
        if argument_name == "fluid":
            
            try:
                assert type(value) is str
            except:
                raise ValueError("Class DemandProfile: Argument 'fluid' must be a string.")
            try:
                value = value.upper()
                assert value in [ "WATER", "W", "AIR", "THERMINOL 66", "THERMINOL_66", "THERMINOL66" ]
            except:
                raise ValueError("Class DemandProfile: Invalid 'fluid' name.")
                
            if value in ["WATER", "W"]:
                value = "WATER"
            elif value in [ "THERMINOL 66", "THERMINOL_66", "THERMINOL66" ]:
                value = "THERMINOL_66"
        
        if argument_name == "fluid_cp":
            
            try:
                value = float(value)
                assert value > 500
            except:
                raise ValueError("Class DemandProfile: Argument 'fluid_cp' must be a value > 500 convertible to string.")
        
        if argument_name in [ "fluid_density",
                              "fuel_density", ]:
            
            try:
                value = float(value)
                assert value > 0.5
            except:
                raise ValueError("Class DemandProfile: Argument 'fluid_density' must be a value > 0.5 convertible to string.")
        
        if argument_name == "pressure":
            
            try:
                value = float(value)
                assert value > 0
            except:
                raise ValueError("Class DemandProfile: Argument 'pressure' must be a value > 0 convertible to type 'float'.")
                
        if argument_name == "weekly_demand_factors":
            
            try:
                value = list(value)
                assert len(value) == 7
                value = [ float(v) for v in value ]
                assert all([ v >= 0 for v in value ]) and sum(value) > 0
            except:
                raise ValueError("Class DemandProfile: Argument 'weekly_demand_factors' must be a list of values convertible to type 'float', all of which must be >= 0. At least one of them must be > 0.")
        
        if argument_name in [
                "monthly_heat_demand",
                "monthly_hot_fluid_demand",
                "monthly_consumption",
                "monthly_production",
                ]:
            try:
                value = list(value)
                assert len(value) == 12
                value = [ float(v) for v in value ]
                assert all([ v >= 0 for v in value ]) and sum(value) > 0
            except:
                raise ValueError(f"Class DemandProfile: {argument_name} must be a list of values convertible to type 'float', all of which must be >= 0. At least one of them must be > 0.")
        
        if argument_name == "normalize_daily_demand":
            
            try:
                assert type(value) is bool
            except:
                raise ValueError("Class DemandProfile: Argument 'normalize_daily_demand' must be a boolean value.")
                
        if argument_name in [ "T_set", "T_in" ]:
            temp_limits = [ [ 25, 150 ], [ 2,130 ] ][ [ "T_set", "T_in" ].index( argument_name ) ]
            try:
                value = float(value)
                assert value >= temp_limits[0] and value <= temp_limits[1]
                value = [ value ]*12
            except TypeError:
                try:
                    value = list(value)
                    value = [ float(v) for v in value ]
                    assert all([ v >= temp_limits[0] and v <= temp_limits[1] for v in value ])
                except:
                    raise ValueError(f"Class DemandProfile: {argument_name} must be a numeric value in the range {temp_limits[0]} <= T <= {temp_limits[1]}, or a list of 12 values in the same range.")
            except AssertionError:
                raise ValueError(f"Class DemandProfile: {argument_name} must be a numeric value in the range {temp_limits[0]} <= T <= {temp_limits[1]}, or a list of 12 values in the same range.")
                
        if argument_name == "Tamb_dependence":
            if ( not callable(value) ) or value is None or value == "auto":
                try:
                    value = float(value)
                    assert value >= 0 and value <= 3
                except:
                    raise ValueError("Class DemandProfile: Tamb_dependence must be either a callable function, a numeric value between 0 and 3, the string 'auto', or None.")
        
        if argument_name == "Tamb_dependence_mode":
            
            try:
                assert type(value) is str and value in [ "manual", "auto" ]
            except:
                raise ValueError("Class DemandProfile: Argument 'Tamb_dependence_mode' must be one of the strings: 'manual' or 'auto'.")
        
        if argument_name == "Tamb_profile":
            try:
                value = list(value)
                value = [ float(v) for v in value ]
                assert all([ v >= -50 and v <= 60 for v in value ])
                assert len( value ) == 365 or len( value )%365 == 0
            except:
                raise ValueError("Class DemandProfile: Tamb_profile must be a list of numberic values between -50 and 60, whose length must be equal to 365 or a multiple of that number.")
        
        if argument_name == "heat_demand_units":
            try:
                assert type(value) is str and value in [ "J", "kWh", "MWh", "BTU", "kBTU", "MBTU", "kJ", "MJ", "TJ" ]
            except:
                raise ValueError("Class DemandProfile: heat_demand_units must be a string within the accepted values: 'J', 'kWh', 'MWh', 'BTU', 'kBTU', 'MBTU', 'kJ', 'MJ', 'TJ'.")
        
        if argument_name == "smooth_Tamb_profile":
            
            try:
                assert type(value) is bool
            except:
                raise ValueError("Class DemandProfile: smooth_Tamb_profile must be a boolean value.")
                
        if argument_name == "year":
            
            try:
                value = int(value)
                assert value >= 2000 and value <= 2050
            except:
                raise ValueError("Class DemandProfile: Argument 'year' must be a numberic value convertible to type 'int'. It must be >= 2000 and <= 2050.")
        
        if argument_name == "heat_source":
            try:
                value = str(value)
            except:
                raise ValueError("Class DemandProfile: Argument 'heat_source' must be convertible to string.")
            
            value = value.upper()
            if not value in Energy_Sources_Database:
                raise ValueError("Class DemandProfile: Non-valid argument 'heat_source'.")
                
        if argument_name == "consumption_units":
            try:
                value = str(value)
            except:
                raise ValueError("Class DemandProfile: Argument 'consumption_units' must be convertible to string.")
                
            if not value in [ "J", "kWh", "MWh", "BTU", "kBTU", "MBTU", "kJ", "MJ", "TJ",
                              "kg", "ton", "lb", "m3", "L", "gal", "ft3" ]:
                raise ValueError("Class DemandProfile: Argument 'consumption_units' not valid. For electricity, valid units are:  'J', 'kWh', 'MWh', 'BTU', 'kBTU', 'MBTU', 'kJ', 'MJ', 'TJ'. For other fuels: 'kg', 'ton', 'lb', 'm3', 'L', 'gal', 'ft3'.")
        
        if argument_name == "heater_efficiency":
            try:
                value = float(value)
            except:
                raise ValueError("Class DemandProfile: Argument 'heater_efficiency' must be convertible to type 'float'.")
            if value <= 0:
                raise ValueError("Class DemandProfile: Argument 'heater_efficiency' must be > 0.")
        
        if argument_name == "heat_source_heating_value":
            try:
                value = float(value)
            except:
                raise ValueError("Class DemandProfile: Argument 'heat_source_heating_value' must be convertible to type 'float'.")
            if value <= 0:
                raise ValueError("Class DemandProfile: Argument 'heat_source_heating_value' must be > 0.")
                
        if argument_name == "heat_source_density":
            try:
                value = float(value)
            except:
                raise ValueError("Class DemandProfile: Argument 'heat_source_density' must be convertible to type 'float'.")
            if value <= 0:
                raise ValueError("Class DemandProfile: Argument 'heat_source_density' must be > 0.")
        
        return value
        
    @staticmethod
    def open_profiles_app():
        profiles_app.launch()
        
    @staticmethod
    def _extend_profile( profile, desired_length ):
        
        if not ( desired_length >= len( profile ) ):
            raise ValueError("DemandProfile._extend_profile: Profile to extend is longer than the desired length.")
        if not ( desired_length%len(profile) == 0 ):
            raise ValueError("DemandProfile._extend_profile: Desired length is not divisible by the length of the profile.")
        
        if desired_length == len( profile ):
            return profile.copy()
        
        extension_factor = desired_length//len(profile)
        return np.concatenate( [ [ value ]*extension_factor for value in profile ] ).astype(float).tolist()
    
    @staticmethod
    def _reduce_profile( profile, desired_length ):
        
        if not ( desired_length <= len( profile ) ):
            raise ValueError("DemandProfile._reduce_profile: Profile to reduce is shorter than the desired length.")
        if not ( len(profile)%desired_length == 0 ):
            raise ValueError("DemandProfile._reduce_profile: The length of the profile is not divisible by the desired length .")
        
        if desired_length == len( profile ):
            return profile.copy()
        
        avg_window_size = len( profile )//365
        return [ float( np.mean( profile[ index : index + avg_window_size ] ) ) for index in range( 0, len( profile ), avg_window_size ) ]
    
    @staticmethod
    def _peak_to_daily_demand_ratio( base_profile, special_profile, peak_demand_ratio ):
        
        assert all( [ value >= 0 for value in base_profile ] )
        assert all( [ value >= 0 for value in special_profile ] )
        
        assert sum( base_profile ) > 0
        assert sum( special_profile ) > 0 or peak_demand_ratio == 0
        
        if peak_demand_ratio == 0:
            return 0
        
        special_profile = special_profile.copy()
        
        maxs_ratio = max( base_profile )/max( special_profile )
        
        special_profile = [ maxs_ratio*peak_demand_ratio*value for value in special_profile ]
        
        return sum( special_profile )/sum( base_profile )
    
    @classmethod
    def from_dict( cls, kwargs ):
        return cls(**kwargs)

    def get_attribute(self, attribute_name):
        return getattr(self, "_" + attribute_name, None)
    
    @staticmethod
    def define_temp_to_factor_func(dependence_coeff):
        """
        Function that takes a numeric value from 0 two 3 (both limits as well as non-integer values are allowed), and returns another function, which computes a scalar factor to take into account the dependence of thermal demand on ambient temperature.
        
        The value taken by this function could be interpreted as a 'dependece coefficient' of the thermal demand on the daily average ambient temperature.
        
        The function returned takes average daily temperature values (in C) and returns a scalar factor that is more dependent on temperature for higher dependece coefficients.
    
        Parameters
        ----------
        dependence_coeff : int or float
            Value from 0 to 3. Both limits are valid.
    
        Returns
        -------
        func
            DESCRIPTION.
    
        """
        try:
            dependence_coeff = float(dependence_coeff)
        except:
            raise SHIPcalError("Function: define_temp_to_factor_func: Parameter 'dependence_coeff' must be convertible to type 'float'.")
        try:
            assert dependence_coeff >= 0 and dependence_coeff <= 3
        except:
            raise SHIPcalError("Function: define_temp_to_factor_func: Parameter 'dependence_coeff' must be larger than or equal to 0, and smaller than or equal to 3.")
        
        if dependence_coeff.is_integer():
            
            dependence_coeff = int(dependence_coeff)
            T_hl = demand_cluster_coefficients[dependence_coeff]["T_hl"]
            m_h = demand_cluster_coefficients[dependence_coeff]["m_h"]
            b_h = demand_cluster_coefficients[dependence_coeff]["b_h"]
            m_w = demand_cluster_coefficients[dependence_coeff]["m_w"]
            b_w = demand_cluster_coefficients[dependence_coeff]["b_w"]
            
            def temp_to_factor(T):
                if T >= T_hl:
                    return m_w*T + b_w
                return m_h*T + b_h
        
        else:
            
            dependence_coeff_1 = int(dependence_coeff)
            dependence_coeff_2 = dependence_coeff_1 + 1
            
            x_1 = dependence_coeff_2 - dependence_coeff
            
            T_hl_1 = demand_cluster_coefficients[dependence_coeff_1]["T_hl"]
            m_h_1 = demand_cluster_coefficients[dependence_coeff_1]["m_h"]
            b_h_1 = demand_cluster_coefficients[dependence_coeff_1]["b_h"]
            m_w_1 = demand_cluster_coefficients[dependence_coeff_1]["m_w"]
            b_w_1 = demand_cluster_coefficients[dependence_coeff_1]["b_w"]
            
            T_hl_2 = demand_cluster_coefficients[dependence_coeff_2]["T_hl"]
            m_h_2 = demand_cluster_coefficients[dependence_coeff_2]["m_h"]
            b_h_2 = demand_cluster_coefficients[dependence_coeff_2]["b_h"]
            m_w_2 = demand_cluster_coefficients[dependence_coeff_2]["m_w"]
            b_w_2 = demand_cluster_coefficients[dependence_coeff_2]["b_w"]
            
            def temp_to_factor_1(T):
                if T >= T_hl_1:
                    return m_w_1*T + b_w_1
                return m_h_1*T + b_h_1
            
            def temp_to_factor_2(T):
                if T >= T_hl_2:
                    return m_w_2*T + b_w_2
                return m_h_2*T + b_h_2
            
            def temp_to_factor(T):
                return x_1*temp_to_factor_1(T) + (1 - x_1)*temp_to_factor_2(T)
            
        return temp_to_factor
    
    def determine_Tamb_dependence(self, Tamb_profile = None):
        
        needed_attributes = [
            "monthly_heat_demand"
            ]
        
        if Tamb_profile is None:
            needed_attributes.append( "Tamb_profile" )
        
        try:
            for attribute in needed_attributes:
                assert hasattr( self, "_" + attribute )
        except:
            warnings.warn("Class DemandProfile: Ambient temperature dependence could not be compute due to lack of data.")
            return 0
        
        if Tamb_profile is None:
            Tamb_profile = self.get_attribute( "Tamb_profile" )
        monthly_energy_demand = self.get_attribute( "monthly_heat_demand" )
        monthly_production = self.get_attribute( "monthly_production" )
        epsilon_fraction = self.get_attribute( "epsilon_fraction" )
        
        if epsilon_fraction is None:
            epsilon_fraction = 0.1
            
        if monthly_production is None:
            monthly_production = month_days
            epsilon_fraction = 0
            
        Tamb_profile = self._reduce_profile(Tamb_profile, 365)
            
        epsilon = epsilon_fraction*float(np.mean(monthly_production))
            
        monthly_normalized_demand = [ monthly_energy_demand[i]/(monthly_production[i] + epsilon ) for i in range(len(monthly_energy_demand)) ]
        total_normalized_demand = sum(monthly_normalized_demand)
        
        def mse_result( coeff_list ):
            
            temp_to_factor = self.define_temp_to_factor_func( coeff_list[0] )
            daily_factors = [ temp_to_factor(Tamb_profile[i]) for i in range(len(Tamb_profile)) ]
            sum_daily_factors = sum(daily_factors)
            assert sum_daily_factors > 0
            predicted_normalized_demand = [ total_normalized_demand*sum( daily_factors[ monthly_cummulated_days[month] : monthly_cummulated_days[month + 1] ] )/sum_daily_factors for month in range(12) ]
            return mean_squared_error(monthly_normalized_demand, predicted_normalized_demand)
        
        boundaries = Bounds(lb = [0], ub = [3])
        
        solving_success = False
        for method in [
                
                'Nelder-Mead',
                'Powell',
                'CG',
                'BFGS',
                'Newton-CG',
                'L-BFGS-B',
                'TNC',
                'COBYLA',
                'COBYQA',
                'SLSQP',
                'trust-constr',
                'dogleg',
                'trust-ncg',
                'trust-exact',
                'trust-krylov', ]:
            
            try:
                minimize_result = minimize(mse_result, [0.5], method = method, bounds = boundaries)
            except:
                continue
            
            if minimize_result['success']:
                solving_success = True
                break
        
        if not solving_success:
            raise SHIPcalError("DemandProfile.determine_Tamb_dependence: It was not possible to solve the minimization problem.")
            
        dependence_coeff = float (minimize_result['x'][0])
        
        self._Tamb_dependence = dependence_coeff
    
    def compute_yearly_profiles(self):
        
        attributes_needed = [
            "monthly_T_set",
            "monthly_T_in",
            "monthly_heat_demand",
            "weekly_demand_profile",
            "Tamb_dependence_mode",
            "fluid_cp",
            "smooth_Tamb_profile",
            "year",
        ]
        
        for attribute in attributes_needed:
            if self.get_attribute( attribute ) is None:
                raise ValueError(f"DemandProfile.compute_yearly_profiles: Class instance does not have the needed attribute: {attribute}")
        
        monthly_Tset = self.get_attribute( "monthly_T_set"  )
        monthly_Tin = self.get_attribute( "monthly_T_in"  )
        monthly_heat_demand = self.get_attribute( "monthly_heat_demand"  )
        weekly_demand_profile = self.get_attribute( "weekly_demand_profile"  )
        Tamb_dependence = self.get_attribute( "Tamb_dependence"  )
        Tamb_dependence_mode = self.get_attribute( "Tamb_dependence_mode" )
        Tamb_profile = self.get_attribute( "Tamb_profile"  )
        fluid_cp = self.get_attribute( "fluid_cp"  )
        smooth_Tamb_profile = self.get_attribute( "smooth_Tamb_profile" )
        starting_week_day = datetime(self.get_attribute( "year" ), 1, 1).weekday()
        heat_demand_units = self.get_attribute( "heat_demand_units" )
        
        if heat_demand_units is not None:
            monthly_heat_demand = [ convert_units(value, heat_demand_units, 'J') for value in monthly_heat_demand ]
        
        if Tamb_profile is None:
            warnings.warn("Class DemandProfile: Attribute 'Tamb_profile' has not been defined. The dependence of demand on ambient temperature will not be considered.")
        else:
            Tamb_profile = self._reduce_profile(Tamb_profile, 365)
            
            if smooth_Tamb_profile:
                Tamb_profile_smoothed = []
                for i in range( len( Tamb_profile ) ):
                    if i == 0:
                        Tamb_profile_smoothed.append( Tamb_profile[i] )
                    elif i == 1:
                        Tamb_profile_smoothed.append( ( Tamb_profile[i] + 0.5*Tamb_profile[ i - 1 ] )/( 1 + 0.5 ) )
                    elif i == 2:
                        Tamb_profile_smoothed.append( ( Tamb_profile[i] + 0.5*Tamb_profile[ i - 1 ] + 0.25*Tamb_profile[ i - 2 ] )/( 1 + 0.5 + 0.25 ) )
                    else:
                        Tamb_profile_smoothed.append( ( Tamb_profile[i] + 0.5*Tamb_profile[ i - 1 ] + 0.25*Tamb_profile[ i - 2 ] + 0.125*Tamb_profile[ i - 3 ] )/( 1 + 0.5 + 0.25 + 0.125 ) )
                        
                Tamb_profile = Tamb_profile_smoothed
            
            if Tamb_dependence_mode == "auto":
                self.determine_Tamb_dependence( Tamb_profile )
                Tamb_dependence = self._Tamb_dependence
                temp_to_factor = self.define_temp_to_factor_func(Tamb_dependence)
        
            else:
                if callable(Tamb_dependence):
                    temp_to_factor = Tamb_dependence
                elif type(Tamb_dependence) is float:
                    temp_to_factor = self.define_temp_to_factor_func(Tamb_dependence)
                else:
                    assert Tamb_dependence is None
                    def temp_to_factor(T):
                        return 1
        
        demanded_power_profile = []
        flowrate_profile = []
        T_in_profile = []
        T_set_profile = []
        
        for month in range(12):
            demand_this_month = monthly_heat_demand[month]
            delta_h_this_month = fluid_cp*( monthly_Tset[month] - monthly_Tin[month] )
            
            factors = []
            for day in range(monthly_cummulated_days[month], monthly_cummulated_days[month + 1]):
                week_day = (day + starting_week_day)%7
                daily_demand_profile = weekly_demand_profile[ week_day*48 : ( week_day + 1 )*48 ]
                if Tamb_profile is None:
                    temp_factor = 1
                else:
                    temp_factor = temp_to_factor(Tamb_profile[day])
                for half_hour_n in range(len(daily_demand_profile)):
                    factors.append(temp_factor*daily_demand_profile[half_hour_n])
            total_factor = sum(factors)
            if total_factor <= 0:
                raise SHIPcalError(f"compute_minutal_demand_profiles: sum of scaling factors is negative or equal to zero for the following month: {month_names[month]}. Check the temperature dependence provided.")
            for n in range(len(factors)):
                energy = demand_this_month*factors[n]/total_factor
                power = energy/1800
                flowrate = power/delta_h_this_month
                demanded_power_profile.append( power )
                flowrate_profile.append(flowrate)
                T_in_profile.append( monthly_Tin[month] )
                T_set_profile.append( monthly_Tset[month] )
        
        flowrate_profile = np.concatenate( [ [value]*30 for value in flowrate_profile ] ).astype(float).tolist() 
        demanded_power_profile = np.concatenate( [ [value]*30 for value in demanded_power_profile ] ).astype(float).tolist() 
        T_in_profile = np.concatenate( [ [value]*30 for value in T_in_profile ] ).astype(float).tolist() 
        T_set_profile = np.concatenate( [ [value]*30 for value in T_set_profile ] ).astype(float).tolist() 
                
        assert len(flowrate_profile) == 525600
        assert len(demanded_power_profile) == 525600
        assert len( T_in_profile ) == 525600
        assert len( T_set_profile ) == 525600
        
        minutes_per_day = 60*24
        self._flowrate_profile = [ flowrate_profile[ init_minute : init_minute + minutes_per_day ] for init_minute in range( 0, len( flowrate_profile ), minutes_per_day ) ]
        self._demanded_power_profile = [ demanded_power_profile[ init_minute : init_minute + minutes_per_day ] for init_minute in range( 0, len( demanded_power_profile ), minutes_per_day ) ]
        self._T_in_profile = [ T_in_profile[ init_minute : init_minute + minutes_per_day ] for init_minute in range( 0, len( T_in_profile ), minutes_per_day ) ]
        self._T_set_profile = [ T_set_profile[ init_minute : init_minute + minutes_per_day ] for init_minute in range( 0, len( T_set_profile ), minutes_per_day ) ]
    
    def _return_single_instant(self, month, day, hour, minute ):
        
        day_number = monthly_cummulated_days[ month - 1 ] + day - 1
        minute_number = hour*60 + minute
        
        flowrate = self._flowrate_profile[ day_number ][ minute_number ]
        demanded_power = self._demanded_power_profile[ day_number ][ minute_number ]
        T_in = self._T_in_profile[ day_number ][ minute_number ]
        T_set = self._T_set_profile[ day_number ][ minute_number ]
        
        return flowrate, demanded_power, T_in, T_set
    
    def _return_lists_from_date_range(self, date_range ):
        
        assert type( date_range ) is pd.DatetimeIndex
        
        flowrate_list = []
        demanded_power_list = []
        T_in_list = []
        T_set_list = []
        
        for dt in date_range:
            flowrate, demanded_power, T_in, T_set = self._return_single_instant(dt.month, dt.day, dt.hour, dt.minute)
            
            flowrate_list.append( flowrate )
            demanded_power_list.append( demanded_power )
            T_in_list.append( T_in )
            T_set_list.append( T_set )
        
        return flowrate_list, demanded_power_list, T_in_list, T_set_list
    
    def get_demand_conditions(self, *args, **kwargs ):
        
        if "flowrate_units" in kwargs:
            def convert_flowrate(flowrate):
                return convert_units(flowrate, 'kg/s', kwargs[ "flowrate_units" ],  density = self.get_attribute( "fluid_density" ))
        else:
            convert_flowrate = lambda flowrate: flowrate
        
        if "power_units" in kwargs:
            def convert_power(power):
                return convert_units(power, 'W', kwargs[ "power_units" ])
        else:
            convert_power = lambda power: power
        
        if "temp_units" in kwargs or "T_units" in kwargs:
            if "temp_units" in kwargs:
                temp_units = kwargs[ "temp_units" ]
            else:
                temp_units = kwargs[ "T_units" ]
            def convert_temp(T):
                return convert_units(T, 'C', temp_units)
        else:
            convert_temp = lambda T: T
        
        if len( args ) == 0 or ( len( args ) == 1 and type( args[0] ) is not pd.DatetimeIndex ):
            
            if len( args ) == 0:
                if not ("month" in kwargs and "day" in kwargs and "hour" in kwargs and "minute" in kwargs):
                    raise KeyError("DemandPorfile.get_demand_conditions: If no datetime is provided, the keyword arguments 'month', 'day', 'hour', and 'minute' must be provided.")
                month = kwargs[ "month" ]
                day = kwargs[ "day" ]
                hour = kwargs[ "hour" ]
                minute = kwargs[ "minute" ]
                
            else:
            
                dt = args[0]
                
                if type(dt) is dict:
                    dt = SimpleNamespace( **dt )
                
                if not all([ hasattr( dt, attribute ) for attribute in [ "month", "day", "hour", "minute" ] ] ):
                    raise ValueError("DemandProfile.get_demand_conditions: Unable to extract elements 'month', 'day', 'hour' and 'minute' from input.")
                month = int(dt.month)
                day = int(dt.day)
                hour = int(dt.hour)
                minute = int(dt.minute)
            
            flowrate, demanded_power, T_in, T_set = self._return_single_instant(month, day, hour, minute)
            
            return {
                
                'flowrate': convert_flowrate(flowrate),
                'demanded_power': convert_power(demanded_power),
                'T_in': convert_temp(T_in),
                'T_set': convert_temp(T_set),
                
                }
        
        elif type( args[0] ) is pd.DatetimeIndex or len( args ) == 2:
            
            if type( args[0] ) is pd.DatetimeIndex:
            
                if len( args ) != 1:
                    raise ValueError("DemandProfile.get_demand_conditions: Only one positional argument must be provided if the first argument is a pandas.DatetimeIndex object.")
            
                date_range = args[ 0 ]
                
            else:
                
                if "inlcusive" in kwargs:
                    inclusive = kwargs[ "inclusive" ]
                else:
                    inclusive = 'both'
                    
                if "freq" in kwargs:
                    freq = kwargs[ "freq" ]
                else:
                    freq = "min"
                    
                if "tz" in kwargs:
                    tz = kwargs[ "tz" ]
                else:
                    tz = None

                try:
                    date_range = pd.date_range( args[0], args[1], freq = freq, tz = tz, inclusive = inclusive )
                except:
                    raise ValueError("DemandProfile.get_demand_conditions: No pandas.DatetimeIndex could be generated from the two positional arguments provided.")
                
            flowrate_list, demanded_power_list, T_in_list, T_set_list = self._return_lists_from_date_range( date_range )
            
            flowrate_list = [ convert_flowrate( flowrate ) for flowrate in flowrate_list ]
            demanded_power_list = [ convert_power( power ) for power in demanded_power_list ]
            T_in_list = [ convert_temp( T ) for T in T_in_list ]
            T_set_list = [ convert_temp( T ) for T in T_set_list ]
            
            df = pd.DataFrame.from_dict( {
                
                "timestamp": date_range,
                "flowrate": flowrate_list,
                "demanded_power": demanded_power_list,
                "T_in": T_in_list,
                "T_set": T_set_list,
                
                }
                
            )
            
            return df
        
        else:
            raise ValueError("DemandProfile.get_demand_conditions: Incorrect arguments.")