# -*- coding: utf-8 -*-
"""
Created on Wed Nov 11 16:07:23 2026

@author: Adrian Riebel Brummer
"""

from .devices import Device, Outlet
from scipy.optimize import root_scalar
import numpy as np
from typing import Optional

HX_allowed_arguments = [
    
    "UA",
    "rated_effectiveness",
    "rated_water_flowrate",
    "release_vapor",
    "vapor_tolerance",
    "max_iterations",
    
    ]

class HeatExchanger( Device ):
    r"""
    Model for a counter-flow :math:`\varepsilon`-NTU heat exchanger.
    
    If not enough parameters are provided, the model is automatically converted
    to a constant-effectiveness heat exchanger. The drawback of this model,
    as its name suggests, is that effectiveness is not
    computed as a function of the operating flowrates.
    
    In order for the :math:`\varepsilon`-NTU model to be applied, the overall heat
    transfer coefficient (also called "UA") must be either provided by the user or
    computed internally. For the latter option, the following parameters must be
    specified:
        
        - The **rated effectiveness**, i.e., the effectiveness of the heat exchanger when it operates under nominal conditions.
        - The **rated water flowrate**, i.e., the nominal flowrate of the heat exchanger.
        Water is assumed as heat transfer fluid to compute UA; nevertheless, any :doc:`Fluid </fluids/fluid_class>` can be used
        to obtain results with an already initialized model.
        
    If only the rated effectiveness of the heat exchanger is provided, constant effectiveness is assumed.
    
    Parameters
    ----------
    UA : float
        Overall heat transfer coefficient of the heat exchanger (W/K).
        If provided, `rated_effectiveness` and `rated_water_flowrate` are ignored.
    
    rated_effectiveness : float
        Rated effectiveness of the heat exchanger (i.e., under nominal conditions).
        Valid range: `0.05 <= rated_effectiveness < 1`.
        This parameter must be specified if `UA` is not provided.
        If provided along with `rated_water_flowrate`,
        `UA` is computed from these two parameters.
        Otherwise, constant effectiveness is assumed.
    
    rated_water_flowrate : float
        Nominal water flowrate of the heat exchanger (kg/s).
    
    release_vapor : bool, optional
        If this parameter is set to `True`, the vapor produced when the saturation
        temperature of the load flow is achieved will be released and
        replaced with water from the distribution network. This mode is only available
        when water is used as heat transfer fluid. This parameter defaults to `True`.
    
    vapor_tolerance : float, optional
        Only relevant if `release_vapor` is set to `True`. This argument defines
        the relative difference allowed between the vapor flowrate being released
        and the water flowrate being introduced from the distribution network to
        replace it. Allowed range: `1e-8` to `1e-1`. If not provided, it defaults to `1e-3`.
        
    max_iterations : int, optional
        Maximum number of iterations allowed when computing the vapor
        being released due to boiling of the heat transfer fluid.
        If not provided, it defaults to `30`.
        
    Attributes
    ----------
    outlet_source : :ref:`Outlet <class_outlet>`
        Instance of the class :ref:`sercpy.devices.Outlet <class_outlet>`
        representing the outlet on the source side (or hot side) of the heat exchanger.
    
    outlet_load : :ref:`Outlet <class_outlet>`
        Instance of the class :ref:`sercpy.devices.Outlet <class_outlet>`
        representing the outlet on the load side (or cold side) of the heat exchanger.
    
    constant_effectiveness : bool
        Boolean value with the value `True` if the constant
        effectiveness model is being used instead of the effectiveness-NTU model.
    
    effectiveness : float
        Effectiveness of the heat exchanger. If the :math:`\varepsilon`-NTU model
        is being used, it corresponds to the value obtained the last time the
        method `HeatExchanger.compute_outputs` was called. Otherwise, it is the
        constant effectiveness of the heat exchanger.
        
    input_convergence : bool
        Boolean value stating whether convergence was achieved the last time the
        method `HeatExchanger.compute_outputs` was called. The concept of
        "convergence" refers to whether the inputs of the `HeatExchanger`
        instance are similar enough in consecutive iterations of a simulation
        time step, so that no further computation is needed.
    
    useful_power : float
        Useful power transferred to the load flow (W). The word 'useful'
        is used to differentiate this value from the power used to
        generate undesired vapor that is then released. This attribute
        gets updated every time the method `HeatExchanger.compute_outputs` is called.
    
    wasted_power : float
        Thermal power used to generate undesired vapor that is then
        released (W). This attribute gets updated every time the
        method `HeatExchanger.compute_outputs` is called.
    
    vapor_flowrate : float
        Undesired vapor being released from the heat exchanger (kg/s).
        This attribute gets updated every time the method
        `HeatExchanger.compute_outputs` is called.
    
    iterations : int
        Number of iterations carried out the last time the method
        `HeatExchanger.compute_outputs` was called. An iteration
        process is only necessary when undesired vapor is being
        produced and released on the load side of the heat exchanger.
    
    vapor_release_convergence : bool
        Boolean value stating whether convergence for the vapor release
        modeling was achieved the last time the method `HeatExchanger.compute_outputs`
        was called. If no vapor is released, this value will be `True`.
    
    ready_to_simulate : bool
        Boolean value stating whether all attributes needed for the
        `HeatExchanger` instance to be used in a
        simulation have been established.
    
    """
    def __init__(self, *,
                 UA = None,
                 rated_effectiveness = None,
                 rated_water_flowrate = None,
                 release_vapor = None,
                 vapor_tolerance = None,
                 max_iterations = None ):
            
        if UA is None and rated_effectiveness is None:
            raise ValueError("HeatExchanger: At least one of the parameters 'UA' and 'rated_effectiveness' must be provided.")
        
        # Case 1: UA is provided directly
        elif UA is not None:
            self._UA = self._validate_argument("UA", UA)
        
        # Case 2: UA is extracted from rated_effectiveness and rated_water_flowrate
        elif rated_effectiveness is not None and rated_water_flowrate is not None:
            
            rated_effectiveness = self._validate_argument("rated_effectiveness", rated_effectiveness)
            rated_water_flowrate = self._validate_argument("rated_water_flowrate", rated_water_flowrate)
            
            cp = 4184
            m_in = rated_water_flowrate
            C_min = m_in*cp
            
            def compute_effectiveness_init( UA ):
                NTU = UA / C_min
                return NTU / ( 1 + NTU )
            
            self._UA = float( root_scalar( lambda UA: compute_effectiveness_init( UA ) - rated_effectiveness,
                                           x0 = 1000, xtol = 1e-5 ).root )
            
            if not abs( compute_effectiveness_init( self._UA ) - rated_effectiveness) <= 1e-4:
                raise ValueError( "HeatExchanger: UA factor could not be determined." )
        
        # Case 3: Only effectiveness is provided. Constant-effectiveness HX is used
        elif rated_effectiveness is not None:
            
            self._rated_effectiveness = self._validate_argument("rated_effectiveness", rated_effectiveness)
            self._UA = None
        
        else:
            raise Exception("HeatExchanger: Unexpected error. No combination of valid parameters for initialization was found.")
            
        if release_vapor is None:
            self._release_vapor = True
        else:
            self._release_vapor = self._validate_argument("release_vapor", release_vapor)
        
        if vapor_tolerance is None:
            self._vapor_tolerance = 1e-3
        else:
            self._vapor_tolerance = self._validate_argument("vapor_tolerance", vapor_tolerance)
        
        if max_iterations is None:
            self._max_iterations = 30
        else:
            self._max_iterations = self._validate_argument("max_iterations", max_iterations)
            
        self._outlet_source = Outlet()
        self._outlet_load = Outlet()
            
    @property
    def outlet_source(self):
        "Instance of the class sercpy.devices.Outlet representing the outlet on the source side (or hot side) of the heat exchanger."
        return self._outlet_source
    
    @property
    def outlet_load(self):
        "Instance of the class sercpy.devices.Outlet representing the outlet on the load side (or cold side) of the heat exchanger."
        return self._outlet_load
    
    @property
    def constant_effectiveness(self):
        "Boolean value with the value 'True' if the constant effectiveness model is being used instead of the effectiveness-NTU model."
        return self._UA is None
    
    @property
    def effectiveness(self):
        "Effectiveness of the heat exchanger. If the effectiveness-NTU model is being used, it corresponds to the value obtained the last time the method 'HeatExchanger.compute_outputs' was called. Otherwise, it is the constant effectiveness of the heat exchanger."
        if self._UA is None:
            return self._rated_effectiveness
        if not hasattr( self, "_effectiveness" ):
            raise AttributeError("HeatExchanger: Attribute 'effectiveness' has not been computed yet. This attribute gets computed after calling the method HeatExchanger.compute_outputs.")
        return self._effectiveness
        
    @property
    def input_convergence(self):
        "Boolean value stating whether convergence was achieved the last time the method HeatExchanger.compute_outputs was called. The concept of 'convergence' refers to whether the inputs of the HeatExchanger instance are similar enough in consecutive iterations of a simulation time step, so that no further computation is needed."
        if not hasattr( self, "_convergence" ):
            raise AttributeError("HeatExchanger: Attribute 'convergence' has not been computed yet. This attribute gets updated when the method 'HeatExchanger.compute_outputs' is called.")
        return self._input_convergence
    
    @property
    def useful_power(self):
        "Useful power transferred to the load flow (W). The word 'useful' is used to differentiate this value from the power used to generate undesired vapor that is then released. This attribute gets updated every time the method 'HeatExchanger.compute_outputs' is called."
        if not hasattr( self, "_useful_power" ):
            raise AttributeError("HeatExchanger: Attribute 'useful_power' has not been computed yet. This attribute gets updated when the method 'HeatExchanger.compute_outputs' is called.")
        return self._useful_power
    
    @property
    def wasted_power(self):
        "Thermal power used to generate undesired vapor that is then released (W). This attribute gets updated every time the method 'HeatExchanger.compute_outputs' is called."
        if not hasattr( self, "_wasted_power" ):
            raise AttributeError("HeatExchanger: Attribute 'wasted_power' has not been computed yet. This attribute gets updated when the method 'HeatExchanger.compute_outputs' is called.")
        return self._wasted_power
    
    @property
    def vapor_flowrate(self):
        "Undesired vapor being released from the heat exchanger (kg/s). This attribute gets updated every time the method 'HeatExchanger.compute_outputs' is called."
        if not hasattr( self, "_vapor_flowrate" ):
            raise AttributeError("HeatExchanger: Attribute 'vapor_flowrate' has not been computed yet. This attribute gets updated when the method 'HeatExchanger.compute_outputs' is called.")
        return self._vapor_flowrate

    @property
    def iterations(self):
        "Number of iterations carried out the last time the method HeatExchanger.compute_outputs was called. An iteration process is only necessary when undesired vapor is being produced and released on the load side of the heat exchanger."
        if not hasattr( self, "_iterations" ):
            raise AttributeError("HeatExchanger: Attribute 'iterations' has not been computed yet. This attribute gets computed after calling the method HeatExchanger.compute_outputs.")
        return self._iterations
    
    @property
    def vapor_release_convergence(self):
        "Boolean value stating whether convergence for the vapor release modeling was achieved the last time the method HeatExchanger.compute_outputs was called. If no vapor is released, this value will be True."
        if not hasattr( self, "_vapor_release_convergence" ):
            raise AttributeError("HeatExchanger: Attribute 'vapor_release_convergence' has not been computed yet. This attribute gets computed after calling the method HeatExchanger.compute_outputs.")
        return self._vapor_release_convergence
    
    @property
    def ready_to_simulate(self):
        "Boolean value stating whether all attributes needed for the HeatExchanger instance to be used in a simulation have been established."
        return all( [
            
            hasattr( self, "_h_tolerance" ) or hasattr( self, "_temp_tolerance" ),
            hasattr( self, "_relative_tolerance" ),
            hasattr( self, "_inlet_source" ),
            hasattr( self, "_inlet_load" ),
            
            ] )
        
    @staticmethod
    def _validate_argument( argument_name, value ):
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
        
        if type(argument_name) is not str:
            raise TypeError("HeatExchanger._validate_argument: Argument 'argument_name' must be a string.")
            
        if not argument_name in HX_allowed_arguments:
            raise ValueError( f"HeatExchanger: '{argument_name}' is not a valid argument." )
            
        if value is None:
            return None
        
        if argument_name == "UA":
            try:
                value = float( value )
            except:
                raise TypeError("HeatExchanger: Parameter 'UA' must be convertible to type 'float'.")
            if not value > 0:
                raise ValueError("HeatExchange: Parameter 'UA' must be > 0.")
        
        if argument_name == "rated_effectiveness":
            try:
                value = float( value )
            except:
                raise TypeError("HeatExchanger: Parameter 'rated_effectiveness' must be convertible to type 'float'.")
            
            if not ( value >= 0.05 and value < 1 ):
                raise ValueError("HeatExchanger: Parameter 'rated_effectiveness' must be in the range 0.05 <= rated_effectiveness < 1.")
            
        if argument_name == "rated_water_flowrate":
            try:
                value = float( value )
            except:
                raise TypeError("HeatExchanger: Parameter 'rated_water_flowrate' must be convertible to type 'float'.")
            
            if not value > 0:
                raise ValueError("HeatExchanger: Parameter 'rated_water_flowrate' must be > 0.")
            
        if argument_name == "release_vapor":
            try:
                value = bool( value )
            except:
                raise TypeError("HeatExchanger: Parameter 'release_vapor' must be a boolean value.")
            
        if argument_name == "vapor_tolerance":
            try:
                value = float( value )
            except:
                raise TypeError("HeatExchanger: Argument 'vapor_tolerance' must be converible to type 'float'.")
            if not ( value >= 1e-8 and value <= 1e-1 ):
                raise ValueError("HeatExchanger: Argument 'vapor_tolerance' must be in the range 1e-8 <= vapor_tolerance <= 1e-1.")
            
        if argument_name == "max_iterations":
            try:
                assert value.is_integer()
                value = int( value )
            except:
                raise TypeError("HeatExchanger: Argument 'max_iterations' must be an integer value.")
                
            if not ( value >= 3 and value <= 300 ):
                raise ValueError("HeatExchanger: Argument 'max_iterations' must be in the range 3 <= max_iterations <= 300.")
                
        return value
    
    def _compute_effectiveness(self, flowrate_source, cp_source, flowrate_load, cp_load):
        
        if self._UA is None:
            return self._rated_effectiveness
        
        C_min = min([ flowrate_source*cp_source, flowrate_load*cp_load ])
        C_max = max([ flowrate_source*cp_source, flowrate_load*cp_load ])
        C_rel = C_min/C_max
        assert C_rel <= 1
        if C_min == 0:
            epsilon = 1
        else:
            NTU = self._UA/C_min
            if C_rel == 1:
                epsilon = NTU/(1 + NTU)
            else:
                epsilon = float( ( 1 - np.exp( -NTU * ( 1 - C_rel ) ) ) / ( 1 - C_rel * np.exp( -NTU * ( 1 - C_rel ) ) ) )
        return epsilon
    
    def set_connections( self, *, inlet_source = None, inlet_load = None ):
        """
        Specify the devices to which the heat exchanger's inlet ports are connected.
        
        Both arguments must be instances of :ref:`sercpy.devices.Outlet <class_outlet>`.
        
        Inlets can be re-defined as many times as needed by using this method.
        
        The method does not expect both inlets to be defined at the same time. However, both inlets must be defined before
        carrying out a simulation using the `HeatExchanger` instance.
        
        Parameters
        ----------
        inlet_source : :ref:`Outlet <class_outlet>`
            Inlet on the source side (or hot side) of the heat exchanger.
        
        inlet_load : :ref:`Outlet <class_outlet>`
            Inlet on the load side (or cold side) of the heat exchanger.
        
        """
        
        if inlet_source is not None and not isinstance( inlet_source, Outlet ):
            raise TypeError( "HeatExchanger.set_connections: Parameter 'inlet_source' must be an instance of sercpy.fluids.Outlet." )
        elif inlet_source is not None:
            self._inlet_source = inlet_source
        
        if inlet_load is not None and not isinstance( inlet_load, Outlet ):
            raise TypeError( "HeatExchanger.set_connections: Parameter 'inlet_load' must be an instance of sercpy.fluids.Outlet." )
        elif inlet_load is not None:
            self._inlet_load = inlet_load
            
    def set_convergence_criteria( self, *,
                                  relative_tolerance: float,
                                  temp_tolerance: Optional[ float ] = None,
                                  h_tolerance: Optional[ float ] = None,
                                  temp_normalization_range: Optional[ float ] = None,
                                  h_normalization_range: Optional[ float ] = None ):
        """
        Establish the convergence criteria of the `HeatExchanger` instance in the context of a simulation.
        
        When used in the context of a simulation, a `HeatExchanger` instance determines that "input convergence" has been achieved when the inputs received by it in consecutive iterations of the same time step differ in less that a certain margin.
        The aforementioned "margin" or "tolerance" is set by this method.
        When covergence is achieved for all components of a simulation, the results are recorded for the current time step and the simulation proceeds to the following time step.
        
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
            Maximum relative difference allowed for all input types except temperature and specific enthalpy. In the case of the `HeatExchanger`
            class, this amounts to flowrate only. Valid range: `1e-6` to `1e-1`.
        
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
            raise TypeError("HeatExchanger.set_convergence_criteria: 'relative_tolerance' must be convertible to type 'float'.")
        
        self._relative_tolerance = relative_tolerance
        
        if sum( [ variable is not None for variable in [ 
                
                temp_tolerance,
                h_tolerance,
                temp_normalization_range,
                h_normalization_range,
                
                ] ] ) != 1:
            
            raise ValueError("HeatExchanger.set_convergence_criteria: One and only one of the optional parameters must be provided: 'temp_tolerance', 'h_tolerance', 'temp_normalization_range', 'h_normalization_range'.")
        
        if all([ variable is None for variable in [ temp_tolerance, temp_normalization_range, h_tolerance, h_normalization_range ] ]):
            raise ValueError("HeatExchanger.set_convergence_criteria: At least one of the following parameters must be provided: 'temp_tolerance', 'temp_normalization_range', 'h_tolerance', 'h_normalization_range'.")
        
        elif temp_tolerance is not None and temp_normalization_range is not None:
            raise ValueError("HeatExchanger.set_convergence_criteria: Parameters 'temp_tolerance' and 'temp_normalization_range' cannot be provided together.")
        
        elif h_tolerance is not None and h_normalization_range is not None:
            raise ValueError("HeatExchanger.set_convergence_criteria: Parameters 'h_tolerance' and 'h_normalization_range' cannot be provided together.")
            
        if temp_tolerance is not None:
            try:
                temp_tolerance = float( temp_tolerance )
            except:
                raise TypeError("HeatExchanger.set_convergence_criteria: 'temp_tolerance' must be convertible to type 'float'.")
            self._temp_tolerance = temp_tolerance
            
        elif temp_normalization_range is not None:
            try:
                temp_normalization_range = float( temp_normalization_range )
            except:
                raise TypeError("HeatExchanger.set_convergence_criteria: 'temp_normalization_range' must be convertible to type 'float'.")
            self._temp_tolerance = relative_tolerance*temp_normalization_range
        
        else:
            self._temp_tolerance = None
        
        if h_tolerance is not None:
            try:
                h_tolerance = float( h_tolerance )
            except:
                raise TypeError("HeatExchanger.set_convergence_criteria: 'h_tolerance' must be convertible to type 'float'.")
            self._h_tolerance = h_tolerance
        elif h_normalization_range is not None:
            try:
                h_normalization_range = float( h_normalization_range )
            except:
                raise TypeError("HeatExchanger.set_convergence_criteria: 'h_normalization_range' must be convertible to type 'float'.")
            self._h_tolerance = relative_tolerance*h_normalization_range
        
        else:
            self._h_tolerance = None
        
        if self._temp_tolerance is not None and not ( self._temp_tolerance >= 1e-5 and self._temp_tolerance <= 1 ):
            raise ValueError(f"HeatExchanger.set_convergence_criteria: 'temp_tolerance' value ( equal to {self._temp_tolerance} ) is out of the allowed range: 1e-5 to 1.")
        
        if self._h_tolerance is not None and not ( self._h_tolerance >= 1e-2 and self._h_tolerance <= 5000 ):
            raise ValueError(f"HeatExchanger.set_convergence_criteria: 'h_tolerance' value ( equal to {self._h_tolerance} ) is out of the allowed range: 1e-2 to 5000.")
        
    def _set_last_inputs( self, flowrate_source, state_in_source, flowrate_load, state_in_load):
        """
        Method that updates the last inputs received by the SolarField instance. These attributes are then used to evaluate the whether input convergence is achieved.
        
        Parameters
        ----------
        flowrate_source : float
            Flowrate received by the solar field (kg/s).
        state_in : sercpy.fluids.FluidState
            State of the fluid received by the solar field.
            
        Returns
        -------
        None.
        
        """
        
        self._flowrate_source_last = flowrate_source
        self._state_in_source_last = state_in_source
        self._flowrate_load_last = flowrate_load
        self._state_in_load_last = state_in_load
        
    def _compute_input_convergence(self, flowrate_source, state_in_source, flowrate_load, state_in_load):
        """
        Method that compares the current inputs with the last inputs received, and determines whether the convergence criteria are met.
        
        Parameters
        ----------
        flowrate : float
            Flowrate received by the solar field (kg/s).
        state_in : sercpy.fluids.FluidState
            State of the fluid received by the solar field.
        
        Returns
        -------
        None.
        
        """
        convergence = True
        if flowrate_source == 0 or self._flowrate_source_last == 0:
            convergence = convergence and flowrate_source == self._flowrate_source_last
        elif flowrate_source != self._flowrate_source_last:
            convergence = convergence and abs( flowrate_source - self._flowrate_source_last ) / min( [ flowrate_source  , self._flowrate_source_last ] ) <= self._relative_tolerance
        
        if flowrate_load == 0 or self._flowrate_load_last == 0:
            convergence = convergence and flowrate_load == self._flowrate_load_last
        elif flowrate_load != self._flowrate_load_last:
            convergence = convergence and abs( flowrate_load - self._flowrate_load_last ) / min( [ flowrate_load  , self._flowrate_load_last ] ) <= self._relative_tolerance

        if self._h_tolerance is not None:
            convergence = convergence and abs( state_in_source.h - self._state_in_source_last.h ) <= self._h_tolerance
            convergence = convergence and abs( state_in_load.h - self._state_in_load_last.h ) <= self._h_tolerance
        
        if self._temp_tolerance is not None:
            convergence = convergence and abs( state_in_source.T - self._state_in_source_last.T ) <= self._temp_tolerance
            convergence = convergence and abs( state_in_load.T - self._state_in_load_last.T ) <= self._temp_tolerance
            
        self._input_convergence = convergence
    
    def compute_outputs( self, operating_conditions = None, iteration_number = None, *,
                         flowrate_source = None, state_in_source = None,
                         flowrate_load = None, state_in_load = None,
                         Tmains = None, ):
        r"""
        Method to compute the outputs of the heat exchanger.
        
        The following attributes of the `HeatExchanger` instance are updated when this method is called (unless input convergence is achieved; in that case only that attribute is updated):
            
            - input_convergence
            - outlet_source (state and flowrate)
            - outlet_load (state and flowrate)
            - effectiveness. This attribute gets updated only if the :math:`\varepsilon`-NTU model is being used
            - useful_power
            - wasted_power
            - vapor_flowrate
            - iterations
            - vapor_release_convergence
        
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
        
        if operating_conditions is None and iteration_number is None:
            if any([ variable is None for variable in [ flowrate_source, state_in_source, flowrate_load, state_in_load ] ]):
                raise TypeError("HeatExchanger.compute_outputs: Not all parameters needed for manual mode were provided. Parameters needed: flowrate_source, state_in_source, flowrate_load, state_in_load.")
            self._input_convergence = False
            
        elif operating_conditions is None or iteration_number is None:
            raise TypeError("HeatExchanger.compute_outputs: Both 'operating_conditions' and 'operating_conditions' must be provided in simulation mode. None of them must be provided in manual mode.")
        
        else:
            
            if type( operating_conditions ) is not dict:
                raise TypeError("HeatExchanger.compute_outputs: Parameter 'operating_conditions' must be a dictionary.")
            if not ( type( iteration_number ) is int and iteration_number >= 0 ):
                raise TypeError("HeatExchanger.compute_outputs: Parameter 'iteration_number' must be an 'int'. Its value msut be >= 0.")

            if not hasattr( self, "_inlet_source" ):
                raise AttributeError( "HeatExchanger.compute_outputs: inlet_source has not been defined. Use the method HeatExchanger.set_connections." )
            if not hasattr( self, "_inlet_load" ):
                raise AttributeError( "HeatExchanger.compute_outputs: inlet_load has not been defined. Use the method HeatExchanger.set_connections." )
            
            flowrate_source = self._inlet_source.flowrate
            state_in_source = self._inlet_source.state
            flowrate_load = self._inlet_load.flowrate
            state_in_load = self._inlet_load.state
                
            if iteration_number == 0:
                self._set_last_inputs(flowrate_source, state_in_source, flowrate_load, state_in_load)
                self._input_convergence = False
            else:
                self._compute_input_convergence(flowrate_source, state_in_source, flowrate_load, state_in_load)
                if self._input_convergence:
                    return
                else:
                    self._set_last_inputs(flowrate_source, state_in_source, flowrate_load, state_in_load)
            
            Tmains = operating_conditions[ 'Tmains' ]
            
        self._outlet_source.flowrate = flowrate_source
        self._outlet_load.flowrate = flowrate_load
        
        if flowrate_source == 0 or flowrate_load == 0:
            
            self._outlet_source.state = state_in_source
            self._outlet_load.state = state_in_load
            self._effectiveness = np.nan
            self._useful_power = 0
            self._wasted_power = 0
            self._vapor_flowrate = 0
            self._iterations = 0
            self._vapor_release_convergence = True
            
            return
        
        fluid_source = state_in_source.fluid
        fluid_load = state_in_load.fluid
        
        h_mains = fluid_load.state( T = Tmains ).h
        
        epsilon = self._compute_effectiveness( flowrate_source, state_in_source.cp, flowrate_load, state_in_load.cp)
        T_in_source = state_in_source.T
        
        self._effectiveness = epsilon
        
        if self._release_vapor and fluid_load.can_boil:
            
            if Tmains is None:
                raise TypeError("HeatExchanger.compute_outputs: Tmains must be provided if water is the load fluid and 'release_vapor' was set to 'True' at initialization (or was not provided).")
            
            flowrate_mains = 0
            it = 0
            
            while True:
                
                total_flowrate_load = flowrate_load + flowrate_mains
                total_h_in_load = ( flowrate_load*state_in_load.h + flowrate_mains*h_mains ) / total_flowrate_load
                total_T_in_load = fluid_load.state( h = total_h_in_load ).T
                
                if fluid_source.can_boil and total_T_in_load >= fluid_source.T_sat:
                    raise ValueError(f"HeatExchanger: Inlet load temperature ({ total_T_in_load } °C) is higher than (or equal to) the source fluid's saturation temperature: { fluid_source.T_sat } °C.")
                
                h_out_source_hyp = fluid_source.state( T = total_T_in_load ).h
                
                if T_in_source >= fluid_load.T_sat:
                    
                    if hasattr( fluid_load, "cp_ref" ):
                        load_liquid_cp = fluid_load.cp_ref
                    else:
                        load_liquid_cp = fluid_load.state( T = fluid_load.T_sat - 1.5 ).cp
                    
                    h_out_load_hyp = fluid_load.h_sat_liq + load_liquid_cp*(T_in_source - fluid_load.T_sat)
                else:
                    h_out_load_hyp = fluid_load.state( T = T_in_source ).h
                    
                Q_max = min( [ flowrate_source     * abs( h_out_source_hyp - state_in_source.h  ),
                               total_flowrate_load * abs( h_out_load_hyp   - total_h_in_load    )   ] )
                
                if not ( T_in_source > total_T_in_load ):
                    Q_max = -Q_max
                
                h_out_source = state_in_source.h - epsilon * Q_max / flowrate_source
                h_out_load = total_h_in_load + epsilon * Q_max / total_flowrate_load
                
                vapor_flowrate = total_flowrate_load * fluid_load.state( h = h_out_load ).Q
                
                it = it + 1
                
                Q_useful = flowrate_load * ( min( [ h_out_load, fluid_load.h_sat_liq ] ) - state_in_load.h )
                Q_actual = total_flowrate_load * ( h_out_load - total_h_in_load )
                Q_waste = Q_actual - Q_useful
                
                if flowrate_mains == vapor_flowrate or abs( flowrate_mains - vapor_flowrate ) / max( [ flowrate_mains, vapor_flowrate ] ) < self._vapor_tolerance:
                    
                    self._vapor_release_convergence = True
                    break
                
                if it == self._max_iterations:
                    self._vapor_release_convergence = False
                    break
                
                if flowrate_mains > 0 and vapor_flowrate == 0:
                    flowrate_mains = 0.5*flowrate_mains
                else:
                    assert h_out_load > fluid_load.h_sat_liq
                    flowrate_mains = Q_waste / ( fluid_load.h_sat_vap - h_mains )
            
            self._outlet_source.state = fluid_source.state( h = h_out_source )
            self._outlet_load.state = fluid_load.state( h = min( [ h_out_load, fluid_load.h_sat_liq ] ) )
            self._useful_power = Q_useful
            self._wasted_power = Q_waste
            self._vapor_flowrate = vapor_flowrate
            self._iterations = it
            
            return
        
        else:
            
            self._iterations = 1
            self._vapor_release_convergence = True
            self._vapor_flowrate = 0
            self._wasted_power = 0
            
            T_in_load = state_in_load.T
            
            if fluid_source.can_boil and T_in_load >= fluid_source.T_sat:
                raise ValueError(f"HeatExchanger: Inlet load temperature ({ T_in_load } °C) is higher than (or equal to) the source fluid's saturation temperature: { fluid_source.T_sat } °C.")
            
            h_out_source_hyp = fluid_source.state( T = T_in_load ).h
            
            if fluid_load.can_boil and T_in_source >= fluid_load.T_sat:
                
                if hasattr( fluid_load, "cp_ref" ):
                    load_liquid_cp = fluid_load.cp_ref
                else:
                    load_liquid_cp = fluid_load.state( T = fluid_load.T_sat - 1.5 ).cp
                
                h_out_load_hyp = fluid_load.h_sat_liq + load_liquid_cp*(T_in_source - fluid_load.T_sat)
            else:
                h_out_load_hyp = fluid_load.state( T = T_in_source ).h
                
            Q_max = min( [ flowrate_source * abs( h_out_source_hyp - state_in_source.h  ),
                           flowrate_load   * abs( h_out_load_hyp   - state_in_load.h    )   ] )
            
            if not ( T_in_source > T_in_load ):
                Q_max = -Q_max
            
            h_out_source = state_in_source.h - epsilon * Q_max / flowrate_source
            h_out_load = state_in_load.h + epsilon * Q_max / flowrate_load
            
            Q_useful = flowrate_load * (  h_out_load - state_in_load.h )
            
            self._outlet_source.state = fluid_source.state( h = h_out_source )
            self._outlet_load.state = fluid_load.state( h = h_out_load )
            self._useful_power = Q_useful