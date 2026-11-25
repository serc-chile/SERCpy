# -*- coding: utf-8 -*-
"""
Created on Mon Aug 17 11:18:03 2026

@author: Adrian Riebel Brummer
"""

from .fluids import Fluid, FluidNameError
from .meteo_profile import MeteoProfile
import pandas as pd
import warnings
import numpy as np
from datetime import datetime
from types import SimpleNamespace
from .units import (
    
    convert_units,
    get_unit_types,
    UnitsError, )
from .core import (
    
    month_days,
    monthly_cummulated_days,
    month_names,
    _mean_squared_error, )

from .config import (
    
    default_year,
    demand_Tin_limits,
    demand_Tset_limits, )
from scipy.optimize import minimize, Bounds

# Numbers to define the fuctions that convert temperature to demand factors
demand_cluster_coefficients = { 0: {"m_h": -0.015442188, "b_h": 1.085192073, "m_w": -0.007095331, "b_w": 1.060986187, "T_hl": 2.9 },
                                1: {"m_h": -0.05875924, "b_h": 1.469535126, "m_w": -0.013263421, "b_w": 0.677907865, "T_hl": 17.4 },
                                2: {"m_h": -0.095984753, "b_h": 1.771938814, "m_w": -0.012756454, "b_w": 0.406994714, "T_hl": 16.4 },
                                3: {"m_h": -0.17801625, "b_h": 2.540402509, "m_w": -0.0214766, "b_w": 0.521041029, "T_hl": 12.9 } }
        
# List of argument names accepted by the DemandProfile class initializer function
DemandProfile_accepted_args = [
    
    "T_in_profile",
    "T_set_profile",
    "flowrate_profile",
    "fluid",
    "fluid_cp",
    "fluid_cp_units",
    "fluid_density",
    "fluid_density_units",
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
    
    "monthly_consumption",
    "heat_source",
    "heater",
    
    "monthly_production",
    
    "T_set",
    "T_in",
    
    "Tamb_dependence",
    "Tamb_dependence_mode",
    "Tamb_profile",
    
    "smooth_Tamb_profile",
    
    "meteo_profile",
    
    ]

