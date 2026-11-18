# -*- coding: utf-8 -*-
"""
Created on Tue Oct 27 15:44:20 2026

@author: Adrian Riebel Brummer
"""

from .operating_conditions import OperatingConditions
from .meteo_profile import MeteoProfile
from .devices import SystemInlet, Device
from .solar import SolarField
from .storage import StorageTank
from .heat_exchanger import HeatExchanger
from .pump import Pump
from .controller import SolarController, LoadTempController, TankChargeController
from .fluids import Fluid
import warnings

class SimulationResult:
    
    def __init__(self):
        
        self._results_dict = {  }
        
    def record_results( self, results_dict ):
        
        for key in results_dict:
            
            if key in self._results_dict:
                
                self._results_dict[ key ].append( results_dict[ key ] )
            
            else:
                
                self._results_dict[ key ] = [ results_dict[ key ] ]

class Simulation:
    
    def __init__( self, operating_conditions, devices_list ):
        
        self._operating_conditions = operating_conditions
        self._devices_list = devices_list
        
    @property
    def operating_conditions(self):
        if not hasattr( self, "_operating_conditions" ):
            raise AttributeError("Simulation: Attribute 'operating_conditions' has not been specified.")
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
        
        if not hasattr( self, "record_time_step" ):
            warnings.warn("Simulation.run: ")
        
        results_record = SimulationResult()
        
        for attribute_name in [
                
                "max_iterations",
                "devices_list",
                
                ]:
            
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
            
            operating_conditions,
            solar_field,
            storage_tank,
            max_iterations,
            
            ):
        
        self._operating_conditions = operating_conditions
        
        self._solar_field = solar_field
        self._storage_tank = storage_tank
        
        if not self._storage_tank.io_positions_defined:
            self._storage_tank.set_io_relative_heights( [ ( 1, 0 ), ( 0, 1 ) ] )
        
        self._max_iterations = max_iterations
        
        self._HX1 = HeatExchanger(
            
            rated_effectiveness = 0.85,
            rated_water_flowrate = self._solar_field.rated_flowrate )
        
        self._solar_field_pump = Pump( self._solar_field.rated_flowrate )
        self._tank_to_SF_pump = Pump( self._solar_field.rated_flowrate )
        
        self._tank_to_load_pump = Pump( self._operating_conditions.max_flowrate )
        
        self._HX2 = HeatExchanger( 
            
            rated_effectiveness = 0.85,
            rated_water_flowrate = self._operating_conditions.max_flowrate )
        
        self._system_inlet = SystemInlet()
        
        self._solar_controller = SolarController( min_irradiance = 150 )
        
        self._solar_field.set_connections( inlet = self._solar_field_pump.outlet )
        self._solar_field_pump.set_connections( inlet = self._HX1.outlet_source, control_signal = self._solar_controller.control_signal )
        self._HX1.set_connections( inlet_source = self._solar_field.outlet, inlet_load = self._tank_to_SF_pump.outlet )
        self._tank_to_SF_pump.set_connections( inlet = self._storage_tank.outlet_1 )
        self._storage_tank.set_connections( inlet_1 = self._HX1.outlet_load, inlet_2 = self._HX2.outlet_source )
        self._tank_to_load_pump.set_connections( inlet = self._storage_tank.outlet_2 )
        self._HX2.set_connections( inlet_source = self._tank_to_load_pump.outlet, inlet_load = self._system_inlet.outlet )
        
        solar_field_fluid = Fluid("Ethylene Glycol 30%", T_ref = 60)
        self._solar_field.outlet.flowrate = 0
        self._solar_field.outlet.state = solar_field_fluid.state( T = 40 )
        
        self._tank_to_SF_controller = TankChargeController(
            
            controlled_pump = self._tank_to_SF_pump,
            heat_exchanger = self._HX1,
            min_temp_difference = 5,
            temp_tolerance = 0.5,
            heat_source_controller = self._solar_controller,
            tank = self._storage_tank,
            tank_max_temp = 100,
            tank_hysteresis = 10,
            last_signal_weight = 0,
            iteration_cycle = [ 0, 0, 1, 0 ] )
        
        self._tank_to_load_controller = LoadTempController(
            
            controlled_pump = self._tank_to_load_pump,
            heat_exchanger = self._HX2,
            tank = self._storage_tank,
            turn_on_dT = self._operating_conditions.min_dT*0.3,
            turn_off_dT = self._operating_conditions.min_dT*0.1,
            temp_tolerance = self._operating_conditions.min_dT*0.02,
            last_signal_weight = 0,
            iteration_cycle = [ 1, 0, 0, 0, ] )
        
        self._devices_list = [
            
            self._system_inlet,
            self._solar_controller,
            self._solar_field,
            self._solar_field_pump,
            self._HX1,
            self._tank_to_SF_pump,
            self._storage_tank,
            self._tank_to_load_pump,
            self._HX2,
            self._tank_to_SF_controller,
            self._tank_to_load_controller ]
        
        for device in self._devices_list:
            
            device.set_convergence_criteria(
                
                relative_tolerance = 1e-3,
                temp_normalization_range = operating_conditions.min_dT )
        
    def record_time_step( self, results_record, convergence ):
        
        solar_field_power = self._solar_field.useful_power
        useful_power = self._HX2.useful_power
        
        results_record.record_results( {
            
            'solar_field_power': solar_field_power,
            'useful_power': useful_power,
            'convergence': 1*convergence } )