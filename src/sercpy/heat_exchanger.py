# -*- coding: utf-8 -*-
"""
Created on Wed Nov 11 16:07:23 2026

@author: Adrian Riebel Brummer
"""

from .devices import Device, Outlet
from scipy.optimize import root_scalar
import numpy as np

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
    Model for a counter-flow :math:`\epsilon`-NTU heat exchanger.
    
    If not enough parameters are provided, the model is automatically converted
    to a constant-effectiveness heat exchanger.
    
    In order for the :math:`\epsilon`-NTU model to be applied, the overall heat
    transfer coefficient (also called "UA") must be either provided by the user or
    computed internally. For the latter option, the following parameters must be
    specified:
        
        - The rated effectiveness, i.e., the effectiveness of the heat exchanger when it operates under nominal conditions.
        - The rated water flowrate, i.e., the nominal flowrate of the heat exchanger.
        
    If only the rated effectiveness of the heat exchanger is provided, constant effectiveness is assumed.
    
    Parameters
    ----------
    UA : float
        Overall heat transfer coefficient of the heat exchanger (W/K).
    
    rated_effectiveness : float
        
    
    In addition to providing this parameter directly, there is also the option of 
    
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
                                           x0 = 1000, bracket = [ 1, np.inf ], xtol = 1e-5 ).root )
            
            if not abs( compute_effectiveness_init( self._UA ) - rated_effectiveness) <= 1e-4:
                raise ValueError( "HeatExchanger: UA factor could not be determined." )
        
        # Case 3: Only effectiveness is provided. Constant-effectiveness HX is used
        elif rated_effectiveness is not None:
            
            self._effectiveness = self._validate_argument("rated_effectiveness", rated_effectiveness)
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
    def input_convergence(self):
        "Boolean value stating whether convergence was achieved the last time the method HeatExchanger.compute_outputs was called. The concept of 'convergence' refers to whether the inputs of the HeatExchanger instance are similar enough in consecutive iterations of a simulation time step, so that no further computation is needed."
        if not hasattr( self, "_convergence" ):
            raise AttributeError("HeatExchanger: Attribute 'convergence' has not been computed yet. This attribute gets updated when the method 'HeatExchanger.compute_outputs' is called.")
        return self._input_convergence
    
    @property
    def useful_power(self):
        "Useful power transferred to the load flow (W). The word 'useful' is used to differentiate this value from the power used to generate undesired vapor that is then released. This attribute gets updated every time the method 'SolarField.compute_outputs' is called."
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
    def effectiveness(self):
        "Effectiveness obtained for the heat exchanger the last time the method 'HeatExchanger.compute_outputs' was called."
        if not hasattr( self, "_effectiveness" ):
            raise AttributeError("HeatExchanger: Attribute 'effectiveness' has not been computed yet. This attribute gets computed after calling the method HeatExchanger.compute_outputs.")
        return self._effectiveness

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
            
            if not ( value >= 0.05 and value <= 1 ):
                raise ValueError("HeatExchanger: Parameter 'rated_effectiveness' must be in the range 0.05 <= rated_effectiveness <= 1.")
            
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
    
    def compute_effectiveness(self, m_in_source, cp_source, m_in_load, cp_load):
        
        if self._UA is None:
            return self._effectiveness
        
        C_min = min([ m_in_source*cp_source, m_in_load*cp_load ])
        C_max = max([ m_in_source*cp_source, m_in_load*cp_load ])
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
        
        if inlet_source is not None and not isinstance( inlet_source, Outlet ):
            raise TypeError( "HeatExchanger.set_connections: Parameter 'inlet_source' must be an instance of sercpy.fluids.Outlet." )
        elif inlet_source is not None:
            self._inlet_source = inlet_source
        
        if inlet_load is not None and not isinstance( inlet_load, Outlet ):
            raise TypeError( "HeatExchanger.set_connections: Parameter 'inlet_load' must be an instance of sercpy.fluids.Outlet." )
        elif inlet_load is not None:
            self._inlet_load = inlet_load
    
    def compute_outputs( self, operating_conditions = None, iteration_number = None, *,
                         state_in = None, flowrate = None,
                         GHI = None, DNI = None, DHI = None,
                         solar_apparent_zenith = None, solar_azimuth = None, 
                         Tamb = None, Tmains = None, doy = None ):
        """
        Method to compute the outputs of the heat exchanger.
        
        The following attributes of the `HeatExchanger` instance are updated when this method is called (unless input convergence is achieved; in that case only that attribute is updated):
            
            - input_convergence
            - outlet (state and flowrate)
            - useful_power
            - wasted_power
            - vapor_flowrate
            - efficiency
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
        
        state_in : :doc:`FluidState </fluids/fluidstate_class>`
            Object defining the thermodynamic state of the fluid as it enters the solar field.
        
        flowrate : float
            Mass flowrate entering the solar field (kg/s).
        
        GHI : float
            Global horizontal irradiance (W/m2).
        
        DNI : float
            Direct normal irradiance (W/m2).
        
        DHI : float
            Diffuse horizontal irradiance (W/m2).
        
        solar_apparent_zenith : float
            Apparent zenithal angle of the solar position (degrees, °).
        
        solar_azimuth : float
            Azimuthal angle of the solar position (degrees, °).
        
        Tamb : float
            Temperature of the environment surrounding the collector (°C).
        
        Tmains : float
            Mains water temperature. Not needed if: (1) the argument `release_vapor` has been set to `False` at initialization,
            or (2) boiling is not supported for the fluid that is entering the collector.
        
        doy : int
            Integer defining the day of the year (1 to 365).
        
        Returns
        -------
        None
        
        """
        
        
        
        
        m_in_source = inputs[0]
        h_in_source = inputs[1]
        m_in_load = inputs[2]
        h_in_load = inputs[3]
        T_mains = inputs[4]
        
        h_mains = self.fluid_props_load.T_to_h(T_mains)
        
        if m_in_source == 0 or m_in_load == 0:
            self.outputs = { 'load_outlet_h': {'output_type': 'h', 'value': h_in_load},
                             'source_outlet_h':{'output_type': 'h', 'value': h_in_source},
                             'load_outlet_flowrate': {'output_type': 'flowrate', 'value': m_in_load},
                             'source_outlet_flowrate': {'output_type': 'flowrate', 'value': m_in_source},
                             'steam_flowrate':{'output_type': 'flowrate', 'value': 0},
                             'useful_power': {'output_type': 'power', 'value': 0},
                             'wasted_power': {'output_type': 'power', 'value': 0},
                             'iterations': {'output_type': 'int', 'value': 0},
                             'maxIt': {'output_type': 'bool', 'value': False} }
            return
        epsilon = self.compute_effectiveness(m_in_source, self.fluid_props_source.liquid_spec_heat , m_in_load, self.fluid_props_load.liquid_spec_heat)
        T_in_source = self.fluid_props_source.h_to_T(h_in_source)
        m_mains = 0
        it = 0
        
        if self._release_vapor and fluid.can_boil:
            
            while True:
                new_m_in_load = m_in_load + m_mains
                new_h_in_load = (m_in_load*h_in_load + m_mains*h_mains)/new_m_in_load
                new_T_in_load = self.fluid_props_load.h_to_T(new_h_in_load)
                if new_T_in_load >= self.fluid_props_source.T_sat:
                    raise ValueError('Load temperature entering heat exchanger is higher than the saturation temperature of the source fluid')
                h_out_source_hyp = self.fluid_props_source.T_to_h(new_T_in_load)
                if T_in_source >= self.fluid_props_load.T_sat:
                    h_out_load_hyp = self.fluid_props_load.h_sat_liq + self.fluid_props_load.liquid_spec_heat*(T_in_source - self.fluid_props_load.T_sat)
                else:
                    h_out_load_hyp = self.fluid_props_load.T_to_h(T_in_source)
                if T_in_source > new_T_in_load:
                    Q_max = min([ m_in_source*(h_in_source - h_out_source_hyp),
                                 new_m_in_load*(h_out_load_hyp - new_h_in_load) ])
                else:
                    Q_max = -min([ m_in_source*(h_out_source_hyp - h_in_source),
                                  new_m_in_load*(new_h_in_load - h_out_load_hyp) ])
                h_out_source = h_in_source - epsilon*Q_max/m_in_source
                h_out_load = new_h_in_load + epsilon*Q_max/new_m_in_load
                m_vap = new_m_in_load*self.fluid_props_load.quality(h_out_load)
                it = it + 1
                if m_mains == m_vap or abs(m_mains - m_vap)/max([ m_mains, m_vap ]) < self.tolerance:
                    maxIt = False
                    break
                if it == self.maxIt:
                    maxIt = True
                    break
                Q_useful = m_in_load*(self.fluid_props_load.h_sat_liq - h_in_load)
                Q_actual = new_m_in_load*(h_out_load - new_h_in_load)
                Q_waste = Q_actual - Q_useful
                m_mains = Q_waste/(self.fluid_props_load.h_sat_vap - h_mains)
            if m_vap > 0:
                self.outputs = { 'load_outlet_h': {'output_type': 'h', 'value': self.fluid_props_load.h_sat_liq},
                                 'source_outlet_h':{'output_type': 'h', 'value': h_out_source},
                                 'load_outlet_flowrate': {'output_type': 'flowrate', 'value': m_in_load},
                                 'source_outlet_flowrate': {'output_type': 'flowrate', 'value': m_in_source},
                                 'steam_flowrate':{'output_type': 'flowrate', 'value': m_vap},
                                 'useful_power': {'output_type': 'power', 'value': Q_useful},
                                 'wasted_power': {'output_type': 'power', 'value': Q_waste},
                                 'iterations': {'output_type': 'int', 'value': it},
                                 'maxIt': {'output_type': 'bool', 'value': maxIt} }
                return
        else:
            
            maxIt = False
            new_m_in_load = m_in_load
            new_h_in_load = h_in_load
            new_T_in_load = self.fluid_props_load.h_to_T(new_h_in_load)
            if new_T_in_load >= self.fluid_props_source.T_sat:
                raise ValueError('Load temperature entering heat exchanger is higher than the saturation temperature of the source fluid')
            h_out_source_hyp = self.fluid_props_source.T_to_h(new_T_in_load)
            if T_in_source >= self.fluid_props_load.T_sat:
                h_out_load_hyp = self.fluid_props_load.h_sat_liq + self.fluid_props_load.liquid_spec_heat*(T_in_source - self.fluid_props_load.T_sat)
            else:
                h_out_load_hyp = self.fluid_props_load.T_to_h(T_in_source)
            if T_in_source > new_T_in_load:
                Q_max = min([ m_in_source*(h_in_source - h_out_source_hyp),
                              new_m_in_load*(h_out_load_hyp - new_h_in_load) ])
            else:
                Q_max = -min([ m_in_source*(h_out_source_hyp - h_in_source),
                               new_m_in_load*(new_h_in_load - h_out_load_hyp) ])
            h_out_source = h_in_source - epsilon*Q_max/m_in_source
            h_out_load = new_h_in_load + epsilon*Q_max/new_m_in_load

        self.outputs = { 'load_outlet_h': {'output_type': 'h', 'value': h_out_load},
                         'source_outlet_h':{'output_type': 'h', 'value': h_out_source},
                         'load_outlet_flowrate': {'output_type': 'flowrate', 'value': m_in_load},
                         'source_outlet_flowrate': {'output_type': 'flowrate', 'value': m_in_source},
                         'steam_flowrate':{'output_type': 'flowrate', 'value': 0},
                         'useful_power': {'output_type': 'power', 'value': new_m_in_load*(h_out_load - new_h_in_load)},
                         'wasted_power': {'output_type': 'power', 'value': 0},
                         'iterations': {'output_type': 'int', 'value': it},
                         'maxIt': {'output_type': 'bool', 'value': maxIt} }