class DemandProfile:
    
    """
    Class that computes, stores, and provides the thermal demand conditions of a heating system throughout an entire operation year.

    It allows the user to introduce custom daily demand profiles with time resolutions as small as 30 minutes.
    
    Moreover, this class is capable of modeling the dependence of the demanded power on the ambient temperature. Its default behavior is to automatically determine the level of dependence based on the monthly heat demand and ambient temperature provided by the user.
    
    It is strongly recommended to follow the :doc:`tutorial on the use of this class </demand_profile/DemandProfile_tutorial>` for some examples on how to construct the instances and get results from them. 

    Parameters
    ----------
    fluid : str or :doc:`Fluid </fluids/fluid_class>`
        Instance of the class :doc:`sercpy.fluids.Fluid </fluids/fluid_class>`
        or a valid name to initialize one. See :doc:`Fluids </fluids/fluids>`.
    
    T_set : float or list of float
        Setpoint temperature of the heating system. It
        can be a floating point value or a list of
        12 values (one per month). Range: 25 <= `T_set` <= 150.
    
    T_in : float, list of float, or str
        Temperature of the water entering the heating
        system. In the case of closed loops, it represents
        the temperature of the water coming back from
        the thermal load. It can be a floating point
        value or a list of 12 values (one per month).
        Range: 2 °C <= `T_in` <= 130 °C. Another valid value for
        this argument is the string `"mains"`, which implies
        that the water enters the heating system from the water
        distribution network. In this case, it is mandatory
        to provide the argument `meteo_profile` described below.
    
    temp_units : str, optional
        Units in which `T_in` and `T_set` are
        being specified. If not provided, it
        defaults to `"°C"`. See :doc:`/units/units`.
        
    T_units : str, optional
        Alias for `temp_units`.
    
    monthly_heat_demand : list of float, optional
        List of values >= 0, representing the heat demand (in terms of energy)
        of the thermal load in each month of the year. 12 values are expected,
        each one representing one month from January to December.
        The units in which energy is being provided
        must be specified with the parameter `heat_demand_units`.
        Either this parameter or `monthly_consumption` must be provided.
    
    heat_demand_units : str, optional
        Energy units used for the list `monthly_heat_demand`.
        Only needed if that parameter is specified.
        See :doc:`/units/units`
        
    monthly_consumption : list of float, optional
        List of 12 values representing the consumption of thermal energy sources
        (such as fuel or electricity) during each month of the year.
        This parameter is an alternative to `monthly_heat_demand` for specifying
        the monthly thermal demand.
        Fuel consumption can be specified in terms of 
        mass or volume. Electricity consumption must be specified in terms of energy.
        
    consumption_units : str, optional
        Units in which `monthly_consumption` is being specified.
        Only needed if that parameter is provided. For heaters (parameter `heater`)
        that use electricity, energy units are required.
        For any other fuel, mass or volume units
        are required. See :doc:`/units/units`.
    
    heater : :doc:`AutomaticBoiler </devices/boiler/automatic_boiler_class>`
        Heater currently used to provide heat to the system. It is used to convert
        the consumption introduced through `monthly_consumption` to thermal energy
        demand. This parameter is only needed if `monthly_consumption` is specified.
        
    daily_demand_profile : list of float, optional
        List of floating point values with length
        48, 24, or a divisor of 24. It represents
        how thermal demand gets distributed
        throughout a 24-hour period (from 00:00 to 24:00),
        with time resolution depending on the length
        of the list. The values within the list
        have no meaningful units; the total energy
        demand gets distributed throughout the
        day proportionally to the values of the list.
    
    daily_demand_profile_saturday : list of float, optional
        Special daily demand profile for saturday.
        This parameter is only considered if
        `daily_demand_profile` is specified.
        The format required is the same as for
        `daily_demand_profile`. If not specified,
        saturday is assumed to have the same
        profile as week days
        (given by theparameter `daily_demand_profile`).
    
    daily_demand_profile_sunday : list of float, optional
        Special daily demand profile for sunday.
        This parameter is only considered if
        `daily_demand_profile` is specified.
        The format required is the same as
        for `daily_demand_profile`. If not specified,
        the behavior depends on whether
        `daily_demand_profile_saturday`
        was specified. If it was specified,
        sunday is assumed to have no demand at
        all. If it was not specified, all days
        are assumed to have the same profile,
        defined by the parameter `daily_demand_profile`.
    
    daily_demand_ratio_saturday : float, optional
        Ratio between the total daily
        demand on saturdays and the
        total daily demand on a week day.
    
    daily_demand_ratio_sunday : float, optional
        Ratio between the total daily demand
        on sundays and the total daily demand on a week day.
    
    peak_demand_ratio_saturday : float, optional
        Ratio between the peak demand on saturdays
        and the peak on a week day. If specified,
        this parameter overrides
        `daily_demand_ratio_saturday`.
    
    peak_demand_ratio_sunday : float, optional
        Ratio between the peak demand on sundays and
        the peak on a week day. If specified,
        this parameter overrides `daily_demand_ratio_sunday`.
    
    weekly_demand_factors : list of float, optional
        List of seven values defining the relative total
        daily demand of each day of the week, starting
        on monday. If specified, this parameter
        overrides the four "ratio" parameters just described.
    
    daily_demand_profiles : list of list of float, optional
        List of seven daily demand profiles; one for
        each day of the week, starting on monday see
        `daily_demand_profile`. It must be specified
        along with `weekly_demand_factors`.
    
    weekly_demand_profile : list of float, optional
        Demand profile encompassing an entire week. It is equivalent
        to concatenating seven daily demand profiles of the
        same length, where the values of all profiles
        have a comparable scale.
    
    op_start : str, optional
        Operation start time. It must be a string with the format
        `"hh:mm"`, going from `"00:00"` to `"23:30"`. The "minutes"
        part of the time (i.e. the string `"mm"`) must be either
        `"00" or `"30". This parameter must be provided along with
        `op_end`. Its use is and alternative to specifying demand
        profiles. It will be ignored if any of the parameters
        `daily_demand_profile`, `daily_demand_profiles`, or
        `weekly_demand_profile` is specified.
    
    op_end : str, optional
        Operation end time. This parameter is only taken into account
        when provided along with `op_start`. The format expected
        from this parameter is the same as for `op_start`, with
        the difference that `op_end` is expected to be
        in the range `"00:30"` to `"24:00"`.
    
    op_start_saturday : str, optional
        Special operation start time for saturday. The expected type
        and format is the same as `op_start`. Only has effect
        if provided along with `op_start`.
    
    op_end_saturday : str, optional
        Special operation end time for saturday. The expected type
        and format is the same as `op_end`. Must be provided
        along with `op_start_saturday`.
    
    op_start_sunday : str, optional
        Special operation start time for sunday. The expected
        type and format is the same as `op_start`. Only has
        effect if provided along with `op_start`.
    
    op_end_sunday : str, optional
        Special operation end time for sunday. The expected
        type and format is the same as `op_end`. Must be provided
        along with `op_start_sunday`.
    
    Tamb_profile : list of float, optional
        Ambient temperature profile. List of values encompassing
        a whole year of temperature data for the location of
        the heating system. The list must have at least a daily
        resolution with average daily temperatures; thus, its
        length must be at least 365. It can also have a length
        which is a multiple of that number, in which case
        it will be interpreted as having a higher time resolution.
    
    Tamb_units : str, optional
        Units in which the `Tamb_profile` is being specified.
        If not provided, it defaults to
        `temp_units`/`T_units`. See :doc:`/units/units`.
        
    meteo_profile : sercpy.meteo_profile.MeteoProfile instance
        A `MeteoProfile` instance can be used to replace the
        argument `Tamb_profile`. If that argument is not provided
        and `meteo_profile` is provided instead, the ambient
        temperature profile will be extracted from that object.
        Specifying the argument `meteo_profile` is mandatory
        if the value of the argument `T_in` is the string `"mains"`.
    
    monthly_production : list of float, optional
        List of 12 values representing the monthly production from
        January to December. If provided, it is interpreted as
        a cause for variability of the monthly thermal demand,
        along with the ambient temperature.
    
    Tamb_dependence : float or callable, optional
        Parameter to define the level of dependence of the thermal
        load on the ambient temperature. Using this parameter is
        generally discouraged since the class
        is meant to automatically determine it.
        If the parameter type is float, it is interpreted as the
        level of dependence of thermal demand on ambient temperature
        as discussed in :doc:`/demand_profile/Tamb_dependence`.
        If it is a callable object, it is interpreted as a custom
        function that translates daily demand values to demand factors.
    
    smooth_Tamb_profile : bool, optional
        Boolean value defining whether to correct the daily ambient
        temperature using the temperatures of the three preceding
        days, as discussed in :doc:`/demand_profile/Tamb_dependence`.
        If not provided, it defaults to `True`.
    
    Attributes
    ----------
    weekly_demand_profile : list of float
        List of 336 values that characterizes how thermal demand
        gets distributed throughout a week, with 30-minute
        resolution. The demand values are ordered from Monday
        to Sunday, and do not have any power or energy units.
    
    fluid : :doc:`Fluid </fluids/fluid_class>`
        Heat transfer fluid that gets heated by the system.
    
    HTF : :doc:`Fluid </fluids/fluid_class>`
        Alias for `fluid`.
    
    heat_transfer_fluid : :doc:`Fluid </fluids/fluid_class>`
        Alias for `fluid`.
    
    Tamb_dependence : float
        Number between 0 and 3 defining the level of
        dependence of thermal demand on the daily ambiente temperature.
    
    monthly_T_set : list of float
        List of 12 values containing the setpoint
        temperature of the heating system for
        each month of the year, from January to December.
    
    monthly_T_in : list of float
        List of 12 values containing the temperature
        with which the heat transfer fluid enters the
        heating system during each month of the year, from January to December.
    
    monthly_heat_demand : list of float
        List of 12 values containing the total energy
        demanded by the thermal load during each
        month of the year. Unit: Joule.
    
    monthly_consumption : list of float
        List of 12 values containing the heat source
        consumption (electricity or fuel) during each
        month of the year. Unit: Joule for electricity; kg for fuels.
    
    op_start : str
        Operation start time. If special operation times
        have been defined for weekend days, it only
        applies to week days. Otherwise, it applies to all days.
    
    op_end : str
        Operation end time. If special operation times have
        been defined for weekend days, it only
        applies to week days. Otherwise, it applies to all days.
    
    op_start_saturday : str
        Operation start time for saturdays.
    
    op_end_saturday : str
        Operation end time for saturdays.
    
    op_start_sunday : str
        Operation start time for sundays.
    
    op_end_sunday : str
        Operation end time for sundays.
    
    """
    
    def __init__(
            
            self, 
            *,
            
            fluid = None,
            pressure_abs = None,
            pressure_man = None,
            pressure_rel = None,
            
            T_set,
            T_in,
            temp_units = None,
            T_units = None,
            
            monthly_heat_demand = None,
            heat_demand_units = None,
            
            monthly_consumption = None,
            consumption_units = None,
            heater = None,
            
            daily_demand_profile = None,
            daily_demand_profile_saturday = None,
            daily_demand_profile_sunday = None,
            
            daily_demand_ratio_saturday = None,
            daily_demand_ratio_sunday = None,
            peak_demand_ratio_saturday = None,
            peak_demand_ratio_sunday = None,
            
            weekly_demand_factors = None,
            
            daily_demand_profiles = None,
            weekly_demand_profile = None,
            
            op_start = None,
            op_end = None,
            op_start_saturday = None,
            op_end_saturday = None,
            op_start_sunday = None,
            op_end_sunday = None,
            
            monthly_production = None,
            
            Tamb_profile = None,
            Tamb_units = None,
            meteo_profile = None,
            
            Tamb_dependence = None,
            
            
            smooth_Tamb_profile = None,
            
            **kwargs,
            
            ):
        
        if T_set is None or T_in is None:
            raise ValueError("Class DemandProfile: Arguments T_set and T_in must be provided.")
        
        self._monthly_T_set = self._validate_argument("T_set", T_set)
        if temp_units is not None:
            self._monthly_T_set = convert_units( self._monthly_T_set, temp_units, "C" )
        elif T_units is not None:
            self._monthly_T_set = convert_units( self._monthly_T_set, T_units, "C" )
            
        if not all( [ T >= demand_Tset_limits[0] and T <= demand_Tset_limits[1] for T in self._monthly_T_set ] ):
            raise ValueError(f"Class DemandProfile: T_set value(s) must be within the range: {demand_Tset_limits[0]} °C <= T_set <= {demand_Tset_limits[1]} °C.")        
        
        T_in = self._validate_argument("T_in", T_in)
        
        if T_in == 'mains':
            if meteo_profile is None:
                raise ValueError("Class DemandProfile: The argument 'meteo_profile' must be provided if the value of 'T_in' is the string 'mains'.")
            meteo_profile = self._validate_argument("meteo_profile", meteo_profile)
            self._monthly_T_in = self._Tin_from_meteo_profile( meteo_profile )
        else:
            self._monthly_T_in = T_in
            if temp_units is not None:
                self._monthly_T_in = convert_units( self._monthly_T_in, temp_units, "C" )
            elif T_units is not None:
                self._monthly_T_in = convert_units( self._monthly_T_in, T_units, "C" )
            if not all( [ T >= demand_Tin_limits[0] and T <= demand_Tin_limits[1] for T in self._monthly_T_in ] ):
                raise ValueError(f"Class DemandProfile: T_in value(s) must be within the range: {demand_Tin_limits[0]} °C <= T_set <= {demand_Tin_limits[0]} °C.")
            
        if fluid is None:
            raise TypeError("Class DemandProfile: Argument 'fluid' cannot be None.")
        
        fluid = self._validate_argument("fluid", fluid)
        
        if type( fluid ) is str:
            try:
                self._fluid = Fluid( fluid, p = 800000, T_ref = float( ( np.mean( self._monthly_T_in ) + np.mean( self._monthly_T_set ) )/2 ) )
            except FluidNameError:
                raise TypeError(f"Class DemandProfile: Fluid (sercpy.fluids.Fluid) instance could not be constructed because the fluid name entered (= {fluid}) is not valid.")
                
        if all( [ keyword in kwargs for keyword in [
                
                "flowrate_profile",
                "demanded_power_profile",
                "T_in_profile",
                "T_set_profile", ] ] ):
            
            self._flowrate_profile = kwargs[ "flowrate_profile" ]
            self._demanded_power_profile = kwargs[ "demanded_power_profile" ]
            self._T_in_profile = kwargs[ "T_in_profile" ]
            self._T_set_profile = kwargs[ "T_set_profile" ]
            return
            
        if monthly_heat_demand is not None:
            self._monthly_heat_demand = self._validate_argument("monthly_heat_demand", monthly_heat_demand)
            heat_demand_units = self._validate_argument("heat_demand_units", heat_demand_units)
            if heat_demand_units is None:
                warnings.warn("Class DemandProfile: 'monthly_heat_demand' argument was provided but no 'heat_demand_units'. Joule is assumed as default.")
            else:
                try:
                    self._monthly_heat_demand = convert_units(self._monthly_heat_demand, heat_demand_units, 'J')
                except UnitsError:
                    raise ValueError( f"Class DemandProfile: monthly_heat_demand could not be converted from the energy units provided: {heat_demand_units}." )
        elif monthly_consumption is not None:
            pass

        else:
            raise ValueError("Class DemandProfile: Either 'monthly_heat_demand' or 'monthly_consumption' must be specified.")

        if weekly_demand_profile is not None:
            weekly_demand_profile = self._validate_argument("weekly_demand_profile", weekly_demand_profile)
            self._weekly_demand_profile = self._extend_profile(weekly_demand_profile, 48*7)
            
        elif daily_demand_profiles is not None:
            self._daily_demand_profiles = self._validate_argument("daily_demand_profiles", daily_demand_profiles)
            self._weekly_demand_factors = self._validate_argument("weekly_demand_factors", weekly_demand_factors)
            self._week_constructor_1()
            
        elif daily_demand_profile is not None:
            
            self._daily_demand_profile = self._validate_argument("daily_demand_profile", daily_demand_profile)
            self._daily_demand_profile_saturday = self._validate_argument("daily_demand_profile_saturday", daily_demand_profile_saturday)
            self._daily_demand_profile_sunday = self._validate_argument("daily_demand_profile_sunday", daily_demand_profile_sunday)
            self._weekly_demand_factors = self._validate_argument("weekly_demand_factors", weekly_demand_factors)
            self._daily_demand_ratio_saturday = self._validate_argument("daily_demand_ratio_saturday", daily_demand_ratio_saturday)
            self._peak_demand_ratio_saturday = self._validate_argument("peak_demand_ratio_saturday", peak_demand_ratio_saturday)
            self._daily_demand_ratio_sunday = self._validate_argument("daily_demand_ratio_sunday", daily_demand_ratio_sunday)
            self._peak_demand_ratio_sunday = self._validate_argument("peak_demand_ratio_sunday", peak_demand_ratio_sunday)
            self._week_constructor_2()
            
        elif op_start is not None:
            
            self._op_start = self._validate_argument("op_start", op_start)
            self._op_end = self._validate_argument("op_end", op_end)
            self._op_start_saturday = self._validate_argument("op_start_saturday", op_start_saturday)
            self._op_end_saturday = self._validate_argument("op_end_saturday", op_end_saturday)
            self._op_start_sunday = self._validate_argument("op_start_sunday", op_start_sunday)
            self._op_end_sunday = self._validate_argument("op_end_sunday", op_end_sunday)
            self._weekly_demand_factors = self._validate_argument("weekly_demand_factors", weekly_demand_factors)
            self._daily_demand_ratio_saturday = self._validate_argument("daily_demand_ratio_saturday", daily_demand_ratio_saturday)
            self._peak_demand_ratio_saturday = self._validate_argument("peak_demand_ratio_saturday", peak_demand_ratio_saturday)
            self._daily_demand_ratio_sunday = self._validate_argument("daily_demand_ratio_sunday", daily_demand_ratio_sunday)
            self._peak_demand_ratio_sunday = self._validate_argument("peak_demand_ratio_sunday", peak_demand_ratio_sunday)
            self._week_constructor_3()
            
        else:
            self._weekly_demand_profile = [ 1 ]*48*7
            
        self._Tamb_dependence = self._validate_argument("Tamb_dependence", Tamb_dependence)
            
        if Tamb_dependence is not None:
            self._Tamb_dependence_mode = "manual"
        else:
            self._Tamb_dependence_mode = "auto"
                
        self._monthly_production = self._validate_argument("monthly_production", monthly_production)
        
        if Tamb_profile is None and meteo_profile is not None:
            meteo_profile = self._validate_argument("meteo_profile", meteo_profile)
            meteo_df = meteo_profile.get_conditions()
            self._Tamb_profile = meteo_df[ "Tamb" ].values.astype(float).tolist()
        else:
            self._Tamb_profile = self._validate_argument("Tamb_profile", Tamb_profile)
            
            if self._Tamb_profile is not None:
                if Tamb_units is not None:
                    self._Tamb_profile = convert_units( self._Tamb_profile, Tamb_units, 'C' )
                elif temp_units is not None:
                    self._Tamb_profile = convert_units( self._Tamb_profile, temp_units, 'C' )
                elif T_units is not None:
                    self._Tamb_profile = convert_units( self._Tamb_profile, T_units, 'C' )
            
        if smooth_Tamb_profile is not None:
            self._smooth_Tamb_profile = self._validate_argument( "smooth_Tamb_profile", smooth_Tamb_profile )
        else:
            self._smooth_Tamb_profile = True
            
        self._year = default_year
            
        self._compute_yearly_profiles()
        
    @property
    def weekly_demand_profile(self):
        "List of 336 values that characterizes how thermal demand gets distributed throughout a week, with 30-minute resolution. The demand values are ordered from Monday to Sunday, and do not have any power or energy units."
        return self._weekly_demand_profile
        
    @property
    def Tamb_dependence(self):
        "Number between 0 and 3 defining the level of dependence of thermal demand on the daily ambiente temperature."
        return self._Tamb_dependence
        
    @property
    def monthly_T_set(self):
        "List of 12 values containing the setpoint temperature of the heating system for each month of the year, from January to December."
        return self._monthly_T_set
        
    @property
    def monthly_T_in(self):
        "List of 12 values containing the temperature with which the heat transfer fluid enters the heating system during each month of the year, from January to December."
        return self._monthly_T_in
    
    @property
    def monthly_heat_demand(self):
        "List of 12 values containing the total energy demanded by the thermal load during each month of the year. Unit: Joule."
        return self._monthly_heat_demand
        
    @property
    def monthly_consumption(self):
        "List of 12 values containing the heat source consumption (electricity or fuel) during each month of the year. Unit: Joule for electricity; kg for fuels."
        return self._monthly_consumption
        
    @property
    def op_start(self):
        "Operation start time. If special operation times have been defined for weekend days, it only applies to week days. Otherwise, it applies to all days."
        return self._op_start
        
    @property
    def op_end(self):
        "Operation end time. If special operation times have been defined for weekend days, it only applies to week days. Otherwise, it applies to all days."
        return self._op_end
        
    @property
    def op_start_saturday(self):
        "Operation start time for saturdays."
        return self._op_start_saturday
        
    @property
    def op_end_saturday(self):
        "Operation end time for saturdays."
        return self._op_end_saturday
        
    @property
    def op_start_sunday(self):
        "Operation start time for sundays."
        return self._op_start_sunday
        
    @property
    def op_end_sunday(self):
        "Operation end time for sundays."
        return self._op_end_sunday
    
    @property
    def fluid(self):
        return self._fluid
    
    @property
    def HTF(self):
        return self._fluid
    
    @property
    def heat_transfer_fluid(self):
        return self._fluid
        
    ## Alternative initialization using the library "loadcast"
    @classmethod
    def from_loadcast( cls, T_set, T_in, fluid, meteo_profile = None, **loadcast_params ):
        """
        Alternative initialization of the `DemandProfile` instance that uses
        the result returned by the function `generate`
        from the library `loadcast <https://loadcast.readthedocs.io/en/latest/>`_
        to establish the yearly heat demand profile.
        
        In addition to the parameters that will be passed to the function just mentioned,
        he user also has to specify the setpoint temperature of the heating system,
        the inlet temperature with wich the heat transfer fluid enters the heating system,
        and the fluid used as heat transfer fluid.
        
        The user has to keep in mind that loadcast is not automatically installed
        along with **SERCpy**. In order to use this function, the user has to install
        loadcast independently.

        Parameters
        ----------
        T_set : list or float
            Setpoint temperature of the heating system (°C). If a list is provided,
            it is expected to have 12 values, where each value represents the
            sepoint temperature during on month of the year, from January to Dember.
        T_in : list, str or float
            Temperature with which the heat transfer fluid
            enters the heating system (°C). If a list is provided,
            it is expected to have 12 values, where each value represents the
            inlet temperature during on month of the year, from January to Dember.
            This parameter can also be the string `"mains"`. In that case, the
            parameter `meteo_profile` is required.
        fluid : str or :doc:`Fluid </fluids/fluid_class>`
            Instance of :doc:`sercpy.fluids.Fluid </fluids/fluid_class>`,
            or a valid name to initialize it (str).
        meteo_profile : :doc:`MeteoProfile </meteo_profile/meteo_profile_class>`
            Only needed when the parameter `T_in` is the string `"mains"`
            (see the argument with the same name in
            :doc:`the main documentation of the class </meteo_profile/meteo_profile_class>`).
        **loadcast_params : any
            Arguments that will be passed to the function `generate` by `loadcast <https://loadcast.readthedocs.io/en/latest/>`_.

        Raises
        ------
        ImportError
            If loadcast fails to be imported.
        
        Returns
        -------
        None.

        """
        
        try:
            import loadcast
        except ImportError:
            raise ImportError("DemandProfile.from_loadcast: 'loadcast' could not be imported. Check whether it is installed.")
        
        try:
            loadcast_profile = loadcast.generate( **loadcast_params )
        except:
            raise Exception("DemandProfile.from_loadcast: loadcast.generate failed to generate the profile. Check the keyword arguments.")
        
        try:
            heat_demand_profile = loadcast_profile[ "heat_kw" ].values
        except KeyError:
            raise KeyError("DemandProfile.from_loadcast: Heat demand column was not found in the DataFrame returned by loadcast with the expected name 'heat_kw'.")
            
        if len( heat_demand_profile ) == 0:
            raise ValueError("DemandProfile.from_loadcast: Resulting demand profile has length zero (i.e. it is empty).")
        
        if len( heat_demand_profile ) % 8760 != 0:
            raise ValueError("DemandProfile.from_loadcast: Demand profile length is expected to be divisible by 8760.")
            

        if T_set is None or T_in is None:
            raise ValueError("Class DemandProfile: Arguments T_set and T_in must be provided.")
        
        monthly_T_set = cls._validate_argument("T_set", T_set)
            
        if not all( [ T >= demand_Tset_limits[0] and T <= demand_Tset_limits[1] for T in monthly_T_set ] ):
            raise ValueError(f"Class DemandProfile: T_set value(s) must be within the range: {demand_Tset_limits[0]} °C <= T_set <= {demand_Tset_limits[1]} °C.")        
        
        T_in = cls._validate_argument("T_in", T_in)
        
        if T_in == 'mains':
            if meteo_profile is None:
                raise ValueError("Class DemandProfile: The argument 'meteo_profile' must be provided if the value of 'T_in' is the string 'mains'.")
            meteo_profile = cls._validate_argument("meteo_profile", meteo_profile)
            monthly_T_in = cls._Tin_from_meteo_profile( meteo_profile )
        else:
            monthly_T_in = T_in
            if not all( [ T >= demand_Tin_limits[0] and T <= demand_Tin_limits[1] for T in monthly_T_in ] ):
                raise ValueError(f"Class DemandProfile: T_in value(s) must be within the range: {demand_Tin_limits[0]} °C <= T_set <= {demand_Tin_limits[0]} °C.")
            
        if fluid is None:
            raise TypeError("Class DemandProfile: Argument 'fluid' cannot be None.")
        
        fluid = cls._validate_argument("fluid", fluid)
        
        if type( fluid ) is str:
            try:
                fluid = Fluid( fluid, p = 800000, T_ref = float( ( np.mean( monthly_T_in ) + np.mean( monthly_T_set ) )/2 ) )
            except FluidNameError:
                raise TypeError(f"Class DemandProfile: Fluid (sercpy.fluids.Fluid) instance could not be constructed because the fluid name entered (= {fluid}) is not valid.")

        
        # Convert to W
        len_before = len( heat_demand_profile )
        heat_demand_profile = 1000*heat_demand_profile
        assert len( heat_demand_profile ) == len_before
        
        values_per_hour = len( heat_demand_profile ) // 8760
        
        demanded_power_profile = []
        flowrate_profile = []
        T_in_profile = []
        T_set_profile = []
        
        for month in range(12):
            
            delta_h_this_month = fluid.state( T = monthly_T_set[ month ] ).h -  fluid.state( T = monthly_T_in[ month ] ).h
            
            index_month_start = monthly_cummulated_days[ month ] * values_per_hour * 24
            index_month_end = monthly_cummulated_days[ month + 1 ] * values_per_hour * 24
            
            for index in range( index_month_start, index_month_end ):
                
                demanded_power = heat_demand_profile[ index ]
                demanded_flowrate = demanded_power / delta_h_this_month
                
                demanded_power_profile.append( demanded_power )
                flowrate_profile.append( demanded_flowrate )
                T_in_profile.append( monthly_T_in[ month ] )
                T_set_profile.append( monthly_T_set[ month ] )
                    
        if not 60 % values_per_hour == 0:
            raise ValueError(f"Number of values per hour obtained from the length of the dataset ({values_per_hour}) does not correspond to an entire number of minutes.")
        
        minutes_per_value = 60 // values_per_hour
        
        flowrate_profile = np.concatenate( [ [value] * minutes_per_value for value in flowrate_profile ] ).astype(float).tolist() 
        demanded_power_profile = np.concatenate( [ [value] * minutes_per_value for value in demanded_power_profile ] ).astype(float).tolist() 
        T_in_profile = np.concatenate( [ [value] * minutes_per_value for value in T_in_profile ] ).astype(float).tolist() 
        T_set_profile = np.concatenate( [ [value] * minutes_per_value for value in T_set_profile ] ).astype(float).tolist() 
                
        assert len(flowrate_profile) == 525600
        assert len(demanded_power_profile) == 525600
        assert len( T_in_profile ) == 525600
        assert len( T_set_profile ) == 525600
        
        minutes_per_day = 60*24
        flowrate_profile = [ flowrate_profile[ init_minute : init_minute + minutes_per_day ] for init_minute in range( 0, len( flowrate_profile ), minutes_per_day ) ]
        demanded_power_profile = [ demanded_power_profile[ init_minute : init_minute + minutes_per_day ] for init_minute in range( 0, len( demanded_power_profile ), minutes_per_day ) ]
        T_in_profile = [ T_in_profile[ init_minute : init_minute + minutes_per_day ] for init_minute in range( 0, len( T_in_profile ), minutes_per_day ) ]
        T_set_profile = [ T_set_profile[ init_minute : init_minute + minutes_per_day ] for init_minute in range( 0, len( T_set_profile ), minutes_per_day ) ]
        
        return cls(
            
            fluid = fluid,
            T_in = monthly_T_in,
            T_set = monthly_T_set,
            flowrate_profile = flowrate_profile,
            demanded_power_profile = demanded_power_profile,
            T_in_profile = T_in_profile,
            T_set_profile = T_set_profile, )
        
    def _week_constructor_1( self, ):
        """
        Private method that defines the attribute "weekly_demand_profile" from the attributes "daily_demand_profiles" and "weekly_demand_factors".
        
        "daily_demand_profiles" is a list of seven lists, where each list defines the daily demand profile of one day of the week, starting on Monday.
        
        "weekly_demand_factors" is a list of seven values defining the relative daily thermal demand of each day of the week, starting on Monday.
        
        The generated attribute "weekly_demand_profile" is a list of 336 values defining how thermal demand is distributed throughout a whole week, with 30-minute resolution.

        The method takes no arguments besides the DemandProfile instance.
        
        Returns
        -------
        None
        """
        
        daily_demand_profiles = self._daily_demand_profiles
        weekly_demand_factors = self._weekly_demand_factors
        
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
        """
        Private method that defines the attributes "daily_demand_profiles" and "weekly_demand_factors" from individual daily profiles, and, if present, special demand ratios or profiles for weekend days.
        
        The generated attribute "daily_demand_profiles" is a list of seven lists, where each list defines the daily demand profile of one day of the week, starting on Monday.
        
        The generated attribute "weekly_demand_factors" is a list of seven values defining the relative daily thermal demand of each day of the week, starting on Monday.
        
        This method calls the private method "_week_constructor_1" to define the attribute "weekly_demand_profile" from the attributes defined here.
        
        The method takes no arguments besides the DemandProfile instance.
        
        Returns
        -------
        None
        """
        
        daily_demand_profile = self._daily_demand_profile
        daily_demand_profile_saturday = self._daily_demand_profile_saturday
        daily_demand_profile_sunday = self._daily_demand_profile_sunday
        weekly_demand_factors = self._weekly_demand_factors
        daily_demand_ratio_saturday = self._daily_demand_ratio_saturday
        peak_demand_ratio_saturday = self._peak_demand_ratio_saturday
        daily_demand_ratio_sunday = self._daily_demand_ratio_sunday
        peak_demand_ratio_sunday = self._peak_demand_ratio_sunday
        
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
        """
        Private method that defines the attribute "weekly_demand_profile" from the attributes "op_start", "op_end", and, if present, special demand ratios or schedules for weekend days.
        
        The generated attribute "weekly_demand_profile" is a list of 336 values defining how thermal demand is distributed throughout a whole week, with 30-minute resolution.
        
        The method takes no arguments besides the DemandProfile instance.
        
        Returns
        -------
        None
        """
        
        # Local function that takes a time of day in string format (e.g. "04:30") and returns the number of half hours elapsed since midnight
        # E.g. To the input "04:30" the function returns 9
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
        
        op_start = self._op_start
        op_end = self._op_end
        op_start_saturday = self._op_start_saturday
        op_end_saturday = self._op_end_saturday
        op_start_sunday = self._op_start_sunday
        op_end_sunday = self._op_end_sunday
        weekly_demand_factors = self._weekly_demand_factors
        peak_demand_ratio_saturday = self._peak_demand_ratio_saturday
        daily_demand_ratio_saturday = self._daily_demand_ratio_saturday
        peak_demand_ratio_sunday = self._peak_demand_ratio_sunday
        daily_demand_ratio_sunday = self._daily_demand_ratio_sunday
        
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
                raise ValueError("Class DemandProfile: Argument 'op_end_saturday' must be different from 'op_start_saturday'.")
                
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
        def _compute_operation_time( start_step, end_step ):
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
                    peak_demand_ratio = daily_demand_ratio*_compute_operation_time( start_step_week, end_step_week )/_compute_operation_time(start_step, end_step)
                    
                elif peak_demand_ratio is None:
                    
                    if daily_demand_ratio is not None:
                        peak_demand_ratio = daily_demand_ratio*_compute_operation_time( start_step_week, end_step_week )/_compute_operation_time(start_step, end_step)
                        
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
    def _validate_argument(argument_name, value):
        """
        Static mathod that takes an argument received by the initializing method (`__init__`) and checks whether its type and value match the expected format.
        
        If necessary, this method modifies the value received to adjust it to the expected format, and returns the modified value.
        
        Parameters
        ----------
        argument_name : str
            Name of the argument that is being processed.
        value : Any
            Value of the variable that is being processed.

        Raises
        ------
        TypeError
            If the argument `argument_name` is not a string.
        ValueError
            Any discrepancy between the expected type or value of the argument and the value received.

        Returns
        -------
        value : Any
            If any adjustment to the value received is necessary, the function returns the modified value.
            Otherwise, the input value is returned as received.

        """
        
        if type(argument_name) is not str:
            raise TypeError("DemandProfile._validate_argument: Argument 'argument_name' must be a string.")
        
        if not argument_name in DemandProfile_accepted_args:
            raise ValueError(f"Class DemandProfile: Unexpected argument name: {argument_name}")
        
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
                hour = int( value.split(':')[0] )
                minute = int( value.split(':')[1] )
                assert hour >= 0 and hour <= 24 and minute in [0, 30] and not (hour == 24 and minute == 30)
                if argument_name.startswith( "op_start" ) and hour == 24:
                    value = "00:00"
                elif argument_name.startswith( "op_end" ) and hour == 0 and minute == 0:
                    value = "24:00"
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
                raise ValueError("Class DemandProfile: Argument 'weekly_demand_profile' must be a list of values convertible to type 'float', whose length must be a divisor of 336, or 336 itself.")
        
        if argument_name == "fluid":
            
            if not ( type(value) is str or isinstance( value, Fluid ) ):
                raise TypeError("Class DemandProfile: Argument 'fluid' must be a string or an instance of sercpy.fluids.Fluid.")
        
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
                "monthly_consumption",
                "monthly_production",
                ]:
            try:
                value = list(value)
                assert len(value) == 12
                value = [ float(v) for v in value ]
                assert all([ v >= 0 for v in value ]) and sum(value) > 0
            except:
                raise ValueError(f"Class DemandProfile: Argument '{argument_name}' must be a list of values convertible to type 'float', all of which must be >= 0. At least one of them must be > 0.")
                
        if argument_name  == "T_set":
            temp_limits = [ 25, 150 ]
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
        
        if argument_name == "T_in":
            temp_limits = [ 2, 130 ]
            
            try:
                value_2 = float( value )
                value_2 = [ value_2 ]*12
                value = value_2
            except:
                try:
                    value_2 = [ float( v ) for v in value ]
                    value = value_2
                except:
                    try:
                        value_2 =  str( value )
                        if value_2 != 'mains':
                            raise ValueError("Class DemandProfile: Argument T_in must be either a floating point value, or a list of 12 values, or the string 'mains'.")
                        value = value_2
                    except:
                        raise ValueError("Class DemandProfile: Argument T_in must be either a floating point value, or a list of 12 values, or the string 'mains'.")
            
            if type( value ) is list:
                if len( value ) != 12:
                    raise ValueError("Class DemandProfile: Argument 'T_in' must be either a floating point value, or a list of 12 values, or the string 'mains'.")
                if not all( [ v >= temp_limits[0] and v <= temp_limits[1] for v in value ] ):
                    raise ValueError("Class DemandProfile: The value of T_in must be in the range 2 °C <= T_in <= 130 °C")
            else:
                assert type( value ) is str
                assert value == 'mains'
        
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
                value = [ float(v) for v in value ]
                assert all([ v >= -50 and v <= 60 for v in value ])
                assert len( value ) == 365 or len( value )%365 == 0
            except:
                raise ValueError("Class DemandProfile: Tamb_profile must be a list of numberic values between -50 and 60, whose length must be equal to 365 or a multiple of that number.")
        
        if argument_name == "heat_demand_units":
            try:
                value = str(value)
            except:
                raise ValueError("Class DemandProfile: Argument 'heat_demand_units' must be convertible to string.")
            try:
                assert get_unit_types( value ) == 'energy'
            except:
                raise ValueError("Class DemandProfile: Argument 'heat_demand_units' must correspond to a unit of energy.")
        
        if argument_name == "smooth_Tamb_profile":
            
            if not ( type(value) is bool or ( type( value ) is int and value in [ 0, 1 ] ) ):
                raise ValueError("Class DemandProfile: smooth_Tamb_profile must be a boolean value.")
            value = bool( value )
                
        if argument_name == "year":
            
            try:
                value = int(value)
                assert value >= 2000 and value <= 2050
            except:
                raise ValueError("Class DemandProfile: Argument 'year' must be a numberic value convertible to type 'int'. It must be >= 2000 and <= 2050.")
        
        if argument_name == "heat_source":
            try:
                value = str(value)
                value = value.upper()
            except:
                raise ValueError("Class DemandProfile: Argument 'heat_source' must be convertible to string.")
                
        if argument_name == "consumption_units":
            try:
                value = str(value)
            except:
                raise ValueError("Class DemandProfile: Argument 'consumption_units' must be convertible to string.")
        
        if argument_name == "heater_efficiency":
            try:
                value = float(value)
            except:
                raise TypeError("Class DemandProfile: Argument 'heater_efficiency' must be convertible to type 'float'.")
            if value <= 0:
                raise ValueError("Class DemandProfile: Argument 'heater_efficiency' must be > 0.")
        
        if argument_name == "heat_source_heating_value":
            try:
                value = float(value)
            except:
                raise TypeError("Class DemandProfile: Argument 'heat_source_heating_value' must be convertible to type 'float'.")
            if value <= 0:
                raise ValueError("Class DemandProfile: Argument 'heat_source_heating_value' must be > 0.")
                
        if argument_name == "heat_source_density":
            try:
                value = float(value)
            except:
                raise TypeError("Class DemandProfile: Argument 'heat_source_density' must be convertible to type 'float'.")
            if value <= 0:
                raise ValueError("Class DemandProfile: Argument 'heat_source_density' must be > 0.")
        
        if argument_name == "heat_source_heating_value_units":
            try:
                value = str(value)
            except:
                raise TypeError("Class DemandProfile: Argument 'heat_source_heating_value_units' must be a string.")
            try:
                assert get_unit_types( value ) in [ 'energy / mass', 'energy / volume' ]
            except:
                raise ValueError("Class DemandProfile: Argument 'heat_source_heating_value_units' must be a string representing units with the form 'energy / mass' or 'energy / volume'.")
                
        if argument_name == "heat_source_density_units":
            try:
                value = str(value)
            except:
                raise ValueError("Class DemandProfile: Argument 'heat_source_density_units' must be a string.")
            try:
                assert get_unit_types( value ) == 'mass / volume'
            except:
                raise ValueError("Class DemandProfile: Argument 'heat_source_heating_value_units' must be a string representing units with the form 'mass / volume'.")
                
        if argument_name == "condensation_boiler":
            if not ( type(value) is bool or ( type( value ) is int and value in [ 0, 1 ] ) ):
                raise ValueError("Class DemandProfile: Argument 'condensation_boiler' must be boolean.")
            value = bool( value )
            
        if argument_name == "meteo_profile":
            
            if not isinstance( value, MeteoProfile ):
                raise TypeError("Class DemandProfile: Argument 'meteo_profile' must be a meteo_profile.MeteoProfile instance.")
        
        return value
        
    @staticmethod
    def open_profile_app():
        """
        Static method to open the Profile App of the class, developed on Python's GUI tool Tkinter.
        
        The method takes no arguments.

        Returns
        -------
        None.
        """
        from . import profile_app
        profile_app.launch()
        
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
        return cls( **kwargs )
    
    @staticmethod
    def define_temp_to_factor_func(
            dependence_coeff,
            temp_units = None ):
        """
        Define a Temperature-to-Demand-Factor function.
        
        This static method takes a floating point value from 0 to 3, which defines the dependence level of thermal demand on ambient temperature.
        
        It returns a function than can be used thereafter to obtain relative daily demand values from daily temperatures.
        
        The temperature units with wich the returned function will process the temperature data can be managed with the argument `temp_units`.
        
        Parameters
        ----------
        dependence_coeff : float
            Value from 0 to 3. Both limits are valid. This value defines the level of dependence of the thermal demand on ambient temperature.
        temp_units : str
            Units in which the daily temperatures will be provided to the returned function. If not provided, it defaults to °C.
        
        Returns
        -------
        func
            Function that takes a daily temperature value (float) and returns a float value proportional to the demand level of that day.
        
        """
        
        try:
            dependence_coeff = float(dependence_coeff)
        except:
            raise ValueError("Function: define_temp_to_factor_func: Parameter 'dependence_coeff' must be convertible to type 'float'.")
            
        if temp_units is not None:
            try:
                T = convert_units(30, temp_units, 'C')
            except:
                raise TypeError(f"DemandProfile.define_temp_to_factor_func: Argument 'temp_units' ({temp_units}) is not valid.")
        
        if not ( dependence_coeff >= 0 and dependence_coeff <= 3 ):
            raise ValueError("Function: define_temp_to_factor_func: Parameter 'dependence_coeff' must be larger than or equal to 0, and smaller than or equal to 3.")
            
        if temp_units is None or temp_units in [ 'C', '°C' ]:
            convert_temperature = False
        else:
            convert_temperature = True
        
        if dependence_coeff.is_integer():
            
            dependence_coeff = int(dependence_coeff)
            T_hl = demand_cluster_coefficients[dependence_coeff]["T_hl"]
            m_h = demand_cluster_coefficients[dependence_coeff]["m_h"]
            b_h = demand_cluster_coefficients[dependence_coeff]["b_h"]
            m_w = demand_cluster_coefficients[dependence_coeff]["m_w"]
            b_w = demand_cluster_coefficients[dependence_coeff]["b_w"]
            
            if convert_temperature:
                def temp_to_factor( T ):
                    T = convert_units( T, temp_units, 'C' )
                    if T >= T_hl:
                        return max( [ m_w*T + b_w, 0 ] )
                    return max( [ m_h*T + b_h, 0 ] )
            else:
                def temp_to_factor(T):
                    if T >= T_hl:
                        return max( [ m_w*T + b_w, 0 ] )
                    return max( [ m_h*T + b_h, 0 ] )
        
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
                    return max( [ m_w_1*T + b_w_1, 0 ] )
                return max( [ m_h_1*T + b_h_1, 0 ] )
            
            def temp_to_factor_2(T):
                if T >= T_hl_2:
                    return max( [ m_w_2*T + b_w_2, 0 ] )
                return max( [ m_h_2*T + b_h_2, 0 ] )
            
            if convert_temperature:
                def temp_to_factor(T):
                    T = convert_units( T, temp_units, 'C' )
                    return x_1*temp_to_factor_1(T) + (1 - x_1)*temp_to_factor_2(T)
            else:
                def temp_to_factor(T):
                    return x_1*temp_to_factor_1(T) + (1 - x_1)*temp_to_factor_2(T)
                
        return temp_to_factor
    
    @staticmethod
    def compute_Tamb_dependence(
            monthly_heat_demand,
            Tamb_profile,
            temp_units = None,
            monthly_production = None,
            monthly_T_in = None,
            monthly_T_set = None,
            epsilon_fraction = None ):
        
        """
        Static method to determine the level of dependence of the heat demand on the ambient temperature.
        
        The function takes monthly heat demand data and a yearly ambient temperature profile.
        
        Monthly production values, if provided, are considered as a cause for the variation of the heat demand, in addition to ambient temperature. If no production data is provided, it is assumed that the only cause for variability in the heat demand is differences in ambient temperature.

        Parameters
        ----------
        monthly_heat_demand : list of float
            List of 12 values representing the monthly heat demand, from January to December. The units of the values of the list are not relevant, as long as they are energy units.
        
        Tamb_profile : list of float
            List of at least 365 values defining the yearly ambient temperature profile. The length can also be a multiple of 365; in that case, it is assumed that the profile has a time resolution higher than one value per day; hence, the values are averaged to get a daily resolution.
        
        monthly_production : list of float, optional
            List of 12 values representing the monthly production, from January to December. The units of the values of the list are not relevant. The default is None.
        
        monthly_T_in : list of float, optional
            List of 12 values representing the monthly temperature of heat transfer fluid entering the heating system. This argument is only considered if `monthly_T_set` is specified as well.
            
        monthly_T_set : list of float, optional
            List of 12 values representing the monthly setpoint temperature of the heating system. This argument is only considered if `monthly_T_in` is specified as well.
        
        temp_units : str, optional
            Units of the values in `Tamb_profile`. If not provided, °C is assumed.
        
        epsilon_fraction : float, optional
            Value that will be multiplied by the average production value and then added to the monthly production values. This is done in order to avoid divergence when the heat demand values are divided by the monthly production values. If not provided, it defaults to 0.1.

        Raises
        ------
        ValueError
            If the parameters do not match the expected format.

        Returns
        -------
        float
            Value between 0 and 3, representing the level of dependence of the heat demand on ambient temperature.

        """
        
        if Tamb_profile is None:
            warnings.warn("Class DemandProfile: Ambient temperature dependence could not be computed because Tamb_profile has not been specified.")
            return 0
        
        try:
            monthly_heat_demand = [ float( value ) for value in monthly_heat_demand ]
            assert len( monthly_heat_demand ) == 12
        except:
            raise ValueError("DemandProfile.compute_Tamb_dependence: Argument 'monthly_heat_demand' must be a list (or similar) with length 12.")
        
        try:
            Tamb_profile = [ float(value) for value in Tamb_profile ]
        except:
            raise ValueError( "DemandProfile.compute_Tamb_dependence: 'Tamb_profile' must be convertible to a list of floating point values." )
        
        if epsilon_fraction is None:
            epsilon_fraction = 0.1
        else:
            try:
                epsilon_fraction = float( epsilon_fraction )
                assert epsilon_fraction >= 0
            except:
                raise ValueError( "DemandProfile.compute_Tamb_dependence: 'epsilon_fraction' must be convertible to float. Its value must be >= 0." )
        
        if monthly_T_in is not None and monthly_T_set is not None:
            try:
                monthly_T_in = [ float( value ) for value in monthly_T_in ]
                monthly_T_set = [ float( value ) for value in monthly_T_set ]
                assert len( monthly_T_in ) == 12 and len( monthly_T_set ) == 12
            except:
                raise ValueError( "DemandProfile.compute_Tamb_dependence: Arguments 'monthly_T_in' and 'monthly_T_set' must be lists of 12 numeric values.")
            if not all( [ monthly_T_in[i] <  monthly_T_set[i] for i in range( 12 ) ] ):
                raise ValueError("DemandProfile.compute_Tamb_dependence: The values of 'monthly_T_in' must be smaller than the values of 'monthly_T_set'.")
        else:
            monthly_T_in = [ 0 ]*12
            monthly_T_set = [ 1 ]*12
        
        if monthly_production is None:
            monthly_production = month_days
            epsilon_fraction = 0
            
        if temp_units is not None:
            try:
                T = convert_units( 30 , temp_units, 'C' )
            except:
                raise TypeError(f"DemandProfile.compute_Tamb_dependence: Argument 'temp_units' ({temp_units}) is not valid.")
            
        if not ( temp_units is None or temp_units in [ 'C', '°C' ] ):
            Tamb_profile = convert_units(Tamb_profile, temp_units, 'C')
            
        Tamb_profile = DemandProfile._reduce_profile(Tamb_profile, 365)
            
        epsilon = epsilon_fraction*float(np.mean(monthly_production))
            
        monthly_normalized_demand = [ monthly_heat_demand[i]/(monthly_production[i] + epsilon ) for i in range(len(monthly_heat_demand)) ]
        monthly_normalized_demand = [ monthly_normalized_demand[i]/( monthly_T_set[ i ] - monthly_T_in[ i ] ) for i in range( len( monthly_T_set ) ) ]
        total_normalized_demand = sum(monthly_normalized_demand)
        
        def mse_result( coeff_list ):
            
            temp_to_factor = DemandProfile.define_temp_to_factor_func( coeff_list[0] )
            daily_factors = [ temp_to_factor(Tamb_profile[i]) for i in range(len(Tamb_profile)) ]
            sum_daily_factors = sum(daily_factors)
            assert sum_daily_factors > 0
            predicted_normalized_demand = [ total_normalized_demand*sum( daily_factors[ monthly_cummulated_days[month] : monthly_cummulated_days[month + 1] ] )/sum_daily_factors for month in range(12) ]
            return _mean_squared_error(monthly_normalized_demand, predicted_normalized_demand)
        
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
            raise ValueError("DemandProfile.compute_Tamb_dependence: It was not possible to solve the minimization problem.")
            
        dependence_coeff = float (minimize_result['x'][0])
        
        return dependence_coeff
    
    def _compute_yearly_profiles(self):
        """
        Private method that that generates the attributes "flowrate_profile", "demanded_power_profile", "T_in_profile", and "T_set_profile" for the DemandProfile instance.
        
        These attributes contain the data that will be returned thereafter when the method 'get_demand_conditions' is called.
        
        Each of these attributes is a list of 365 lists (one for each day of the year, from January 1st to December 31st).
        Each one of those 365 lists contains 1440 values; one for every minute of the day, starting at 00:00 and ending at 23:59.

        Returns
        -------
        None

        """
        
        attributes_needed = [
            "monthly_T_set",
            "monthly_T_in",
            "monthly_heat_demand",
            "weekly_demand_profile",
            "Tamb_dependence_mode",
            "smooth_Tamb_profile",
            "year",
        ]
        
        for attribute in attributes_needed:
            if hasattr( self, '_' + attribute ) is False:
                raise ValueError(f"DemandProfile._compute_yearly_profiles: Class instance does not have the needed attribute: {attribute}")
        
        monthly_Tset = self._monthly_T_set
        monthly_Tin = self._monthly_T_in
        monthly_heat_demand = self._monthly_heat_demand
        monthly_production = self._monthly_production
        weekly_demand_profile = self._weekly_demand_profile
        Tamb_dependence = self._Tamb_dependence
        Tamb_dependence_mode = self._Tamb_dependence_mode
        Tamb_profile = self._Tamb_profile
        smooth_Tamb_profile = self._smooth_Tamb_profile
        starting_week_day = datetime(self._year, 1, 1).weekday()
        
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
                
                self._Tamb_dependence = self.compute_Tamb_dependence(
                    
                    monthly_heat_demand,
                    Tamb_profile,
                    monthly_production = monthly_production,
                    monthly_T_in = self._monthly_T_in,
                    monthly_T_set = self._monthly_T_set )
                
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
            delta_h_this_month = self._fluid.state( T = monthly_Tset[month] ).h -  self._fluid.state( T = monthly_Tin[month] ).h
            
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
                raise ValueError(f"compute_minutal_demand_profiles: sum of scaling factors is negative or equal to zero for the following month: {month_names[month]}. Check the temperature dependence provided.")
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
    
    @staticmethod
    def _Tin_from_meteo_profile( meteo_profile ):
        """
        Private method that takes a meteo_profile.MeteoProfile instance and creates a list of 12 monthly values for mains water temperature.
        
        This is done when the user specifies that the heated water enters the heating system from the distribution network.

        Parameters
        ----------
        meteo_profile : meteo_profile.MeteoProfile instance
            Object from which the mains water temperature profile is extracted.

        Returns
        -------
        result : list
            List of 12 monthly values, computed by averaging the values of the profile extracted from meteo_profile.

        """
        
        result = []
        
        for month in range( 1, 13 ):
            month_df = meteo_profile.get_conditions( month = month )
            result.append( float( np.mean( month_df[ "Tmains" ].values ) ) )
            
        return result
    
    def _return_single_instant(self, month, day, hour, minute ):
        """
        Private method that returns the demand conditions for a signle instant in time.

        Parameters
        ----------
        month : int
            Month number from 1 to 12.
        day : int
            Day number from 1 to 28, 30, or 31, depending on the month.
        hour : int
            Hour from 0 to 23.
        minute : int
            Minute from 0 to 59.

        Returns
        -------
        flowrate : float
            Flowrate value (kg/s).
        demanded_power : float
            Demanded power value (W).
        T_in : float
            Inlet temperature value (C).
        T_set : float
            Setpoint temperature value (C).

        """
        
        day_number = monthly_cummulated_days[ month - 1 ] + day - 1
        minute_number = hour*60 + minute
        
        if month == 2 and day == 29:
            warnings.warn("Class DemandProfile: Data for February 29 was requested. Leap years are not supported. Data for February 28 is returned instead.")
            day = 28
        
        flowrate = self._flowrate_profile[ day_number ][ minute_number ]
        demanded_power = self._demanded_power_profile[ day_number ][ minute_number ]
        T_in = self._T_in_profile[ day_number ][ minute_number ]
        T_set = self._T_set_profile[ day_number ][ minute_number ]
        
        return flowrate, demanded_power, T_in, T_set
    
    def _return_lists_from_date_range(self, date_range ):
        """
        Private method that takes a pandas.DatetimeIndex instance and generates 4 lists of values containing the demand conditions (flowrate, demanded_power, T_in, T_set) for each instant contained in the input

        Parameters
        ----------
        date_range : pandas.DateTimeindex
            Object that specifies the set of instants for which the demand conditions must be returned.

        Raises
        ------
        ValueError
            If the input value does not match the expected type.

        Returns
        -------
        flowrate_list : list of float
            List containing the flowrate values (kg/s).
        demanded_power_list : list of float
            List containing the demanded power values (W).
        T_in_list : list of float
            List containing the inlet temperature values (C).
        T_set_list : list of float
            List containing the setpoint temperature values (C).

        """
        
        if not type( date_range ) is pd.DatetimeIndex:
            raise ValueError("DemandProfile._return_lists_from_date_range: type of date_range must be pandas.DatetimeIndex.")
        
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
        """
        Method to obtain the demand conditions for a certain instant or time period.
        
        The standard way of obtaining the demand conditions for a single instant in time is by providing a `datetime.datetime <https://docs.python.org/3/library/datetime.html#datetime-objects>`_ instance as the only positional argument. See ****kwargs** for an alternative way.
        
        The conditions for a time period can be obtained either by providing two `datetime.datetime <https://docs.python.org/3/library/datetime.html#datetime-objects>`_ instances, or a single `pandas.DatetimeIndex <https://pandas.pydata.org/docs/reference/api/pandas.DatetimeIndex.html>`_, as positional arguments.
        In the former case, a `pandas.DatetimeIndex` instance is generated internally using the first datetime as start and the second datetime as end. See ****kwargs** to customize other details of the `DatetimeIndex` instance.
        
        If the conditions for a single instant are asked for, this method returns a `dictionary <https://docs.python.org/3/tutorial/datastructures.html#dictionaries>`_ with the following keys:
            
            - `"flowrate"`: Flowrate value in kg/s, unless a different unit is specified by the user.
            - `"demanded_power"`: Thermal power demanded, obtained from the flowrate and the enthalpy change between the inlet temperature and the setpoint. The unit is W unless a different unit is specified by the user.
            - `"T_in"`: Temperature of the flow when it enters the heating system. The units are C unless a different unit is specified by the user.
            - `"T_set"`: Setpoint of the heating system, i.e. the temperature with which the heat transfer fluid is meant to leave the heating system. The units are C unless other units are specified by the user.
            
        If the conditions for a time period are asked for, this method returns a `pandas.DataFrame <https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.html>`_. The first column of the `DataFrame` is called `"timestamp"` and it stores all the instants considered when computing the result.
        The other columns of the DataFrame have the same names as the keys of the dictionary mentioned above, and store the same variables.
            
        Parameters
        ----------
        *args : `datetime.datetime` or similar, or `pandas.DatetimeIndex`
            Positional arguments. No keyword allowed.
            
            The function returns the results for a single instant in time if only one `datetime.datetime` instance is provided as positional argument.
            
            On the other hand, the function returns the result for a time period if:
                
                - Two `datetime.datetime` instances are provided as positional arguments.
                - A `pandas.DatetimeIndex` instance is provided as the only positional argument.
        
        **kwargs :
            Keyword arguments. Accepted argument names are:
                
                - `month`, `day`, `hour` and `minute`, when provided together, can replace a `datetime.datetime` instance to get the conditions for a single instant in time. The expected type for all these arguments is `int`, with ranges 1 to 12, 1 to 31, 0 to 23, and 0 to 59, respectively.
                
                - `flowrate_units`, `power_units`, and `temp_units` can be used to customize the units for the values of flowrate, power, and temperature, respectively. `T_units` is an allowed alias for `temp_units`. See :doc:`/units/units`.
                
                - `inclusive`, `freq`, and `tz` can be used to customize the generation of the `pandas.DatetimeIndex` instance. These keyword arguments are thus only taken into account when two `datetime.datetime` instances are provided as positional arguments. See `pandas.date_range <https://pandas.pydata.org/docs/reference/api/pandas.date_range.html>`_

        Returns
        -------
        `dict` or `pandas.DataFrame`
            A `dictionary <https://docs.python.org/3/tutorial/datastructures.html#dictionaries>`_ is returned when the conditions for a single instant in time are asked for. This dictionary has the following keys:
                
                - `"flowrate"`: Flowrate value in kg/s, unless a different unit is specified by the user (see ****kwargs**).
                - `"demanded_power"`: Thermal power demanded, obtained from the flowrate and the enthalpy change between the inlet temperature and the setpoint. The unit is W unless a different unit is specified by the user (see ****kwargs**).
                - `"T_in"`: Temperature of the flow when it enters the heating system. The unit is °C unless a different unit is specified by the user (see ****kwargs**).
                - `"T_set"`: Setpoint of the heating system, i.e. the temperature with which the heat transfer fluid is meant to leave the heating system. The unit is °C unless other units are specified by the user (see ****kwargs**).
            
            A `pandas.DataFrame <https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.html>`_ is returned when the conditions for a time period are asked for. The first column of the `DataFrame` is called `"timestamp"` and it stores all the instants considered when computing the result.
            The other columns of the DataFrame have the same names as the keys of the dictionary mentioned above, and store the same variables.
        """
        
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
                    raise ValueError("DemandProfile.get_demand_conditions: Unable to obtain attributes 'month', 'day', 'hour' and 'minute' from input.")
                month = int(dt.month)
                day = int(dt.day)
                hour = int(dt.hour)
                minute = int(dt.minute)
                
            try:
                month = int(month)
                day = int(day)
                hour = int(hour)
                minute = int(minute)
            except:
                raise ValueError("DemandProfile.get_demand_conditions: Values 'month', 'day', 'hour', and 'minute' must be convertible to type 'float'.")
            
            if not (month >= 1 and month <= 12):
                raise ValueError("DemandProfile._return_single_instant: Month value is not within the accepted range.")
            if not ( ( day >= 1 and day <= month_days[ month - 1 ] ) or ( month == 2 and day == 29 ) ):
                raise ValueError("DemandProfile._return_single_instant: Day value is not within the accepted range.")
            if not (hour >= 0 and hour <= 23):
                raise ValueError("DemandProfile._return_single_instant: Hour value is not within the accepted range.")
            if not (minute >= 0 and minute <= 59):
                raise ValueError("DemandProfile._return_single_instant: Minute value is not within the accepted range.")
            
            flowrate, demanded_power, T_in, T_set = self._return_single_instant(month, day, hour, minute)
            
            if "flowrate_units" in kwargs:
                fluid_density = self._fluid.state( T = T_set ).D
                flowrate = convert_units(flowrate, "kg/s", kwargs[ "flowrate_units" ], density = fluid_density)
            if "power_units" in kwargs:
                demanded_power = convert_units(demanded_power, 'W', kwargs[ "power_units" ])
            if "temp_units" in kwargs:
                T_in = convert_units(T_in, 'C', kwargs[ "temp_units" ])
                T_set = convert_units(T_set, 'C', kwargs[ "temp_units" ])
            elif "T_units" in kwargs:
                T_in = convert_units(T_in, 'C', kwargs[ "T_units" ])
                T_set = convert_units(T_set, 'C', kwargs[ "T_units" ])
                
            return {
                
                'flowrate': flowrate,
                'demanded_power': demanded_power,
                'T_in': T_in,
                'T_set': T_set,
                
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
                    raise ValueError("DemandProfile.get_demand_conditions: No pandas.DatetimeIndex could be generated from the arguments provided.")
                
            flowrate_list, demanded_power_list, T_in_list, T_set_list = self._return_lists_from_date_range( date_range )
            
            if "flowrate_units" in kwargs:
                # Density must be computed for each value of T_set which could be variable
                # Time is spared by indentifying portions with constant setpoint temperature
                
                a = np.asarray(T_set_list)
                T_set_breaks = a[1:] != a[:-1]
                T_set_change_indexes = np.flatnonzero( T_set_breaks ) + 1
                T_set_change_indexes = [ 0 ] + T_set_change_indexes.astype(float).tolist() + [ len( T_set_list ) ]
                
                flowrates_converted = []
                for i in range( len( T_set_change_indexes ) - 1 ):
                    index_start = T_set_change_indexes[ i ]
                    index_end = T_set_change_indexes[ i + 1 ]
                    fluid_density = self._fluid_density.state( T = T_set_list[ index_start ] ).D
                    flowrates_converted = np.concatenate( ( flowrates_converted, convert_units( flowrate_list[ index_start : index_end ], "kg/s", kwargs[ "flowrate_units" ], density = fluid_density ) ), )
                
                flowrate_list = flowrates_converted
                assert len( flowrate_list ) == len( T_set_list )
            if "power_units" in kwargs:
                demanded_power_list = convert_units( demanded_power_list, 'W', kwargs[ "power_units" ] )
            if "temp_units" in kwargs:
                T_in_list = convert_units( T_in_list, 'C', kwargs[ "temp_units" ] )
                T_set_list = convert_units( T_set_list, 'C', kwargs[ "temp_units" ] )
            elif "T_units" in kwargs:
                T_in_list = convert_units( T_in_list, 'C', kwargs[ "T_units" ] )
                T_set_list = convert_units( T_set_list, 'C', kwargs[ "T_units" ] )
            
            df = pd.DataFrame.from_dict( {
                
                "timestamp": date_range,
                "flowrate": flowrate_list,
                "demanded_power": demanded_power_list,
                "T_in": T_in_list,
                "T_set": T_set_list, } )
            
            return df
        
        else:
            raise ValueError("DemandProfile.get_demand_conditions: Incorrect arguments.")