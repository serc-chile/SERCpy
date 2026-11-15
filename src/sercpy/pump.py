# -*- coding: utf-8 -*-
"""
Created on Fri Nov 13 16:14:16 2026

@author: adria
"""

from .devices import Outlet
from .controller import ControlSignal
from .units import get_unit_type, convert_units
import warnings

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
        
    inlet : :ref:`Outlet <class_outlet>`
        Instance of the class :ref:`sercpy.devices.Outlet <class_outlet>`
        representing an outlet of another device from which the
        `Pump` instance takes its inputs. It must be set with the
        method `Pump.set_connections`.
        
    control_signal : :ref:`ControlSignal <control_signal_class>`
        Instance of the class :ref:`ControlSignal <control_signal_class>`
        representing the control signal of the Controller that controls the pump.
    
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
        """
        Method to compute the outputs of the pump.
        
        The following attributes of the `Pump` instance are updated when this method is called (unless input convergence is achieved; in that case only that attribute is updated):
            
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
            flowrate_in = self._inlet.flowrate
            state_in = self._inlet.state
            control_signal_value = self._control_signal.signal_value
        except AttributeError:
            self._input_convergence = False
            return
        
        if iteration_number == 0:
            self._relative_inputs_last, self._state_inputs_last = [ control_signal_value, flowrate_in ], [ state_in ]
            self._input_convergence = False
        else:
            self._compute_input_convergence( 
                relative_inputs = [ control_signal_value, flowrate_in ],
                state_inputs = [ state_in ], )
        
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
        
        if flowrate_in == 0 or flowrate_out == 0:
            self._input_convergence = self._input_convergence and flowrate_in == flowrate_out
        elif flowrate_in != flowrate_out:
            self._input_convergence = self._input_convergence and abs( flowrate_in - flowrate_out ) / min( [ flowrate_in  , flowrate_out ] ) <= self._relative_tolerance