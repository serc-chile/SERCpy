# -*- coding: utf-8 -*-
"""
Created on Fri Nov 13 16:14:16 2026

@author: adria
"""

from .devices import Outlet, ControlSignal
from .units import get_unit_type, convert_units
import warnings
from typing import Optional

pump_allowed_arguments = [
    
    "rated_flowrate",
    "flowrate_units",
    "rated_power",
    "power_units",
    "minimum_flowrate",
    
    ]

class Pump:
    r"""
    Model for a pump.
    
    It imposes a flowrate based on a control signal. The flowrate imposed is proportional
    to the control signal received (in the range 0-1). When the control signal is equal to `1`,
    the flowrate imposed is equal to the rated flowrate specified by the user at initialization.
    
    When the control signal corresponds to a flowrate that is less than the minimum flowrate
    specified by the user at initialization, the flowrate is automatically set to zero. If the
    minimum flowrate is not specified by the user, its value is set to 1% of the rated flowrate.
    
    Moreover, when a flowrate is being imposed as a condition in its inlet, it
    checks whether this flow matches the flowrate that the pump is producing.
    
    It also computes the power consumption of the pump, based on the assumption that:
        
    .. math::
        
        P \; \propto \; Q^3
        
    where :math:`P` is the power of the pump and :math:`Q` is the flowrate.
    
    Parameters
    ----------
    rated_flowrate : float
        Rated flowrate of the pump. It is the flowrate imposed by the pump when
        the control signal it receives is equal to `1`.
    
    flowrate_units : str, optional
        Flowrate units in which the rated_flowrate **and the minimum_flowrate**
        are being specified. If not provided, `"kg/s"` is assumed. Volumetric flowrate units
        are accepted as well; nevertheless, using volumetric flowrate units can slow down a
        a simulation. See :doc:`/units/units`.
    
    rated_power : float, optional
        Power used by the pump when it produces its rated flowrate. If not provided,
        power consumption is not considered (the attribute `power` is set to zero).
    
    power_units : str, optional
        Units in which `rated_power` is being specified. If not provided, `"W"`
        is assumed. See :doc:`/units/units`.
    
    minimum_flowrate : str, optional
        Minimum flowrate that the pump can produce. When the flowrate computed for a certain control
        signal is less than this value, the flowrate is set to zero. If not provided,
        it is assumed to be 1% of the rated flowrate specified.
    
    Attributes
    ----------
    outlet : :ref:`Outlet <outlet_class>`
        Instance of the class sercpy.devices.Outlet representing the outlet of the pump.
    
    input_convergence : bool
        Boolean value stating whether convergence was achieved the last time the method Pump.compute_outputs was called. The concept of 'input_convergence' refers to whether the inputs of the `Pump` instance are similar enough in consecutive iterations of a simulation time step, so that no further computation is needed.
    
    power : float
        Power used by the pump (W). This attribute gets updated every time the method 'Pump.compute_outputs' is called.
        
    rated_flowrate : float
        Rated flowrate of the pump, in kg/s or m3/s (see `flowrate_units`). It is the same as the value introduced by the user at initialization, expressed in SI units.
    
    minimum_flowrate : float
        Minimum flowrate of the pump. It is the same as the value introduced by the user at initialization, expressed in SI units.
    
    flowrate_units : str
        Units of `rated_flowrate` and `minimum_flowrate`. It is either 'kg/s' or 'm3/s', depending on whether the flowrates introduced by the user at initalization were mass flowrates or volumetric flowrates. See :doc:`/units/units`.
    
    """
    
    def __init__(
            
            self,
            rated_flowrate, *,
            flowrate_units = None,
            rated_power = None,
            power_units = None,
            minimum_flowrate = None,
            
            ):
        
        if rated_flowrate is None:
            raise TypeError("Pump: rated_flowrate cannot be None.")
        
        rated_flowrate = self._validate_argument( "rated_flowrate", rated_flowrate )
        flowrate_units = self._validate_argument("flowrate_units", flowrate_units)
        
        if flowrate_units is None:
            self._flowrate_type = 'm'
            flowrate_units = 'kg/s'
        
        if self._flowrate_type == 'm':
            self._rated_flowrate = convert_units( rated_flowrate, flowrate_units, 'kg/s' )
        else:
            assert self._flowrate_type == 'v'
            self._rated_flowrate = convert_units( rated_flowrate, flowrate_units, 'm3/s' )
        
        if minimum_flowrate is not None:
            
            minimum_flowrate = self._validate_argument( "minimum_flowrate", minimum_flowrate )
            
            if self._flowrate_type == 'm':
                self._minimum_flowrate = convert_units( minimum_flowrate, flowrate_units, 'kg/s' )
            else:
                assert self._flowrate_type == 'v'
                self._minimum_flowrate = convert_units( minimum_flowrate, flowrate_units, 'm3/s' )
            
            if not ( self._minimum_flowrate < self._rated_flowrate ):
                raise ValueError("Pump: Argument 'minimum_flowrate' must be smaller than 'rated_flowrate'.")
        
        else:
            self._minimum_flowrate = self._rated_flowrate*1e-2
        
        if rated_power is None:
            rated_power = 0
        else:
            rated_power = self._validate_argument("rated_power", rated_power)
        
        if power_units is None:
            power_units = 'W'
        else:
            power_units = self._validate_argument("power_units", power_units)
        
        self._rated_power = convert_units( rated_power, power_units, "W" )
        
        self._outlet = Outlet()
        
    @property
    def outlet(self):
        "Instance of the class sercpy.devices.Outlet representing the outlet of the pump."
        return self._outlet
    
    @property
    def input_convergence(self):
        "Boolean value stating whether convergence was achieved the last time the method Pump.compute_outputs was called. The concept of 'input_convergence' refers to whether the inputs of the `Pump` instance are similar enough in consecutive iterations of a simulation time step, so that no further computation is needed."
        if not hasattr( self, "_input_convergence" ):
            raise AttributeError("Pump: Attribute 'input_convergence' has not been computed yet. This attribute gets updated when the method 'Pump.compute_outputs' is called.")
        return self._input_convergence
    
    @property
    def power(self):
        "Power used by the pump (W). This attribute gets updated every time the method 'Pump.compute_outputs' is called."
        if not hasattr( self, "_power" ):
            raise AttributeError("Pump: Attribute 'power' has not been computed yet. This attribute gets updated when the method 'Pump.compute_outputs' is called.")
        return self._power
        
    @property
    def rated_flowrate( self ):
        "Rated flowrate of the pump. It is the same as the value introduced by the user at initialization, expressed in SI units."
        return self._rated_flowrate
    
    @property
    def minimum_flowrate( self ):
        "Minimum flowrate of the pump. It is the same as the value introduced by the user at initialization, expressed in SI units."
        return self._minimum_flowrate
    
    @property
    def flowrate_units( self ):
        "Units of `rated_flowrate` and `minimum_flowrate`. It is either 'kg/s' or 'm3/s', depending on whether the flowrates introduced by the user at initalization were mass flowrates or volumetric flowrates."
        if self._flowrate_type == 'm':
            return 'kg/s'
        else:
            return 'm3/s'
    
    def _validate_argument( self, argument_name, value ):
        """
        Private method to confirm that a certain argument provided by the user matches the expected type and other restrictions such as range, in the case of numeric values.
        
        In some cases, this method modifies the argument so that it matches the expected format.
        
        Parameters
        ----------
        argument_name : str
            Name to identify the argument.
        value : any
            Argument value.
        
        Raises
        ------
        ValueError
            Any discrepancy between the expected value and the value provided.
        
        Returns
        -------
        value : any
            Processed value. In most cases, the value returned is the same as the input.
        
        """
        
        if type( argument_name ) is not str:
            raise TypeError("HeatExchanger._validate_argument: Argument 'argument_name' must be a string.")
            
        if not argument_name in pump_allowed_arguments:
            raise ValueError( f"HeatExchanger: '{argument_name}' is not a valid argument." )
        
        if argument_name == [
                
                "rated_flowrate",
                "rated_power",
                "minimum_flowrate",
                
                ]:
            
            try:
                value = float( value )
            except:
                raise TypeError(f"Pump: Argument '{argument_name}' must be convertible to type 'float'.")
            
            if not value > 0:
                raise ValueError(f"Pump: Argument '{argument_name}' must be larger than zero.")
            
        
        if argument_name == "power_units":
            
            try:
                value = str( value )
            except:
                raise TypeError("Pump: Argument 'power_units' must be convertible to type 'str'.")
            
            if get_unit_type( value ) != "power":
                raise ValueError(f"Pump: Argument 'power_units' ( value specified: '{value}' ) was not recognized as a power unit.")
            
        if argument_name == "flowrate_units":
            try:
                value = str( value )
            except:
                raise TypeError("Pump: Argument 'flowrate_units' must be convertible to type 'str'.")
            
            unit_type = get_unit_type( value )
            
            if not unit_type in [ "volumetric_flowrate", "mass_flowrate" ]:
                raise ValueError(f"Pump: Argument 'flowrate_units' ( value specified: '{value}' ) was not recognized as a flowrate unit.")
            
            if unit_type == "volumetric_flowrate":
                warnings.warn("Pump: Specifying the rated flowrate in terms of volumetric flowrate will slow down the simulation.")
                self._flowrate_type = 'v'
            else:
                self._flowrate_type = 'm'
                
    def set_convergence_criteria( self, *,
                                  relative_tolerance,
                                  temp_tolerance,
                                  h_tolerance,
                                  temp_normalization_range,
                                  h_normalization_range ):
        """
        Establish the convergence criteria of the `Pump` instance in the context of a simulation.
        
        When used in the context of a simulation, a `Pump` instance determines that "input convergence" has been achieved when the inputs received by it in consecutive iterations of the same time step differ in less that a certain margin.
        The aforementioned "margin" or "tolerance" is set by this method.
        When covergence is achieved for all components of a simulation, the results are recorded for the current time step and the simulation proceeds to the following time step.
        
        In the particular case of the class `Pump`, convergence also depends on whether the input flow that the pump is receiving matches the output flow it is producing.
        
        The argument `relative_tolerance` is the relative discrepancy allowed between any type of input (flowrate, power, etc.) but temperature and specific enthalpy.
        
        For temperature and specific enthalpy, convergence is not evaluated in terms of relative differences but in terms of absolute differences (°C for temperature, J/kg for specific enthalpy).
        Moreover, it is only mandatory to set a tolerance for **ONE** of these two quantities (though the user may also specify values for both of them).
        
        There are two ways of setting the tolerances for temperature and specific enthalpy:
            
            - By directly setting their values (e.g. 0.01 °C for temperature, 50 J/kg for enthalpy).
            - By setting a "normalization range". The absolute tolerance is then determined with the result `relative_tolerance * normalization_range`. E.g.: if the value of `relative_tolerance` has been set to 1e-3, and the normalization range for temperature is set to 30 °C (which may be the difference between the maximum and minimum temperatures at which the system operates), then the absolute tolerance for temperature would be 0.03 °C.
        
        **Only the first parameter is always needed. At least one of the four latter parameters is needed. See the method's descritpion above for more details.**
        
        Parameters
        ----------
        relative_tolerance : float
            Maximum relative difference allowed for all input types except temperature and specific enthalpy. In the case of the `Pump`
            class, this corresponds to flowrates and control signals. Valid range: `1e-6` to `1e-1`.
        
        temp_tolerance : float, optional
            Absolute temperature difference allowed (°C). Valid range: `1e-5` to `1`.
        
        h_tolerance : float, optional
            Absolute enthalpy difference allowed (J/kg). Valid range: `1e-2` to `5000`.
        
        temp_normalization_range : float, optional
            Normalization range for temperature. See the description above for more details.
        
        h_normalization_range : float, optional
            Normalization range for specific enthalpy. See the description above for more details.
        
        Returns
        -------
        None.
        
        """
        try:
            relative_tolerance = float( relative_tolerance )
        except:
            raise TypeError("Pump.set_convergence_criteria: 'relative_tolerance' must be convertible to type 'float'.")
        
        self._relative_tolerance = relative_tolerance
        
        if sum( [ variable is not None for variable in [ 
                
                temp_tolerance,
                h_tolerance,
                temp_normalization_range,
                h_normalization_range,
                
                ] ] ) != 1:
            
            raise ValueError("Pump.set_convergence_criteria: One and only one of the optional arguments must be provided: 'temp_tolerance', 'h_tolerance', 'temp_normalization_range', 'h_normalization_range'.")
        
        if all([ variable is None for variable in [ temp_tolerance, temp_normalization_range, h_tolerance, h_normalization_range ] ]):
            raise ValueError("Pump.set_convergence_criteria: At least one of the following arguments must be provided: 'temp_tolerance', 'temp_normalization_range', 'h_tolerance', 'h_normalization_range'.")
        
        elif temp_tolerance is not None and temp_normalization_range is not None:
            raise ValueError("Pump.set_convergence_criteria: Arguments 'temp_tolerance' and 'temp_normalization_range' cannot be provided together.")
        
        elif h_tolerance is not None and h_normalization_range is not None:
            raise ValueError("Pump.set_convergence_criteria: Arguments 'h_tolerance' and 'h_normalization_range' cannot be provided together.")
            
        if temp_tolerance is not None:
            try:
                temp_tolerance = float( temp_tolerance )
            except:
                raise TypeError("Pump.set_convergence_criteria: 'temp_tolerance' must be convertible to type 'float'.")
            self._temp_tolerance = temp_tolerance
            
        elif temp_normalization_range is not None:
            try:
                temp_normalization_range = float( temp_normalization_range )
            except:
                raise TypeError("Pump.set_convergence_criteria: 'temp_normalization_range' must be convertible to type 'float'.")
            self._temp_tolerance = relative_tolerance*temp_normalization_range
        
        else:
            self._temp_tolerance = None
        
        if h_tolerance is not None:
            try:
                h_tolerance = float( h_tolerance )
            except:
                raise TypeError("Pump.set_convergence_criteria: 'h_tolerance' must be convertible to type 'float'.")
            self._h_tolerance = h_tolerance
        elif h_normalization_range is not None:
            try:
                h_normalization_range = float( h_normalization_range )
            except:
                raise TypeError("Pump.set_convergence_criteria: 'h_normalization_range' must be convertible to type 'float'.")
            self._h_tolerance = relative_tolerance*h_normalization_range
        
        else:
            self._h_tolerance = None
        
        if self._temp_tolerance is not None and not ( self._temp_tolerance >= 1e-5 and self._temp_tolerance <= 1 ):
            raise ValueError(f"Pump.set_convergence_criteria: 'temp_tolerance' value ( equal to {self._temp_tolerance} ) is out of the allowed range: 1e-5 to 1.")
        
        if self._h_tolerance is not None and not ( self._h_tolerance >= 1e-2 and self._h_tolerance <= 5000 ):
            raise ValueError(f"Pump.set_convergence_criteria: 'h_tolerance' value ( equal to {self._h_tolerance} ) is out of the allowed range: 1e-2 to 5000.")
    
    def _set_last_inputs( self, flowrate, state_in, control_signal_value ):
        
        self._flowrate_last = flowrate
        self._state_in_last = state_in
        self._control_signal_value_last = control_signal_value
    
    def _compute_input_convergence( self, flowrate, state_in, control_signal_value ):
        
        convergence = True
        if flowrate == 0 or self._flowrate_last == 0:
            convergence = convergence and flowrate == self._flowrate_last
        elif flowrate != self._flowrate_last:
            convergence = convergence and abs( flowrate - self._flowrate_last ) / min( [ flowrate  , self._flowrate_last ] ) <= self._relative_tolerance
        
        if flowrate == 0 or self._flowrate_out_last == 0:
            convergence = convergence and flowrate == self._flowrate_out_last
        elif flowrate != self._flowrate_out_last:
            convergence = convergence and abs( flowrate - self._flowrate_out_last ) / min( [ flowrate  , self._flowrate_out_last ] ) <= self._relative_tolerance

        if control_signal_value == 0 or self._control_signal_value_last == 0:
            convergence = convergence and control_signal_value == self._control_signal_value_last
        elif control_signal_value != self._control_signal_value_last:
            convergence = convergence and abs( control_signal_value - self._control_signal_value_last ) / min( [ control_signal_value  , self._control_signal_value_last ] ) <= self._relative_tolerance
        
        if self._h_tolerance is not None:
            convergence = convergence and abs( state_in.h - self._state_in_last.h ) <= self._h_tolerance
        
        if self._temp_tolerance is not None:
            convergence = convergence and abs( state_in.T - self._state_in_last.T ) <= self._temp_tolerance
            
        self._input_convergence = convergence
        
    def set_connections( self, *, inlet = None, control_signal = None ):
        
        if inlet is not None and not isinstance( inlet, Outlet ):
            raise TypeError( "Pump.set_connections: Argument 'inlet' must be an instance of sercpy.devices.Outlet." )
            
        if control_signal is not None and not isinstance( control_signal, ControlSignal() ):
            raise TypeError( "Pump.set_connections: Argument 'control_signal' must be an instance of sercpy.devices.ControlSignal." )
        
        if inlet is not None:
            self._inlet = inlet
        if control_signal is not None:
            self._control_signal = control_signal
        
    def compute_outputs( self, operating_conditions, iteration_number ):
        r"""
        Method to compute the outputs of the heat exchanger.
        
        The following attributes of the `HeatExchanger` instance are updated when this method is called (unless input convergence is achieved; in that case only that attribute is updated):
            
            - input_convergence
            - outlet (state and flowrate)
            - power
        
        **The first two parameters are meant to be used in the context of a simulation.
        All the other parameters are keyword-only and are meant for users to obtain results outside of simulations.**
        
        Parameters
        ----------
        operating_conditions : dict
            Dictionary returned by an :doc:`OperatingConditions </operating_conditions/operating_conditions>` instance when its method `get_conditions` is called.
        
        iteration_number : int
            Number of the iteration.
        
        flowrate_source : float
            Mass flowrate on the source side (or hot side) of the heat exchanger (kg/s).
        
        state_in_source : :doc:`FluidState </fluids/fluidstate_class>`
            Thermodynamic state of the fluid entering the heat exchanger in its source side (or hot side).
        
        flowrate_load : float
            Mass flowrate on the load side (or cold side) of the heat exchanger (kg/s).
        
        state_in_load : :doc:`FluidState </fluids/fluidstate_class>`
            Thermodynamic state of the fluid entering the heat exchanger in its load side (or cold side).
        
        Tmains : float, optional
            Temperature of the water in the distribution network. This parameter
            is only needed when the fluid in the load side of the heat exchanger
            is water, and if the parameter `release_vapor` was set to `True` at
            initialization (or if this parameter was omitted, since `True` is its
            default value).
        
        Returns
        -------
        None
        
        """
        
        if type( operating_conditions ) is not dict:
            raise TypeError("Pump.compute_outputs: Parameter 'operating_conditions' must be a dictionary.")
        if not ( type( iteration_number ) is int and iteration_number >= 0 ):
            raise TypeError("Pump.compute_outputs: Parameter 'iteration_number' must be an 'int'. Its value msut be >= 0.")
            
        if not hasattr( self, "_inlet" ):
            raise AttributeError( "Pump.compute_outputs: 'inlet' has not been defined. Use the method Pump.set_connections." )

        if not hasattr( self, "_control_signal" ):
            raise AttributeError( "Pump.compute_outputs: 'control_signal' has not been defined. Use the method Pump.set_connections." )
        
        try:
            flowrate = self._inlet.flowrate
            state_in = self._inlet.state
            control_signal_value = self._control_signal.signal_value
        except AttributeError:
            self._input_convergence = False
            return
        
        if iteration_number == 0:
            self._set_last_inputs( flowrate, state_in, control_signal_value )
            self._input_convergence = False
        else:
            self._compute_input_convergence( flowrate, state_in, control_signal_value )
            if self._input_convergence:
                return
            else:
                self._set_last_inputs( flowrate, state_in, control_signal_value )
        
        flowrate_out = control_signal_value * self._rated_flowrate
        
        if flowrate_out < self._minimum_flowrate and abs( flowrate_out - self._minimum_flowrate ) / self._minimum_flowrate < 1e-2:
            flowrate_out = self._minimum_flowrate
        elif flowrate_out < self._minimum_flowrate:
            flowrate_out = 0
        
        self._power = self._rated_power * ( flowrate_out / self._rated_flowrate )**3
        
        if self._flowrate_type == 'v':
            flowrate_out = convert_units( flowrate_out, 'm3/s', 'kg/s', density = state_in.D )
            
        self._outlet.state = state_in
        self._outlet.flowrate = flowrate_out
        
        self._flowrate_out_last = flowrate_out