# -*- coding: utf-8 -*-
"""
Created on Sat Nov 14 23:18:38 2026

@author: Adrian Riebel Brummer
"""

from .devices import Device

class Controller( Device ):
    """
    Base class to implement a controller.
    
    As a base class, this class is not meant to be used directly, but to implement inherited classes.
    
    Its initializing function takes no arguments and only creates a ControlSignal instance
    as attribute (and assigns the value 1 to the signal).
    
    To implement an inherited Controller class, the user should implement the
    method `compute_outputs`, which should update the value of the control signal
    produced by the controller (see the attribute `control_signal`),
    and the attribute 'convergence' (see the `introduction to sercpy devices </devices/devices>`).
    
    Attributes
    ----------
    control_signal : :ref:`ControlSignal <control_signal_class>`
        Instance of sercpy.controller.ControlSignal. This object is used to store the signal
        value determined by the controller, and to deliver it to other devices that need it to
        operate.
        
    convergence : bool
        Inherited from :doc:`Device </devices/devices>`
        
    Methods
    -------
    compute_outputs
        This method must be implemented by the user since it it what defines
        the actions of the controller on other devices. See 
    
    """
    
    def __init__(self):
        
        self._control_signal = 1
        self._convergence = True
        
    @property
    def control_signal(self):
        if not hasattr( self, "_control_signal" ):
            class_name = self.__class__.__name__
            raise AttributeError(f"{class_name}: Control signal value has not been defined.")
        return self._control_signal
    
    @control_signal.setter
    def control_signal(self, value):
        try:
            value = float( value )
        except:
            raise TypeError("{class_name}: signal value must be a float.")
        if not ( value >= 0 and value <= 1 ):
            raise ValueError("{class_name}: signal value must be in the range 0 <= signal_value <= 1.")
        self._control_signal = value
    
    @property
    def signal_value(self):
        return self.control_signal
    
    @signal_value.setter
    def signal_value( self, value ):
        self.control_signal = value
    
    @property
    def signal(self):
        return self.control_signal
    
    @signal.setter
    def signal(self, value):
        self.control_signal = value

class SolarController( Controller ):
    
    def __init__(self, min_irradiance, controlled_pump, security_shutdown = None ):
        
        from .pump import Pump
        
        if not isinstance(controlled_pump, Pump):
            raise TypeError("SolarController: Argument 'controlled_pump' must be an instance of sercpy.pump.Pump.")
        if security_shutdown is None:
            self._security_shutdown = Controller()
        else:
            if not isinstance(security_shutdown, Controller):
                raise TypeError("SolarController: Argument 'security_shutdown' is expected to be a controller.")
            self._security_shutdown = security_shutdown
            
        self._security_control_signal_last = 1
            
        controlled_pump.set_connections( controller = self )
        
        try:
            min_irradiance = float( min_irradiance )
        except:
            raise TypeError("LoadTempController: 'min_irradiance' must be convertible to type 'float'.")
        if not min_irradiance > 0:
            raise ValueError("LoadTempController: Argument 'min_irradiance' must be larger than zero.")
        
        self._min_irradiance = min_irradiance
        self._control_signal = 1
        
    def compute_outputs( self, operating_conditions, iteration_number ):
        
        if type( iteration_number ) is not int:
            raise TypeError("SolarController.compute_outputs: Argument 'iteration_number' must be an 'int'.")
        if not iteration_number >= 0:
            raise ValueError("SolarController.compute_outputs: Argument 'iteration_number' must be >= 0.")
        
        if iteration_number == 0:
            convergence = False
            if type( operating_conditions ) is not dict:
                raise TypeError("SolarController.compute_outputs: Argument 'operating_conditions' must be a dictionary.")
            if not 'irradiance_first_row' in operating_conditions:
                raise KeyError("SolarController.compute_outputs: Irradiance data could not be retrieved from 'operating_conditions'. Maybe you forgot to call the method 'MeteoProfile.compute_poa_irradiance'. After this, redefine the instance of `OperatingConditions` for the change to be applied.")
            self._irradiance_last = operating_conditions[ 'irradiance_first_row' ]
        else:
            convergence = True
        
        new_signal = 1 * ( self._irradiance_last >= self._min_irradiance )
        
        try:
            security_control_signal = self._security_shutdown._control_signal
        except AttributeError:
            self._convergence = False
            self._control_signal = new_signal
            return
        
        if not security_control_signal in [ 0, 1 ]:
            raise ValueError(f"SolarController: Only 1 and 0 should be received from security shutdown controller. Value received: {security_control_signal}")
        
        self._convergence = convergence and ( security_control_signal == self._security_control_signal_last )
        self._security_control_signal_last = security_control_signal
        
        self._control_signal = new_signal * ( security_control_signal == 1 )
        
