# -*- coding: utf-8 -*-
"""
Created on Tue Oct 27 15:44:20 2026

@author: Adrian Riebel Brummer
"""

import pandas as pd
from .operating_conditions import OperatingConditions
from .meteo_profile import MeteoProfile
from .devices import SystemInlet, Device
from .solar import SolarField
from .storage import StorageTank
from .heat_exchanger import HeatExchanger
from .pump import Pump
from .controller import SolarController, LoadTempController, TankChargeController, ExcessTempShutDown
from .fluids import Fluid
import warnings

class SimulationResult:
    
    def __init__(self):
        self._results_dict = {  }
        
    @property
    def df(self):
        return pd.DataFrame.from_dict( self._results_dict )
        
    def record_results( self, results_dict ):
        for key in results_dict:
            if key in self._results_dict:
                self._results_dict[ key ].append( results_dict[ key ] )
            else:
                self._results_dict[ key ] = [ results_dict[ key ] ]

class Simulation:
    """
    Class to simulate a thermal system operating during a whole year.
    
    Parameters
    ----------
    operating_conditions : :doc:`OperatingConditions </operating_conditions/operating_conditions>`
        Object that provides the operating conditions of the system (weather and thermal demand).
    
    devices_list : list of :ref:`Device <device_class>` or inherited classes
        List of components of the thermal system. The components should be ready to be used
        in a simulation; this implies:
            
            - The connections between them must already be established.
            - The convergence criteria of all components must be set.
    
    time_step_recording_function : func
        Function that takes an instance of SimulationResult, carries out the
        necessary calculations based on the results delivered by the components of the
        thermal system, and records those results in the SimulationResults instance.
        
    Attributes
    ----------
    operating_conditions : :doc:`OperatingConditions </operating_conditions/operating_conditions>`
        Same as the argument provided at initialization.
    
    devices_list : list of :ref:`Device <device_class>` or inherited classes
        Same as the argument provided at initialization.
    
    time_step_recording_function : func
        Same as the argument provided at initialization.
    
    """
    
    def __init__( self, operating_conditions, devices_list, time_step_recording_function ):
        
        self.operating_conditions = operating_conditions
        self.devices_list = devices_list
        self.time_step_recording_function = time_step_recording_function
        
    @property
    def operating_conditions(self):
        if not hasattr( self, "_operating_conditions" ):
            raise AttributeError( "Simulation: Attribute 'operating_conditions' has not been specified." )
        return self._operating_conditions
    
    @operating_conditions.setter
    def operating_conditions(self, value):
        if not isinstance( value, OperatingConditions ):
            raise TypeError("Simulation: Attribute 'operating_conditions' must be an instance of sercpy.operating_conditions.OperatingConditions.")
        self._operating_conditions = value
    
    @property
    def devices_list(self):
        if not hasattr( self, "_devices_list" ):
            raise AttributeError("Simulation: Attribute 'devices_list' has not been specified.")
        return self._devices_list
    
    @devices_list.setter
    def devices_list(self, value):
        if not ( type( value ) is list and all( [ isinstance( element, Device ) for element in value  ] ) ):
            raise TypeError("Simulation: Attribute 'devices_list' must be a list of instances of sercpy.devices.Device")
        self._devices_list = value
        
    @property
    def time_step_recording_function(self):
        if not hasattr( self, "_time_step_recording_function" ):
            raise AttributeError("Simulation: Attribute 'time_step_recording_function' has not been specified.")
        return self._time_step_recording_function
    
    @time_step_recording_function.setter
    def time_step_recording_function(self, value):
        if not callable( value ):
            raise TypeError("Simulation: Attribute 'time_step_recording_function' must be a callable element.")
        self._time_step_recording_function = value
    
    def compute_time_step( self , time_step_number, results_record ):
        
        conditions = self._operating_conditions.get_conditions( time_step_number )
        
        it = 0
        while True:
            
            for device in self._devices_list:
                
                device.compute_outputs( conditions, it )
                
            it = it + 1
            
            if all([ device.convergence for device in self._devices_list ] ):
                convergence = True
                break
            
            if it == self._max_iterations:
                convergence = False
                break
            
        for device in self._devices_list:
            device.update_state()
        
        if time_step_number >= 0:
            self.record_time_step( results_record, convergence )
                
    def run( self, pre_heating_days = 0 ):
        
        results_record = SimulationResult()
        
        for attribute_name in [
                
                "max_iterations",
                "devices_list", ]:
            
            if not hasattr( self, "_" + attribute_name ):
                class_name = self.__class__.__name__
                raise AttributeError( f"{ class_name }: Attribute '{attribute_name}' has not been defined." )
        
        pre_heating_time_steps = self._operating_conditions.time_steps_per_day*pre_heating_days
        
        for time_step_number in range( - pre_heating_time_steps, self._operating_conditions.time_steps_per_year ):
            self.compute_time_step( time_step_number, results_record )
            
        return results_record