class LoadTempController( Controller ):
    
    def __init__( self, *,
                 
                 controlled_pump,
                 heat_exchanger,
                 tank,
                 turn_on_dT,
                 turn_off_dT,
                 temp_tolerance,
                 last_signal_weight = None,
                 iteration_cycle = None ):
        
        ## Validate arguments
        
        from .pump import Pump
        from .heat_exchanger import HeatExchanger
        from .storage import StorageTank
        
        if not isinstance(controlled_pump, Pump):
            raise TypeError("LoadTempController: Argument 'controlled_pump' must be an instance of sercpy.pump.Pump.")
        if not isinstance(heat_exchanger, HeatExchanger):
            raise TypeError("LoadTempController: Argument 'heat_exchanger' must be an instance of sercpy.pump.HeatExchanger.")
        if not isinstance(tank, StorageTank):
            raise TypeError("LoadTempController: Argument 'tank' must be an instance of sercpy.pump.StorageTank.")
            
        try:
            turn_on_dT = float( turn_on_dT )
        except:
            raise TypeError("LoadTempController: 'turn_on_dT' must be convertible to type 'float'.")
        if not turn_on_dT > 0:
            raise ValueError("LoadTempController: Argument 'turn_on_dT' must be larger than zero.")
            
        try:
            turn_off_dT = float( turn_off_dT )
        except:
            raise TypeError("LoadTempController: 'turn_off_dT' must be convertible to type 'float'.")
        if not turn_off_dT > 0:
            raise ValueError("LoadTempController: Argument 'turn_off_dT' must be larger than zero.")
            
        if not ( turn_on_dT > turn_off_dT ):
            raise ValueError("LoadTempController: Argument 'turn_on_dT' must be larger than 'turn_off_dT'.")
        
        try:
            temp_tolerance = float( temp_tolerance )
        except:
            raise TypeError("LoadTempController: 'temp_tolerance' must be convertible to type 'float'.")
        if not temp_tolerance > 0:
            raise ValueError("LoadTempController: Argument 'temp_tolerance' must be larger than zero.")
            
        if last_signal_weight is not None:
            try:
                last_signal_weight = float( last_signal_weight )
            except:
                raise TypeError("LoadTempController: 'last_signal_weight' must be convertible to type 'float'.")
            if not ( last_signal_weight >= 0 and last_signal_weight <= 0.999 ):
                raise ValueError("LoadTempController: Argument 'last_signal_weight' must be in the range 0 <= last_signal_weight <= 0.999.")
        else:
            last_signal_weight = 0
        
        if iteration_cycle is not None:
            try:
                iteration_cycle = [ value for value in iteration_cycle ]
                assert all([ type( value ) is bool or value in [ 0, 1 ] for value in iteration_cycle ])
            except:
                raise TypeError("LoadTempController: Argument 'iteration_cycle' must be a list of boolean values.")
                
        # Assign attributes
        
        self._control_signal = 1
        self._current_state = 'on'
        self._controlled_pump = controlled_pump
        self._heat_exchanger = heat_exchanger
        self._tank = tank
        
        self._iteration_cycle = iteration_cycle
        
        self._turn_on_dT = turn_on_dT
        self._turn_off_dT = turn_off_dT
        self._temp_tolerance = temp_tolerance
        self._last_signal_weight = last_signal_weight
        
        self._min_signal = controlled_pump.minimum_flowrate / controlled_pump.rated_flowrate
        controlled_pump.set_connections( controller = self )
        
    def _check_condition( self, demanded_flowrate, HX_load_state_in, HX_load_state_out, set_state, tank_top_temp ):
        
        current_signal = self._control_signal
        
        tank_turnOff_temp = HX_load_state_in.T + self._turn_off_dT
        tank_turnOn_temp = HX_load_state_in.T + self._turn_on_dT
        
        if current_signal == 0 and any( [ 
                
                demanded_flowrate == 0 or tank_top_temp < tank_turnOff_temp ,
                self._current_state == 'off' and tank_top_temp < tank_turnOn_temp ]):
            
            return True
        
        if demanded_flowrate > 0 and any( [ 
                
                current_signal == 1 and HX_load_state_out.h <= set_state.h ,
                current_signal == self._min_signal and HX_load_state_out.h >= set_state.h ,
                abs( HX_load_state_out.T - set_state.T ) <= self._temp_tolerance ] ):
                
            return True
        
        return False
    
    def _update_signal_value( self, demanded_flowrate, HX_load_state_in, HX_load_state_out, set_state, tank_top_temp ):
        
        current_signal = self._control_signal
        
        tank_turnOff_temp = HX_load_state_in.T + self._turn_off_dT
        tank_turnOn_temp = HX_load_state_in.T + self._turn_on_dT
        
        if demanded_flowrate == 0 or tank_top_temp < tank_turnOff_temp:
            self._control_signal = 0
            return
        
        if self._current_state == 'off' and tank_top_temp < tank_turnOn_temp:
            self._control_signal = 0
            return
        
        if current_signal == 0:
            self._control_signal = 1
            return
        
        if current_signal == 1 and HX_load_state_out.h <= set_state.h:
            self._control_signal = 1
            return
        
        if HX_load_state_out.h == HX_load_state_in.h:
            self._control_signal = 1
            return
        
        new_signal = current_signal*( set_state.h - HX_load_state_in.h )/( HX_load_state_out.h - HX_load_state_in.h )
        new_signal = new_signal*( 1 - self._last_signal_weight ) + current_signal*self._last_signal_weight
        new_signal = max( [ min( [ new_signal, 1 ] ), self._min_signal ] )
        self._control_signal = new_signal
    
    def compute_outputs( self, operating_conditions, iteration_number ):
        
        if type( iteration_number ) is not int:
            raise TypeError("LoadTempController.compute_outputs: Argument 'iteration_number' must be an 'int'.")
        if not iteration_number >= 0:
            raise ValueError("LoadTempController.compute_outputs: Argument 'iteration_number' must be >= 0.")
        
        if type( operating_conditions ) is not dict:
            raise TypeError("SolarController.compute_outputs: Argument 'operating_conditions' must be a dictionary.")
            
        if not "T_set" in operating_conditions:
            raise KeyError("LoadTempController: 'T_set' (i.e. setpoint temperature) could not be optained from 'operating_conditions'.")
        
        T_set = operating_conditions[ "T_set" ]
        
        try:
            HX_load_state_in = self._heat_exchanger.inlet_load.state
            HX_load_state_out = self._heat_exchanger.outlet_load.state
            HX_load_flowrate = self._heat_exchanger.outlet_load.flowrate
        except AttributeError:
            self._convergence = False
            return
        
        set_state = HX_load_state_out.fluid.state( T = T_set )
        tank_top_temp = self._tank.top_temp
        
        tank_turnOff_temp = HX_load_state_in.T + self._turn_off_dT
        tank_turnOn_temp = HX_load_state_in.T + self._turn_on_dT
        
        if self._current_state == 'on' and tank_top_temp < tank_turnOff_temp:
            self._new_state = 'off'
        elif self._current_state == 'off' and tank_top_temp > tank_turnOn_temp:
            self._new_state = 'on'
        else:
            self._new_state = self._current_state
        
        if iteration_number == 0:
            self._convergence = False
            self._update_signal_value( HX_load_flowrate, HX_load_state_in, HX_load_state_out, set_state, tank_top_temp )
            return
        else:
            prior = self._check_condition(
                
                HX_load_flowrate,
                HX_load_state_in,
                HX_load_state_out,
                set_state,
                tank_top_temp )
            
            self.compute_input_convergence(
                relative_inputs = [ HX_load_flowrate ],
                state_inputs = [ HX_load_state_in, HX_load_state_out ], prior = prior )
        
        if ( not self._convergence ) and (
                
                self._iteration_cycle is None or self._iteration_cycle[  iteration_number % len( self._iteration_cycle )  ] ):
            
            self._update_signal_value( HX_load_flowrate, HX_load_state_in, HX_load_state_out, set_state, tank_top_temp )
    
    def update_state(self):
        
        self._current_state = self._new_state
        
class ExcessTempShutDown( Controller ):
    
    def __init__( self, *,
                 
                 tank,
                 tank_max_temp,
                 hysteresis,
                 
                 ):
        
        self._control_signal = 1
        self._current_state = 'on'
        self._new_state = 'on'
        self._convergence = False
        
        self._tank = tank
        self._tank_max_temp = tank_max_temp
        self._hysteresis = hysteresis
        
    def compute_outputs( self, operating_conditions, iteration_number ):
        
        if type( iteration_number ) is not int:
            raise TypeError("ExcessTempShutDown.compute_outputs: Argument 'iteration_number' is expected to be an 'int'.")
            if not iteration_number >= 0:
                raise ValueError("ExcessTempShutDown.compute_outputs: Argument 'iteration_number' must be >= 0.")
        
        if iteration_number == 0:
            self._convergence = False
            tank_top_temp = self._tank.top_temp
            if tank_top_temp > self._tank_max_temp:
                self._control_signal = 0
                self._new_state = 'off'
            elif tank_top_temp > self._tank_max_temp - self._hysteresis and self._current_state == 'off':
                self._control_signal = 0
                self._new_state = 'off'
            else:
                self._control_signal = 1
                self._new_state = 'on'
        else:
            self._convergence = True
    
    def update_state(self):
        self._current_state = self._new_state