class HeatingSystem1( Simulation ):
    
    def __init__(
            
            self, *,
            
            solar_field,
            operating_conditions,
            storage_tank = None,
            HX1 = None,
            HX2 = None,
            solar_field_pump = None,
            tank_charge_pump = None,
            tank_discharge_pump = None,
            tank_max_temp = None,
            shutdown_hysteresis_dT = None,
            tank_charge_controller = None,
            tank_charge_min_dT = None,
            solar_field_fluid = None,
            tank_discharge_turnoff_dT = None,
            tank_discharge_turnon_dT = None,
            relative_tolerance = None,
            max_iterations = None, ):
        
        if not isinstance(solar_field, SolarField):
            raise TypeError("HeatingSystem1: Argument 'solar_field' must be an instance of sercpy.solar.SolarField'.")
        self._solar_field = solar_field
        
        if not isinstance( operating_conditions, OperatingConditions ):
            raise TypeError("HeatingSystem1: Argument 'solar_field' must be an instance of sercpy.operating_conditions.OperatingConditions'.")
        self._operating_conditions = operating_conditions
        
        if storage_tank is None:
            
            if tank_max_temp is None:
                tank_max_temp = max( [ self._operating_conditions.max_Tin + 30, self._operating_conditions.max_Tset + 20 ] )
            
            else:
                try:
                    tank_max_temp = float( tank_max_temp )
                except:
                    raise TypeError("HeatingSystem1: Argument 'tank_max_temp' must be a numeric value.")
                if not ( tank_max_temp >= 30 and tank_max_temp <= 250 ):
                    raise ValueError("HeatingSystem1: Argument 'tank_max_temp' must be in the range 30°C <= tank_max_temp <= 250°C.")
                if tank_max_temp <= self._operating_conditions.max_Tin:
                    raise ValueError(f"HeatingSystem1: Maximum allowed temperature of the tank (argument 'tank_max_temp', value {tank_max_temp} is lower than (or equal to) the system's inlet temperature: {self._operating_conditions.max_Tin})")
            
            tank_fluid_T_ref = ( tank_max_temp + self._operating_conditions.min_Tin ) / 2
            
            if tank_max_temp <= 120:
                tank_fluid = Fluid( 'water', p = 400000, T_ref = tank_fluid_T_ref  )
                tank_volume = 0.12 * self._solar_field.collection_area
            else:
                tank_fluid = Fluid( 'therminol 66', T_ref = tank_fluid_T_ref )
                tank_volume = 0.26 * self._solar_field.collection_area
            
            
            tank_aspect_ratio = 1.5
            self._storage_tank = StorageTank(
                
                volume = tank_volume,
                aspect_ratio = tank_aspect_ratio,
                stored_fluid = tank_fluid )
            
        else:
            if not isinstance(storage_tank, StorageTank):
                raise TypeError("HeatingSystem1: Argument 'storage_tank' must be an instance of sercpy.storage.StorageTank.")
            self._storage_tank = storage_tank
            
            if storage_tank.stored_fluid.can_boil:
                tank_max_allowed_temp = storage_tank.stored_fluid.T_sat - 5
            else:
                tank_max_allowed_temp = storage_tank.stored_fluid.T_max - 2
            
            if tank_max_temp is None:
                tank_max_temp = max( [ self._operating_conditions.max_Tin + 30, self._operating_conditions.max_Tset + 20 ] )
                if tank_max_temp < tank_max_allowed_temp:
                    tank_max_temp = max( [ self._operating_conditions.max_Tin + 20, self._operating_conditions.max_Tset + 10 ] )
                if tank_max_temp < tank_max_allowed_temp:
                    if 'Glycol' in storage_tank.stored_fluid.fluid_name:
                        raise ValueError("HeatingSystem1: Models for water-glycol mixtures are limited to 120°C. The system's operating temperature is too high for this fluid to be used as energy-storing fluid inside the tank. Consider switching to a thermal oil as energy storing fluid.")
                    raise ValueError("HeatingSystem1: The boiling temperature of the fluid stored inside the tank is too low for the system's operating temperature. Consider switching to a thermal oil as energy storing fluid, or rising the pressure of the water inside the tank.")
            else:

                try:
                    tank_max_temp = float( tank_max_temp )
                except:
                    raise TypeError("HeatingSystem1: Argument 'tank_max_temp' must be a numeric value.")
                if not ( tank_max_temp >= 30 and tank_max_temp <= 250 ):
                    raise ValueError("HeatingSystem1: Argument 'tank_max_temp' must be in the range 30°C <= tank_max_temp <= 250°C.")
                if tank_max_temp <= self._operating_conditions.max_Tin:
                    raise ValueError(f"HeatingSystem1: Maximum allowed temperature of the tank (argument 'tank_max_temp', value {tank_max_temp} is lower than (or equal to) the system's inlet temperature: {self._operating_conditions.max_Tin})")
                if tank_max_temp < tank_max_allowed_temp:
                    if 'Glycol' in storage_tank.stored_fluid.fluid_name:
                        raise ValueError(f"HeatingSystem1: Models for water-glycol mixtures are limited to 120°C. The maximum temperature set for the tank ({tank_max_temp}°C) is too close to this limit or higher than it. Consider switching to a thermal oil, or pressurized water, as energy storing fluid.")
                    raise ValueError(f"HeatingSystem1: The boiling temperature of the fluid stored inside the tank is too low for the maximum temperature set for the tank ({tank_max_temp}°C). Consider switching to a thermal oil as energy storing fluid, or rising the pressure of the water inside the tank.")
        
        if not self._storage_tank.io_positions_defined:
            self._storage_tank.io_relative_heights = [ ( 1, 0 ), ( 0, 1 ) ]
        
        if HX1 is None:
            self._HX1 = HeatExchanger(
                rated_effectiveness = 0.85,
                rated_water_flowrate = self._solar_field.rated_flowrate )
        else:
            if not isinstance(HX1, HeatExchanger):
                raise TypeError("HeatingSystem1: Argument 'HX1' must be an instance of sercpy.heat_exchanger.HeatExchanger.")
            self._HX1 = HX1
        
        if HX2 is None:
            self._HX2 = HeatExchanger(
                rated_effectiveness = 0.85,
                rated_water_flowrate = self._operating_conditions.max_flowrate )
        else:
            if not isinstance(HX2, HeatExchanger):
                raise TypeError("HeatingSystem1: Argument 'HX2' must be an instance of sercpy.heat_exchanger.HeatExchanger.")
            self._HX2 = HX2
        
        if solar_field_pump is None:
            self._solar_field_pump = Pump( self._solar_field.rated_flowrate )
        else:
            if not isinstance( solar_field_pump, Pump ):
                raise TypeError("HeatingSystem1: Argument 'solar_field_pump' must be an instance of sercpy.pump.Pump.")
            self._solar_field_pump = solar_field_pump
                
        if tank_charge_pump is None:
            self._tank_charge_pump = Pump( self._solar_field.rated_flowrate )
        else:
            if not isinstance( tank_charge_pump, Pump ):
                raise TypeError("HeatingSystem1: Argument 'tank_charge_pump' must be an instance of sercpy.pump.Pump.")
            self._tank_charge_pump = tank_charge_pump
            
        if tank_discharge_pump is None:
            self._tank_discharge_pump = Pump( self._operating_conditions.max_flowrate )
        else:
            if not isinstance( tank_discharge_pump, Pump ):
                raise TypeError("HeatingSystem1: Argument 'tank_discharge_pump' must be an instance of sercpy.pump.Pump.")
            self._tank_discharge_pump = tank_discharge_pump
        
        self._system_inlet = SystemInlet()
        
        self._solar_field.set_connections( inlet = self._solar_field_pump.outlet )
        self._solar_field_pump.set_connections( inlet = self._HX1.outlet_source )
        self._HX1.set_connections( inlet_source = self._solar_field.outlet, inlet_load = self._tank_charge_pump.outlet )
        self._tank_charge_pump.set_connections( inlet = self._storage_tank.outlet_1 )
        self._storage_tank.set_connections( inlet_1 = self._HX1.outlet_load, inlet_2 = self._HX2.outlet_source )
        self._tank_discharge_pump.set_connections( inlet = self._storage_tank.outlet_2 )
        self._HX2.set_connections( inlet_source = self._tank_discharge_pump.outlet, inlet_load = self._system_inlet.outlet )
        
        solar_field_fluid = Fluid("Ethylene Glycol 30%", T_ref = 60)
        self._solar_field.outlet.flowrate = 0
        self._solar_field.outlet.state = solar_field_fluid.state( T = 40 )
        
        self._security_shutdown_controller = ExcessTempShutDown(
            
            tank = self._storage_tank,
            tank_max_temp = tank_max_temp,
            hysteresis = shutdown_hysteresis_dT )

        self._solar_controller = SolarController(
            
            min_irradiance = 150,
            controlled_pump = self._solar_field_pump,
            security_shutdown = self._security_shutdown_controller )
        
        if tank_charge_controller:
            
            if tank_charge_min_dT is None:
                tank_charge_min_dT = 5
            
            try:
                tank_charge_min_dT = float( tank_charge_min_dT )
            except:
                raise TypeError("HeatingSystem1: Argument 'tank_charge_min_dT' must be convertible to type 'float'.")
            if not tank_charge_min_dT > 0:
                raise ValueError("HeatingSystem1: Argument 'tank_charge_min_dT' must be larger than zero.")
            
            self._tank_to_SF_controller = TankChargeController(
                
                controlled_pump = self._tank_charge_pump,
                heat_exchanger = self._HX1,
                min_dT = tank_charge_min_dT,
                temp_tolerance = tank_charge_min_dT*0.1,
                heat_source_controller = self._solar_controller,
                last_signal_weight = 0,
                iteration_cycle = [ 0, 0, 1, 0 ] )
            
            tank_to_load_controller_iteration_cycle = [ 1, 0, 0, 0, ]
            
        else:
            self._tank_charge_pump.set_connections( controller = self._solar_controller )
            tank_to_load_controller_iteration_cycle = [ 1, 0, ]
        
        self._tank_to_load_controller = LoadTempController(
            
            controlled_pump = self._tank_discharge_pump,
            heat_exchanger = self._HX2,
            tank = self._storage_tank,
            turn_on_dT = self._operating_conditions.min_dT*0.3,
            turn_off_dT = self._operating_conditions.min_dT*0.1,
            temp_tolerance = self._operating_conditions.min_dT*0.02,
            last_signal_weight = 0,
            iteration_cycle = tank_to_load_controller_iteration_cycle )
        
        self._devices_list = [
            
            self._system_inlet,
            self._security_shutdown_controller,
            self._solar_controller,
            self._solar_field,
            self._solar_field_pump,
            self._HX1,
            self._tank_charge_pump,
            self._storage_tank,
            self._tank_discharge_pump,
            self._HX2, ]
        
        if tank_charge_controller:
            
            self.devices_list = self.devices_list + [
                
                self._tank_to_SF_controller,
                self._tank_to_load_controller ]
        
        else:
            self.devices_list = self.devices_list + [ self._tank_to_load_controller ]
            
        if relative_tolerance is None:
            relative_tolerance = 1e-3
        else:
            try:
                relative_tolerance = float( relative_tolerance )
            except:
                raise TypeError(f"HeatingSystem1: Argument 'relative_tolerance' must a numeric value, not {type(relative_tolerance)}.")
            if not ( relative_tolerance >= 1e-8 and relative_tolerance <= 5e-2 ):
                raise ValueError("HeatingSystem1: Argument 'relative_tolerance' must be in the range: 1e-8 <= relative_tolerance <= 5e-2.")
            
        
        for device in self._devices_list:
            
            device.set_convergence_criteria(
                
                relative_tolerance = relative_tolerance,
                temp_normalization_range = operating_conditions.min_dT )
            
        if max_iterations is None:
            self._max_iterations = 200
        else:
            try:
                assert max_iterations.is_integer()
            except:
                raise TypeError("HeatingSystem1: Argument 'max_iterations' must be an integer value.")
            max_iterations = int( max_iterations )
            self._max_iterations = max_iterations
        
    def record_time_step( self, results_record, convergence ):
        
        solar_field_power = self._solar_field.useful_power
        useful_power = self._HX2.useful_power
        
        results_record.record_results( {
            
            'solar_field_power': solar_field_power,
            'useful_power': useful_power,
            'convergence': 1*convergence } )