class TankChargeController( Controller ):
    
    def __init__( self, *,
                 
                  controlled_pump,
                  heat_exchanger,
                  min_dT,
                  temp_tolerance,
                  heat_source_controller,
                  last_signal_weight = None,
                  iteration_cycle = None ):
        
        ## Validate arguments
        
        from .pump import Pump
        from .heat_exchanger import HeatExchanger
        from .storage import StorageTank
        
        if not isinstance(controlled_pump, Pump):
            raise TypeError("TankChargeController: Argument 'controlled_pump' must be an instance of sercpy.pump.Pump.")
        if not isinstance(heat_exchanger, HeatExchanger):
            raise TypeError("TankChargeController: Argument 'heat_exchanger' must be an instance of sercpy.pump.HeatExchanger.")
        if not isinstance(heat_source_controller, Controller):
            raise TypeError("TankChargeController: Argument 'heat_source_controller' must be an instance of sercpy.pump.Controller.")
            
        try:
            min_dT = float( min_dT )
        except:
            raise TypeError("TankChargeController: 'min_dT' must be convertible to type 'float'.")
        if not min_dT > 0:
            raise ValueError("TankChargeController: Argument 'min_dT' must be larger than zero.")
        
        try:
            temp_tolerance = float( temp_tolerance )
        except:
            raise TypeError("TankChargeController: 'temp_tolerance' must be convertible to type 'float'.")
        if not temp_tolerance > 0:
            raise ValueError("TankChargeController: Argument 'temp_tolerance' must be larger than zero.")
            
        if last_signal_weight is not None:
            try:
                last_signal_weight = float( last_signal_weight )
            except:
                raise TypeError("TankChargeController: 'last_signal_weight' must be convertible to type 'float'.")
            if not ( last_signal_weight >= 0 and last_signal_weight <= 0.999 ):
                raise ValueError("TankChargeController: Argument 'last_signal_weight' must be in the range 0 <= last_signal_weight <= 0.999.")
        else:
            last_signal_weight = 0
        
        if iteration_cycle is not None:
            try:
                iteration_cycle = [ value for value in iteration_cycle ]
                assert all([ type( value ) is bool or value in [ 0, 1 ] for value in iteration_cycle ])
            except:
                raise TypeError("LoadTempController: Argument 'iteration_cycle' must be a list of boolean values.")
        
        ## Assign attributes
        
        self._control_signal = 1
        self._controlled_pump = controlled_pump
        self._heat_exchanger = heat_exchanger
        self._heat_source_controller = heat_source_controller
        
        self._iteration_cycle = iteration_cycle
        
        self._last_signal_weight = last_signal_weight
        
        self._min_dT = min_dT
        self._temp_tolerance = temp_tolerance
        
        self._min_signal = controlled_pump.minimum_flowrate / controlled_pump.rated_flowrate
        controlled_pump.set_connections( controller = self )
        
    def _check_condition( self, heat_source_control_signal, HX_load_state_in, HX_load_state_out ):
        
        current_signal = self._control_signal
        
        if current_signal == 0 and heat_source_control_signal == 0:
            return True
        
        desired_state_out = HX_load_state_in.fluid.state( T = HX_load_state_in.T + self._min_dT )
        
        if current_signal == 1 and HX_load_state_out.h >= desired_state_out.h:
            return True
        
        if current_signal == self._min_signal and HX_load_state_out.h <= desired_state_out.h:
            return True
        
        if abs( HX_load_state_out.T - desired_state_out.T ) < self._temp_tolerance:
            return True
        
        return False
    
    def _update_signal_value( self, heat_source_control_signal, HX_load_state_in, HX_load_state_out ):
        
        if heat_source_control_signal == 0:
            self._control_signal = 0
            return
        
        current_signal = self._control_signal
        
        if current_signal == 0:
            self._control_signal = 1
            return
        
        desired_state_out = HX_load_state_in.fluid.state( T = HX_load_state_in.T + self._min_dT )
        
        if current_signal == 1 and HX_load_state_out.h >= desired_state_out.h:
            self._control_signal = 1
            return
        
        if current_signal == self._min_signal and HX_load_state_out.h <= desired_state_out.h:
            self._control_signal = self._min_signal
            return
        
        new_signal = current_signal*( HX_load_state_out.h - HX_load_state_in.h )/( desired_state_out.h - HX_load_state_in.h )
        new_signal = new_signal*( 1 - self._last_signal_weight ) + current_signal*self._last_signal_weight
        new_signal = max( [ min( [ new_signal, 1 ] ), self._min_signal ] )
        self._control_signal = new_signal
    
    def compute_outputs( self, operating_conditions, iteration_number ):
        
        if type( iteration_number ) is not int:
            raise TypeError("LoadTempController.compute_outputs: Argument 'iteration_number' must be an 'int'.")
        if not iteration_number >= 0:
            raise ValueError("LoadTempController.compute_outputs: Argument 'iteration_number' must be >= 0.")
        
        try:
            HX_load_state_in = self._heat_exchanger.inlet_load.state
            HX_load_state_out = self._heat_exchanger.outlet_load.state
            HX_load_flowrate = self._heat_exchanger.outlet_load.flowrate
            heat_source_control_signal = self._heat_source_controller.control_signal
        except AttributeError:
            self._convergence = False
            return
        
        if iteration_number == 0:
            self._convergence = False
            self._update_signal_value( heat_source_control_signal, HX_load_state_in, HX_load_state_out )
            return
        else:
            prior = self._check_condition(
                
                heat_source_control_signal,
                HX_load_state_in,
                HX_load_state_out )
            
            self.compute_input_convergence(
                relative_inputs = [ heat_source_control_signal, HX_load_flowrate ],
                state_inputs = [ HX_load_state_in, HX_load_state_out ], prior = prior )
        
        if ( not self._convergence ) and (
                
                self._iteration_cycle is None or self._iteration_cycle[  iteration_number % len( self._iteration_cycle )  ]
                
                ):
            
            self._update_signal_value( heat_source_control_signal, HX_load_state_in, HX_load_state_out )