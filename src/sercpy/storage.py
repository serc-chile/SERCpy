# -*- coding: utf-8 -*-
"""
Created on Wed Nov  4 21:27:10 2026

@author: Adrian Riebel Brummer
"""

from .devices import Device, Outlet
import numpy as np
from bisect import bisect
from .fluids import Fluid
from typing import Optional

tank_allowed_parameters = [
    
    "volume",
    "aspect_ratio",
    "diameter",
    "height",
    "loss_coeff",
    "top_loss_coeff",
    "edge_loss_coeff",
    "bottom_loss_coeff",
    "n_nodes",
    "io_relative_heights",
    "stored_fluid",
    "initial_temperature",
    "inlet_mode",
    "flow_alloc_coeff",
    "tolerance",
    "max_iterations",
    
    ]

class StorageTank( Device ):
    r"""
    One-dimensional nodal model for a vertical, cylindrical storage tank.
    
    This model discretizes a tank dividing its volume into vertically-stacked equally-sized parts, known as "nodes".
    
    This is a computationally cheap way of modeling stratified tanks, i.e.,
    tanks in which there is a noticeable temperature difference between the top
    part and the bottom part, with the top part being hotter.
    
    It is based on the models presented by Newton in 1995 [1]_, which have been featured in simulation programs such as `TRNSYS <https://www.trnsys.com/>`_.
    
    It also features the model known as "Advanced Flowrate Distribution", presented by Saloux and Candanedo in 2019 [2]_.
    
    References
    ----------
    .. [1] Newton, Brian J., "Modeling of Solar Storage Tanks,"
       Master Thesis, *University of Wisconsin-Madison*
       https://minds.wisc.edu/items/12af0289-60e9-436a-9c26-30bb04d2a228
    .. [2] E. Saloux, J.A. Candanedo. "Modelling stratified thermal energy storage tanks using an advanced flowrate distribution of the received flow,"
       *Applied Energy*, Volume 241, pages 34-45, 1 May 2019. https://doi.org/10.1016/j.apenergy.2019.02.075
    
    **Only two of the first four parameters must be provided to define the shape and size of the tank.**
    
    Parameters
    ----------
    volume : float, optional
        Internal volume of the tank, in m3. If provided, one and only one of the other parameters `aspect_ratio`, `diameter`, and `height` must also be provided.
    
    aspect_ratio : float, optional
        Aspect ratio of the tank; i.e., the ratio between the height and the diameter.
        If provided, one and only one of the other parameters `volume`, `diameter`, and `height` must also be provided.
    
    diameter : float, optional
        Diameter of the tank, in m.
        If provided, one and only one of the other parameters `volume`,
        `aspect_ratio`, and `height` must also be provided.
    
    height : float, optional
        Height of the tank, in m.
        If provided, one and only one of the other parameters `volume`,
        `aspect_ratio`, and `diameter` must also be provided.
    
    loss_coeff : float, optional
        Thermal loss coefficient of the tank (W/m2 K). If provided,
        this value replaces the other parameters `top_loss_coeff`,
        `edge_loss_coeff`, and `bottom_loss_coeff`, only if they are not provided.
    
    top_loss_coeff : float, optional
        Thermal loss coefficient at the top face of the tank (W/m2 K).
        If not provided, this value gets replaced by `loss_coeff`.
        If that parameter is not provided either, it defaults to 1 W/m2 K.
    
    edge_loss_coeff : float, optional
        Thermal loss coefficient at the lateral wall of the tank (W/m2 K).
        If not provided, this value gets replaced by `loss_coeff`.
        If that parameter is not provided either, it defaults to 1 W/m2 K.
    
    bottom_loss_coeff : float, optional
        Thermal loss coefficient at the bottom face of the tank (W/m2 K).
        If not provided, this value gets replaced by `loss_coeff`.
        If that parameter is not provided either, it defaults to 1 W/m2 K.
    
    n_nodes : int, optional
        Number of nodes of the tank. If not provided, it defaults to 8.
    
    io_relative_heights : list of pairs, optional
        Object specifying the positions of the inlet- and outlet ports of the tank.
        See :ref:`inlet_outlet_ports_definition` for more details on the format of this parameter.
    
    stored_fluid : :doc:`Fluid </fluids/fluid_class>`
        Fluid stored inside the tank.
    
    initial_temperature : float or list of float
        Initial temperature or temperatures of the tank (°C). This parameter
        can be a single value or a list of values.
        In the former case, all nodes are initialized with the same temperature.
        In the latter case, the length of the list has to be equal to `n_nodes`.
        The first value of the list corresponds to the top node of the tank;
        the last value corresponds to the bottom node.
    
    inlet_mode : str, optional
        String specifying how the flows that enter the tank through its inlets ports are modeled.
        The question of how to model the inlet flows comes from a
        simple fact: when an entering flow has a different temperature from the
        fluid inside the tank at the height where the inlet is located,
        the flow tends rise or sink to density differences.
        This parameter has three possible values:
            
        `"fixed_inlets"`
            The flows that enter the tank are assumed to stay in the node where
            the inlet is physically located. In other words, the phenomenon just discussed is neglected.
        `"temperature_seeking"`
            The flows are assumed to flow directly to the node that is closest
            to their temperature. The drawback of this model is that
        `"AFD"`
            This string stands for "Advanced Flowrate Distribution", which is
            a modelling method presented by Saloux and Candanedo in 2019,
            and could be summarized as a method to 
            The model proposed by Saloux and Candanedo [2]_, which is an
            intermediate between the two models just discussed, is used.
    
    flow_alloc_coeff : float, optional
        The "flowrate allocation coefficient", represented as :math:`\alpha` in the paper of Saloux and Candanedo [2]_,
        is an essential parameter for their modelling method. Range: `-inf` to `1`.
        If not provided, it defaults to `-0.5`.
    
    tolerance : float, optional
        Maximum temperature discrepancy (°C) allowed between successive **internal** iterations of the model so that convergence is achieved.
        Valid range: `1e-8` to `1e-1`. If not specified, it defaults to 1e-4.
    
    max_iterations : int, optional
        Maximum number of **internal** iterations of the model allowed before forcing the computation to stop. Valid range: `3` to `300`.
        If not specified, it defaults to `30`.
    
    """
    def __init__( self, *,
                  volume = None,
                  aspect_ratio = None,
                  diameter = None,
                  height = None,
                  loss_coeff = None,
                  top_loss_coeff = None,
                  edge_loss_coeff = None,
                  bottom_loss_coeff = None,
                  n_nodes = None,
                  io_relative_heights = None,
                  stored_fluid,
                  initial_temperature = None,
                  inlet_mode = None,
                  flow_alloc_coeff = None,
                  tolerance = None,
                  max_iterations = None ):
        
        # Compute geometry
        volume = self._validate_argument( "volume", volume )
        aspect_ratio = self._validate_argument( "aspect_ratio", aspect_ratio )
        diameter = self._validate_argument( "diameter", diameter )
        height = self._validate_argument( "height", height )
        
        self._volume, self._aspect_ratio, self._diameter, self._height =  self._compute_geometry( volume, aspect_ratio, diameter, height )
        
        # Define loss coefficients
        if top_loss_coeff is not None:
            self._top_loss_coeff = self._validate_argument("top_loss_coeff", top_loss_coeff)
        elif loss_coeff is not None:
            self._top_loss_coeff = self._validate_argument("loss_coeff", loss_coeff)
        else:
            self._top_loss_coeff = 1
            
        if edge_loss_coeff is not None:
            self._edge_loss_coeff = self._validate_argument("edge_loss_coeff", edge_loss_coeff)
        elif loss_coeff is not None:
            self._edge_loss_coeff = self._validate_argument("loss_coeff", loss_coeff)
        else:
            self._edge_loss_coeff = 1
            
        if bottom_loss_coeff is not None:
            self._bottom_loss_coeff = self._validate_argument("bottom_loss_coeff", bottom_loss_coeff)
        elif loss_coeff is not None:
            self._bottom_loss_coeff = self._validate_argument("loss_coeff", loss_coeff)
        else:
            self._bottom_loss_coeff = 1
        
        # Define number of nodes
        if n_nodes is not None:
            self._n_nodes = self._validate_argument("n_nodes", n_nodes)
        else:
            self._n_nodes = 8
        
        # Define inlet/outlet positions
        if io_relative_heights is not None:
            self.set_io_relative_heights( io_relative_heights )
            
        self._stored_fluid = self._validate_argument("stored_fluid", stored_fluid)
        
        # Set current temperature of the tank
        if initial_temperature is None:
            self._node_temperatures = [ 20 ]*self._n_nodes
        else:
            self._node_temperatures = self._validate_argument( "initial_temperature", initial_temperature )
        
        # Set inlet mode
        if inlet_mode is None:
            self._inlet_mode = 'fixed_inlets'
        else:
            self._inlet_mode = self._validate_argument("inlet_mode", inlet_mode)
            
        if self._inlet_mode == 'AFD':
            if flow_alloc_coeff is None:
                self._alpha = -0.5
            else:
                self._alpha = self._validate_argument("flow_alloc_coeff", flow_alloc_coeff)
        else:
            self._alpha = None
        
        # Set internal tolerance
        if tolerance is None:
            self._internal_tolerance = 1e-4
        else:
            self._internal_tolerance = self._validate_argument( "tolerance", tolerance )
        
        # Set maximum internal interations
        if max_iterations is None:
            self._max_iterations = 30
        else:
            self._max_iterations = self._validate_argument( "max_iterations", max_iterations )
        
        try:
            self._fluid_cp = self._stored_fluid.cp_ref
            self._fluid_thermal_conductivity = self._stored_fluid.k_ref
            self._fluid_density = self._stored_fluid.D_ref
        except AttributeError:
            raise AttributeError("StorageTank: stored_fluid does not have reference properties. Parameter 'T_ref' must be provided when initializing the 'Fluid' instance.")
        
        node_mass = self._fluid_density * self._volume / self._n_nodes
        self._node_thermal_capacity = node_mass * self._fluid_cp
        self._cross_area = float( np.pi * self._diameter**2 / 4 )
        self._node_height = self._height / self._n_nodes
        self._nodal_edge_area = float( np.pi * self._diameter * self._node_height )
        
    @property
    def stored_fluid(self):
        return self._stored_fluid
    
    @property
    def n_nodes(self):
        return self._n_nodes
    
    @property
    def volume(self):
        return self._volume
    
    @property
    def aspect_ratio(self):
        return self._aspect_ratio
        
    @property
    def height(self):
        return self._height
    
    @property
    def diameter(self):
        return self._diameter
    
    @property
    def top_temp(self):
        return self._node_temperatures[ 0 ]
    
    @property
    def bottom_temp(self):
        return self._node_temperatures[ self._n_nodes - 1 ]
    
    @property
    def convergence(self):
        return self._convergence
    
    @property
    def dE(self):
        if not hasattr( self, "_dE" ):
            raise AttributeError("StorageTank: Attribute 'dE' has not been computed yet. This attribute is computed when the method 'StorageTank.compute_outputs' is called.")
        return self._dE
    
    @property
    def Q_loss(self):
        if not hasattr( self, "_Q_loss" ):
            raise AttributeError("StorageTank: Attribute 'Q_loss' has not been computed yet. This attribute is computed when the method 'StorageTank.compute_outputs' is called.")
        return self._Q_loss
    
    @property
    def internal_convergence(self):
        if not hasattr( self, "_internal_convergence" ):
            raise AttributeError("StorageTank: Attribute 'internal_convergence' has not been computed yet. This attribute is computed when the method 'StorageTank.compute_outputs' is called.")
        return self._internal_convergence
    
    @property
    def iterations(self):
        return self._iterations
    
    @property
    def ready_to_simulate(self):
        
        for i in range( len( self._inlet_nodes ) ):
            if not hasattr( self, "_inlet_" + str( i + 1 ) ):
                return False
        return True
    
    @n_nodes.setter
    def n_nodes(self, value):
        if value == self._n_nodes:
            return
        if not value.is_integer():
            raise ValueError("StorageTank: 'n_nodes' must be an integer value.")
        if not value >= 1:
            raise ValueError("StorageTank: 'n_nodes' must be >= 1.")
        self._n_nodes = int( value )
        self._io_nodes_from_relative_heights()
        node_mass = self._fluid_density * self._volume / self._n_nodes
        self._node_thermal_capacity = node_mass * self._fluid_cp
        self._node_height = self._height / self._n_nodes
        self._nodal_edge_area = float( np.pi * self._diameter * self._node_height )
        self._update_temp_after_n_node_updating()
        
    def _update_temp_after_n_node_updating( self ):
        
        n_nodes_old = len( self._node_temperatures )
        node_interfaces_old = np.linspace( 0, 1, n_nodes_old + 1 ).astype(float).tolist()
        
        def T_func( x, node_temperatures_old ):
            assert x >= 0 and x <= 1
            if x == 0:
                return node_temperatures_old[ 0 ]
            if x == 1:
                return node_temperatures_old[ -1 ]
            index = bisect( node_interfaces_old, x ) - 1
            return node_temperatures_old[ index ]
        
        def integrate_function( a, b, node_temperatures_old ):
            assert a >= 0 and a <= 1
            assert b >= 0 and b <= 1
            assert b >= a
            if b == a:
                return 0
            current_position = a
            integral = 0
            while True:
                interface_between = False
                for interface in node_interfaces_old:
                    if interface > current_position and interface < b:
                        next_position = interface
                        interface_between = True
                        integral = integral + T_func( ( current_position + interface )/2, node_temperatures_old )*( interface - current_position )
                        break
                if not interface_between:
                    integral = integral + T_func( ( current_position + b )/2, node_temperatures_old )*( b - current_position )
                    break
                current_position = next_position
            integral = integral/( b - a )
            return integral
        
        node_interfaces_new = np.linspace( 0, 1, self._n_nodes + 1 ).astype(float).tolist()
        
        node_temps_new = []
        for i in range( len( node_interfaces_new ) - 1 ):
            node_temps_new.append( integrate_function( node_interfaces_new[ i ] , node_interfaces_new[ i + 1 ], self._node_temperatures ) )
        self._node_temperatures = node_temps_new
        
        if hasattr( self, "_new_temperatures" ):
            new_temps_new = []
            for i in range( len( node_interfaces_new ) - 1 ):
                new_temps_new.append( integrate_function( node_interfaces_new[ i ] , node_interfaces_new[ i + 1 ], self._new_temperatures ) )
            self._new_temperatures = new_temps_new
            
    
    def change_geometry( self, *, 
                         volume = None,
                         aspect_ratio = None,
                         diameter = None,
                         height = None,
                         keep_constant = None ):
        
        volume = self._validate_argument("volume", volume)
        aspect_ratio = self._validate_argument("aspect_ratio", aspect_ratio)
        diameter = self._validate_argument("diameter", diameter)
        height = self._validate_argument("height", height)
        
        parameters_to_change = sum( [ variable is not None for variable in [ volume, aspect_ratio, diameter, height ] ] )
        
        if not parameters_to_change in [ 1,2 ]:
            raise ValueError("StorageTank.change_geometry: One or two of the following parameters must be provided: 'volume', 'aspect_ratio', 'diameter', 'height'.")

        if parameters_to_change == 2 and keep_constant is not None:
            raise ValueError("StorageTank.change_geometry: Parameter 'keep_constant' must not be provided when two other parameters are specified.")

        if parameters_to_change == 1:
        
            if not keep_constant in [ 'volume', 'aspect_ratio', 'diameter', 'height' ]:
                raise ValueError("StorageTank.change_geometry: Parameter 'keep_constant' must be one of the following strings: 'volume', 'aspect_ratio', 'diameter', 'height'.")
            
            if keep_constant == 'volume':
                if volume is not None:
                    raise ValueError("StorageTank.change_geometry: Parameter 'keep_constant' cannot be the same as the parameter to change.")
                volume = self._volume
            if keep_constant == 'aspect_ratio':
                if aspect_ratio is not None:
                    raise ValueError("StorageTank.change_geometry: Parameter 'keep_constant' cannot be the same as the parameter to change.")
                aspect_ratio = self._aspect_ratio
            if keep_constant == 'diameter':
                if diameter is not None:
                    raise ValueError("StorageTank.change_geometry: Parameter 'keep_constant' cannot be the same as the parameter to change.")
                diameter = self._diameter
            if keep_constant == 'height':
                if height is not None:
                    raise ValueError("StorageTank.change_geometry: Parameter 'keep_constant' cannot be the same as the parameter to change.")
                height = self._height
        
        self._volume, self._aspect_ratio, self._diameter, self._height =  self._compute_geometry( volume, aspect_ratio, diameter, height )
        
        node_mass = self._fluid_density * self._volume / self._n_nodes
        self._node_thermal_capacity = node_mass * self._fluid_cp
        self._cross_area = float( np.pi * self._diameter**2 / 4 )
        self._node_height = self._height / self._n_nodes
        self._nodal_edge_area = float( np.pi * self._diameter * self._node_height )
        
    def set_io_relative_heights( self, io_relative_heights ):
        
        io_relative_heights = self._validate_argument("io_relative_heights", io_relative_heights)
        
        if hasattr( self, "_n_io_pairs" ):
            if not len( io_relative_heights ) == self._n_io_pairs:
                raise AttributeError("StorageTank.set_io_relative_heights: Number of inlet/outlet pairs cannot be modified. Port positions can.")
        else:
            self._n_io_pairs = len( io_relative_heights )
            for i in range( self._n_io_pairs ):
                new_outlet = Outlet()
                setattr( self , "_outlet_" + str( i + 1 ) , new_outlet )
        
        self._io_relative_heights = io_relative_heights
        self._io_nodes_from_relative_heights()
    
    def _io_nodes_from_relative_heights( self ):
        
        if not hasattr( self, "_n_nodes" ):
            raise AttributeError("Storagetank._io_nodes_from_relative_heights: Attribute 'n_nodes' is not defined.")
        if not hasattr( self, "_io_relative_heights" ):
            raise AttributeError("Storagetank._io_nodes_from_relative_heights: Attribute 'io_relative_heights' is not defined.")
        
        node_interfaces_rel_heigths = [ i/self._n_nodes for i in range( self._n_nodes ) ]
        
        self._inlet_nodes = [ bisect( node_interfaces_rel_heigths, pair[ 0 ] ) - 1 for pair in self._io_relative_heights ]
        self._outlet_nodes = [ bisect( node_interfaces_rel_heigths, pair[ 1 ] ) - 1 for pair in self._io_relative_heights ]
    
    @staticmethod
    def _compute_geometry( volume, aspect_ratio, diameter, height ):
        
        if sum([ variable is not None for variable in [ volume, aspect_ratio, diameter, height ] ]) != 2:
            raise ValueError("StorageTank: Two and only two of the parameters 'volume','aspect_ratio', 'diameter', and 'height' must be provided.")
        
        if volume is not None and aspect_ratio is not None:
            diameter = float( ( 4*volume / ( np.pi * aspect_ratio ) ) ** ( 1/3 ) )
            height = aspect_ratio * diameter
        
        elif volume is not None and diameter is not None:
            aspect_ratio = float( 4 * volume / ( np.pi * diameter**3 ) )
            height = aspect_ratio * diameter
        
        elif volume is not None and height is not None:
            aspect_ratio = float( ( np.pi * height**3  / ( 4 * volume ) ) ** ( 1/2 ) )
            diameter = height / aspect_ratio
        
        elif aspect_ratio is not None and diameter is not None:
            height = aspect_ratio * diameter
            volume = float( np.pi * diameter**2 * height / 4 )
        
        elif aspect_ratio is not None and height is not None:
            diameter = height / aspect_ratio
            volume = float( np.pi * diameter**2 * height / 4 )
        
        elif diameter is not None and height is not None:
            volume = float( np.pi * diameter**2 * height / 4 )
            aspect_ratio = height / diameter
        
        else:
            raise ValueError("StorageTank: No combination of parameters could be found to determine the geometry of the tank.")
        
        if not ( aspect_ratio >=  0.2 and aspect_ratio <= 5 ):
            raise ValueError(f"StorageTank: Aspect ratio of the tank is {aspect_ratio}. This is out of the allowed range: 0.2 - 5.")
        
        return volume, aspect_ratio, diameter, height
    
    def _validate_argument( self, parameter_name, value ):
        """
        Private method to confirm that a certain argument provided by the user matches the expected type and other restrictions such as range, in the case of numeric values.
        
        In some cases, this method modifies the argument so that it matches the expected format.
        
        Parameters
        ----------
        parameter_name : str
            Name to identify the parameter.
        value : any
            Parameter value.
        
        Raises
        ------
        ValueError
            Any discrepancy between the expected value and the value provided.
        
        Returns
        -------
        value : any
            Processed value. In most cases, the value returned is the same as the input.
        
        """
        
        if type(parameter_name) is not str:
            raise TypeError("StorageTank._validate_argument: Parameter 'parameter_name' must be a string.")
            
        if not parameter_name in tank_allowed_parameters:
            raise ValueError( f"StorageTank: '{parameter_name}' is not a valid parameter." )
            
        if value is None:
            return None
        
        if parameter_name in [
                
                "volume",
                "aspect_ratio",
                "diameter",
                "height",
                "loss_coeff",
                "top_loss_coeff",
                "edge_loss_coeff",
                "bottom_loss_coeff",
                
                ]:
            
            try:
                value = float( value )
            except:
                raise TypeError(f"StorageTank: '{parameter_name}' must be convertible to type 'float'.")
            if value <= 0:
                raise ValueError(f"StorageTank: '{parameter_name}' must larger than zero.")
                
        if parameter_name == 'n_nodes':
            
            try:
                assert value.is_integer()
                value = int( value )
            except:
                raise TypeError("StorageTank: 'n_nodes' must be an integer value.")
                
            if not value >= 1:
                raise ValueError("StorageTank: 'n_nodes' must be >= 1.")
            
        if parameter_name ==  "io_relative_heights":
            
            try:
                value = [ v for v in value ]
                assert all([ len( v ) == 2 for v in value ])
                value = [ [ v[0], v[1] ] for v in value ]
            except:
                raise ValueError("StorageTank: Parameter 'io_relative_heights' does not match the expected format: [ [ input_height_1, output_height_1 ], [ input_height_2, output_height_2 ], ... ].")
            
            try:
                value = [ [ float( v[0] ), float( v[1] ) ] for v in value ]
            except:
                raise ValueError("StorageTank: The numeric values of 'io_relative_heights' must be integers.")
            
            if not all( [ v[0] >= 0 and v[0] <= 1 and v[1] >= 0 and v[1] <= 1 for v in value ] ):
                raise ValueError("StorageTank: The numeric values of 'io_relative_heights' must be in the range 0 <= relative_height <= 1.")
        
        if parameter_name == "stored_fluid":
            
            if not isinstance( value, Fluid ):
                raise TypeError("StorageTank: stored_fluid must be an instance of sercpy.fluids.Fluid.")
                
        if parameter_name == "initial_temperature":
            
            try:
                value_2 = float( value )
                value_2 = [ value_2 ]*self._n_nodes
                value = value_2
            except TypeError:
                try:
                    value = [ float(v) for v in value ]
                    assert len( value ) == self._n_nodes
                except:
                    raise ValueError("StorageTank: Parameter 'initial_temperature' must be a single numeric value or a list of numeric values. In the latter case, its length must be equal to n_nodes.")
                
        if parameter_name == "inlet_mode":
            
            try:
                value = str(value)
            except:
                raise ValueError("StorageTank: Parameter 'inlet_mode' must be a string.")
                
            if not value in [ "fixed_inlets", "temperature_seeking", "AFD" ]:
                raise ValueError("StorageTank: Parameter 'inlet_mode' must be one of the strings: 'fixed_inlets', 'temperature_seeking' or 'AFD'.")
                
        if parameter_name == "flow_alloc_coeff":
            
            try:
                value = float(value)
            except:
                raise ValueError("StorageTank: Parameter 'flow_alloc_coeff' must be convertible to type 'float'.")
            
            value = min( [ value, 1 ] )
            
        if parameter_name == "tolerance":
            try:
                value = float( value )
            except:
                raise TypeError("StorageTank: Parameter 'tolerance' must be convertible to type 'float'.")
            
            if not ( value >= 1e-8 and value <= 1e-1 ):
                raise ValueError("StorageTank: Parameter 'tolerance' must be in the range 1e-8 - 1e-1.")
        
        if parameter_name == "max_iterations":
            try:
                assert value.is_integer()
                value = int( value )
            except:
                raise TypeError("StorageTank: Parameter 'max_iterations' must be an integer value.")
            
            if not ( value >= 3 and value <= 300 ):
                raise ValueError("StorageTank: Parameter 'max_iterations' must be in the range 3 <= max_iterations <= 300.")
        
        return value
        
    def set_inlet_flows(self, inlet_flowrates, inlet_temps):
        """
        Method to set the flow entering each node of the tank.
        This method is called by the Tank.compute_outputs method.

        Parameters
        ----------
            - inlet_1_T : float or int
                  temperature of inlet flow 1
            - inlet_1_flow_rate : float or int
                  mass flow of inlet flow 1
            - inlet_2_T : float or int
                  temperature of inlet flow 2
            - inlet_2_flow_rate : float or int
                  mass flow of inlet flow 2

        Returns
        -------
            - inlet_1_dist : dictionary with the format: {1: F1, 2: F2, 3: F3, ... , N: FN}
                  Where the keys of the dictionary represent the number each node.
                  F1, F2, F3 represent the portion of the inlet flow 1 entering each node (in flow units).
                  The top node has the number 1 and the bottom node has the number N, with N being the total number of nodes.
            - inlet_2_dist : same format as inlet_1_dist
                  same purpose but for inlet flow 2.
        """
        assert len( inlet_flowrates ) == len( self._inlet_nodes )
        assert len( inlet_flowrates ) == len( inlet_temps )
        
        if self._n_nodes == 1:
            return None
        
        distributions_list = [  ]
        
        if self._inlet_mode == 'fixed_inlets':
            
            for i, inlet_node in enumerate( self._inlet_nodes ):
                distributions_list.append( [ inlet_flowrates[ i ]*( node == inlet_node ) for node in range( self._n_nodes ) ] )
                
            return distributions_list
            
        virtual_ports = []
        
        for inlet_index in range( len( self._inlet_nodes ) ):
            inlet_temp = inlet_temps[ inlet_index ]
            inlet_node = self._inlet_nodes[ inlet_index ]
            
            if inlet_temp == self._node_temperatures[ inlet_node ]:
                virtual_ports.append( inlet_node )
                continue
            
            if inlet_temp > self._node_temperatures[ inlet_node ]:
                flow_direction = 'up'
                step = -1
            else:
                flow_direction = 'down'
                step = 1
            
            current_node = inlet_node
            while True:
                if flow_direction == 'up' and current_node == 0:
                    virtual_port_node = 0
                    break
                if flow_direction == 'down' and current_node == self._n_nodes - 1:
                    virtual_port_node = self._n_nodes - 1
                    break
                if inlet_temp == self._node_temperatures[ current_node ]:
                    virtual_port_node = current_node
                    break
                
                if (  ( flow_direction ==   'up' and inlet_temp < self._node_temperatures[ current_node + step ] )  or
                      ( flow_direction == 'down' and inlet_temp > self._node_temperatures[ current_node + step ] )      ):
                    
                    diff_1 = abs( inlet_temp - self._node_temperatures[ current_node ] )
                    diff_2 = abs( inlet_temp - self._node_temperatures[ current_node + step ] )
                    
                    if diff_2 < diff_1:
                        virtual_port_node = current_node + step
                    else:
                        virtual_port_node = current_node
                        
                    break
                
                current_node = current_node + step
                
            virtual_ports.append( virtual_port_node )
        
        assert len( virtual_ports ) == len( self._inlet_nodes )
        
        if self._inlet_mode == 'temperature_seeking':
            
            for i, virtual_port_node in enumerate( virtual_ports ):
                distributions_list.append( [ inlet_flowrates[ i ]*( node == virtual_port_node ) for node in range( self._n_nodes ) ] )
                
            return distributions_list
        
        assert self._inlet_mode == 'AFD'
        
        distributions_list = [ [ 0 ]*self._n_nodes for i in range( len( self._inlet_nodes ) ) ]
            
        loss_factor = max( [ min ( [ (1 - self._alpha)/(self._n_nodes - 1) , 1 ] ) , 0 ] )
        
        for inlet_index in range( len( self._inlet_nodes ) ):
            
            virtual_port_node = virtual_ports[ inlet_index ]
            if virtual_port_node == self._inlet_nodes[ inlet_index ]:
                distributions_list[ inlet_index ][ virtual_port_node ] = inlet_flowrates[ inlet_index ]
                continue
            
            if virtual_port_node < self._inlet_nodes[ inlet_index ]:
                step = -1
            else:
                step = 1
            
            dFlow = inlet_flowrates[ inlet_index ]*loss_factor
            
            current_node = self._inlet_nodes[ inlet_index ]
            remaining_flow = inlet_flowrates[ inlet_index ]
            
            while True:
                
                if any( [  current_node == virtual_port_node, remaining_flow <= dFlow, step == -1 and current_node == 0, step == 1 and current_node == self._n_nodes - 1 ] ):
                    distributions_list[ inlet_index ][current_node] = remaining_flow
                    break
                
                distributions_list[ inlet_index ][current_node] = dFlow
                remaining_flow = remaining_flow - dFlow
                current_node = current_node + step
        
        assert len( distributions_list ) == len( self._inlet_nodes )
        assert all( [ len( distribution ) == self._n_nodes for distribution in distributions_list ] )
        return distributions_list
    
    def _compute_internal_convergence(self, list_1, list_2):
        """
        Method that receives the temperatures of successive iterations.
        It returns a boolean value which is True is convergence has been achieved (i.e. the difference between successive iterations is less than the tolerance) and False otherwise.
        This method is called by the Tank.compute_outputs method.
        
        Parameters
        ----------
            - dict1 : dictionary
                dictionary of resulting temperatures as yielded by the method Tank.iteration, corresponding to the previous iteration.
            - dict2 : dictionary
                dictionary of resulting temperatures as yielded by the method Tank.iteration, corresponding to the current iteration.

        Returns
        -------
            - Boolean Value
                True is convergence has been achieved (i.e. the difference between successive iterations is less than the tolerance) and False otherwise.
        """
        
        return all( abs( temps_1[ 'T_avg' ] - temps_2[ 'T_avg' ] ) <= self._internal_tolerance      and 
                    abs( temps_1[ 'T_final' ] - temps_2[ 'T_final' ] ) <= self._internal_tolerance 
                    for temps_1, temps_2 in zip( list_1, list_2 ) )
    
    def _mix_nodes(self, temps_list):
        """
        Method to mix the nodes in the case that there are temperature inversions (i.e., a certain node is hotter than the node above it).
        This method is called by the Tank.compute_outputs method.
        
        Parameters
        ----------
            - dict1 : dictionary
                 dictionary of resulting temperatures as yielded by the method Tank.iteration.
        """
        assert len( temps_list ) == self._n_nodes
        
        if self._n_nodes == 1:
            return [ { 'T_avg': temps_list[ 0 ][ 'T_avg' ], 'T_final': temps_list[ 0 ][ 'T_final' ] } ]
        
        mixed_nodes = [ { 'original_node_numbers': [ i ], 'T_final': temps_list[ i ]['T_final'],
                          'mass': 1} for i in range( len( temps_list ) ) ]
        while True:
            
            if all(  [ mixed_nodes[ i ][ 'T_final' ] >= mixed_nodes[ i + 1 ][ 'T_final' ] for i in range( len( mixed_nodes ) - 1 ) ]  ):
                break
            
            for i in range( len( mixed_nodes ) - 1 ):
                
                if mixed_nodes[ i ][ 'T_final' ] < mixed_nodes[ i + 1 ][ 'T_final' ]:
                    
                    total_mass = mixed_nodes[ i ][ 'mass' ] + mixed_nodes[ i + 1 ][ 'mass' ]
                    
                    T_final = ( ( mixed_nodes[   i   ][ 'mass' ] / total_mass ) * mixed_nodes[   i   ][ 'T_final' ] +
                                ( mixed_nodes[ i + 1 ][ 'mass' ] / total_mass ) * mixed_nodes[ i + 1 ][ 'T_final' ]   )
                    
                    nodes_list = mixed_nodes[ i ][ 'original_node_numbers' ] + mixed_nodes[ i + 1 ][ 'original_node_numbers' ]
                    
                    mixed_nodes[ i ] = { 'original_node_numbers': nodes_list , 'T_final': T_final , 'mass': total_mass }
                    
                    mixed_nodes.pop( i + 1 )
                    
                    break
        
        result = [ np.nan ]*self._n_nodes
        for dictionary in mixed_nodes:
            for node_number in dictionary[ 'original_node_numbers' ]:
                result[ node_number ] = { 'T_avg': temps_list[ node_number ][ 'T_avg' ], 'T_final': dictionary[ 'T_final'] }
        
        return result
    
    def _iteration( self, inlet_flowrates, inlet_temps,
                    Tamb, previous_result, time_step,
                    distributions_list ):
        """
        Method that executes a single iteration to determine the temperature at the end of the time step and the average temperature over the time step for each node.
        This method is called by the Tank.compute_outputs method.

        Parameters
        ----------
            - inlet_1_flow_rate : float or int (positive or zero)
                  mass flow rate entering the tank through inlet 1
            - inlet_1_T : float or int
                  temperature of the flow entering the tank through inlet 1
            - inlet_2_flow_rate : float or int (positive or zero)
                  mass flow rate entering the tank through inlet 2
            - inlet_2_T : float or int
                  temperature of the flow entering the tank through inlet 2
            - Tamb : float or int
                  ambient temperature
            - previous_result : dictionary
                  dictionary of temperatures at the end of the time step and average temperatures yielded by the previous iteration (see the information on what this method returns).
            - time_step : float or int (positive)
                  time step value (time units)

        Returns
        -------
            - Sol : dictionary
                  This method returns a dictionary with the following format:
                      {1: {'T_avg': T_avg_1, 'T_final': T_final_1},
                       2: {'T_avg': T_avg_2, 'T_final': T_final_2},
                       3: {'T_avg': T_avg_3, 'T_final': T_final_3},
                       .... ,
                       .... ,
                       N: {'T_avg': T_avg_N, 'T_final': T_final_N}}
                    
                  The keys of the dictionary are integers representing each node of the tank.
                  The top node has the number 1 and the bottom node has the number N, with N being the total number of nodes.
                  Each node has a corresponding dictionary with the keys 'T_avg' and 'T_final'.
                  The values T_avg_1, T_avg_2, T_avg_3, .... , T_avg_N represent the average temperature determined for each node during the current time step.
                  The values T_final_1, T_final_2, T_final_3, .... , T_final_N represent the temperature determined for each node at the end of the current time step.
        """
        # Case 1: The tank has only 1 node
        if self._n_nodes == 1:
            a = -self._nodal_edge_area*self._edge_loss_coeff
            b = self._nodal_edge_area*self._edge_loss_coeff*Tamb
            a = a - self._cross_area*self._top_loss_coeff
            b = b + self._cross_area*self._top_loss_coeff*Tamb
            a = a - self._cross_area*self._bottom_loss_coeff
            b = b + self._cross_area*self._bottom_loss_coeff*Tamb
            a = a - sum( [ inlet_flowrates[ inlet_node_index ]*self._fluid_cp for inlet_node_index in range( len( self._inlet_nodes ) ) ] )
            b = b + sum( [ inlet_flowrates[ inlet_node_index ]*self._fluid_cp*inlet_temps[ inlet_node_index ] for inlet_node_index in range( len( self._inlet_nodes ) ) ] )
            a = a/self._node_thermal_capacity
            b = b/self._node_thermal_capacity
            T_final = float( ( self._node_temperatures[ 0 ] + b/a ) * np.exp( a*time_step ) - b/a )
            T_avg = float( ( 1 / ( a*time_step ) ) * ( self._node_temperatures[ 0 ] + b/a ) * ( np.exp( a * time_step ) - 1 ) - b/a )
            return [ { 'T_avg': T_avg, 'T_final': T_final } ]
        
        # Case 2: The tank has more than one node
        result = []
        # The values of a_i and b_i of each node are determined (first without dividing by the thermal capacity of the node)
        for node in range( self._n_nodes ):
            a = -self._nodal_edge_area*self._edge_loss_coeff
            b = self._nodal_edge_area*self._edge_loss_coeff*Tamb
            flow_in = sum( [ distributions_list[ inlet_node_index ][ node ] for inlet_node_index in range( len( self._inlet_nodes ) ) ] )
            a = a - sum( [ distributions_list[ inlet_node_index ][ node ]*self._fluid_cp for inlet_node_index in range( len( self._inlet_nodes ) ) ] )
            b = b + sum( [ distributions_list[ inlet_node_index ][ node ]*self._fluid_cp*inlet_temps[ inlet_node_index ] for inlet_node_index in range( len( self._inlet_nodes ) ) ] )
            flow_out = sum( [ ( node == self._outlet_nodes[ outlet_node_index ] )*inlet_flowrates[ outlet_node_index ] for outlet_node_index in range( len( self._outlet_nodes ) ) ] )
            
            if node == 0:
                flow_below = flow_out - flow_in
                a = a - self._cross_area*self._top_loss_coeff
                a = a - self._fluid_thermal_conductivity*self._cross_area/self._node_height
                b = b + self._cross_area*self._top_loss_coeff*Tamb
                b = b + self._fluid_thermal_conductivity*self._cross_area*previous_result[ node + 1 ]['T_avg']/self._node_height
                if flow_below > 0:
                    a = a - flow_below*self._fluid_cp
                    b = b + flow_below*self._fluid_cp*previous_result[ node + 1 ]['T_avg']
                flow_above = -flow_below
            
            elif node == self._n_nodes - 1:
                a = a - self._cross_area*self._bottom_loss_coeff
                a = a - self._fluid_thermal_conductivity*self._cross_area/self._node_height
                b = b + self._cross_area*self._bottom_loss_coeff*Tamb
                b = b + self._fluid_thermal_conductivity*self._cross_area*previous_result[ node - 1 ]['T_avg']/self._node_height
                if abs(flow_above + flow_in - flow_out) > 1e-8:
                    raise ValueError("StorageTank: Flow balance error.")
                if flow_above > 0:
                    a = a - flow_above*self._fluid_cp
                    b = b + flow_above*self._fluid_cp*previous_result[ node - 1 ]['T_avg']
            
            else:
                flow_below = flow_out - flow_in - flow_above
                a = a - 2*self._fluid_thermal_conductivity*self._cross_area/self._node_height
                b = b + self._fluid_thermal_conductivity*self._cross_area*previous_result[ node + 1 ]['T_avg']/self._node_height
                b = b + self._fluid_thermal_conductivity*self._cross_area*previous_result[ node - 1 ]['T_avg']/self._node_height
                if flow_above > 0:
                    a = a - flow_above*self._fluid_cp
                    b = b + flow_above*self._fluid_cp*previous_result[ node - 1 ]['T_avg']
                if flow_below > 0:
                    a = a - flow_below*self._fluid_cp
                    b = b + flow_below*self._fluid_cp*previous_result[ node + 1]['T_avg']
                flow_above = -flow_below
            # The actual values of a_i and b_i are determined by dividing by the thermal capacity of the nodes
            a = a/self._node_thermal_capacity
            b = b/self._node_thermal_capacity
            # Average temperatures and temperatures at the end of the time step are determined.
            T_final = float( ( self._node_temperatures[ node ] + b/a ) * np.exp( a*time_step ) - b/a )
            T_avg = float( ( 1 / ( a*time_step ) ) * ( self._node_temperatures[ node ] + b/a )*( np.exp( a*time_step ) - 1 ) - b/a )
            result.append( { 'T_avg': T_avg, 'T_final': T_final } )
            
        return result
    
    def __setattr__(self, name, value):
        
        if type(name) is not str:
            raise TypeError("StorageTank.__setattr__: 'name' must be a string.")
            
        if name.startswith("inlet"):
            if hasattr( self, '_' + name ):
                raise AttributeError(f"StorageTank: Attribute {name} is read-only.")
            else:
                raise AttributeError(f"StorageTank: Attribute {name} cannot be set manually.")
                
        if name.startswith("outlet"):
            if hasattr( self, '_' + name ):
                raise AttributeError(f"StorageTank: Attribute {name} is read-only.")
            else:
                raise AttributeError(f"StorageTank: Attribute {name} cannot be set manually.")
        
        super().__setattr__(name, value)
        
    def __getattr__(self, name):
        
        if type(name) is not str:
            raise TypeError("StorageTank.__getattr__: 'name' must be a string.")
        
        if name.startswith( "inlet" ):
            if hasattr(self, "_" + name ):
                return getattr( self, "_" + name  )
            raise AttributeError(f"StorageTank: Attribute '{name}' has not been set.")
            
        if name.startswith( "outlet" ) and hasattr(self, "_" + name ):
            return getattr( self, "_" + name  )
        
        raise AttributeError(f"StorageTank: Attribute '{name}' not recognized.")
    
    def set_connections(self, **kwargs):
        
        if not hasattr( self, "_inlet_nodes" ):
            raise AttributeError("StorageTank.set_connections: Inlet and outlet nodes have not been define. Use the method StorageTank.set_io_relative_heights.")
        
        n_inlets = len( self._inlet_nodes )
        
        for inlet_name in kwargs:
            try:
                inlet_name_split = inlet_name.split( '_' )
                assert len( inlet_name_split ) == 2
                assert inlet_name_split[0] == 'inlet'
                inlet_number = int( inlet_name_split[1] )
                assert inlet_number >= 1 and inlet_number <= n_inlets + 1
            except:
                ValueError(f"StorageTank.set_connections: Unexpected parameter name: {inlet_name}")
            if not isinstance( kwargs[ inlet_name ] , Outlet ):
                raise TypeError(f"StorageTank.set_connections: {inlet_name} is expected to be an instance of sercpy.devices.Outlet.")
            setattr( self, '_' + inlet_name , kwargs[ inlet_name ] )
            
    def set_convergence_criteria( self, *,
                                  relative_tolerance: float,
                                  temp_tolerance: Optional[ float ] = None,
                                  h_tolerance: Optional[ float ] = None,
                                  temp_normalization_range: Optional[ float ] = None,
                                  h_normalization_range: Optional[ float ] = None ):
        """
        Method for the user to establish the convergence criteria of the `StorageTank` instance.
        
        When used in the context of a simulation, a `StorageTank` instance determines that convergence has been achieved when the inputs received by it in consecutive iterations of the same time step differ in less that a certain margin.
        The aforementioned "margin" or "tolerance" is set by this method.
        When covergence is achieved for all components of a simulation, the results are recorded for the current time step and the simulation proceeds to the following time step.
        
        The parameter `relative_tolerance` is the relative discrepancy allowed between any type of input (flowrate, power, etc.) but temperature and specific enthalpy.
        
        For temperature and specific enthalpy, convergence is not evaluated in terms of relative differences but in terms of absolute differences (°C for temperature, J/kg for specific enthalpy).
        Moreover, it is only mandatory to set a tolerance for **ONE** of these two quantities (though the user may also specify values for both of them).
        
        There are two ways of setting the tolerances for temperature and specific enthalpy:
            
            - By directly setting their values (e.g. 0.01 °C for temperature, 50 J/kg for enthalpy).
            - By setting a "normalization range". The absolute tolerance is then determined with the result `relative_tolerance * normalization_range`. E.g.: if the value of `relative_tolerance` has been set to 1e-3, and the normalization range for temperature is set to 30 °C (which may be the difference between the maximum and minimum temperatures at which the system operates), then the absolute tolerance for temperature would be 0.03 °C.
        
        Parameters
        ----------
        
        Only the first parameter is always needed. At least one of the four latter parameters is needed. See the method's descritpion for more details.
        
        relative_tolerance : float
            Maximum relative difference allowed for all input types except temperature and specific enthalpy. In the case of the `StorageTank`
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
            raise TypeError("StorageTank.set_convergence_criteria: 'relative_tolerance' must be convertible to type 'float'.")
        
        self._relative_tolerance = relative_tolerance
        
        if sum( [ variable is not None for variable in [ 
                
                temp_tolerance,
                h_tolerance,
                temp_normalization_range,
                h_normalization_range,
                
                ] ] ) != 1:
            
            raise ValueError("StorageTank.set_convergence_criteria: One and only one of the optional parameters must be provided: 'temp_tolerance', 'h_tolerance', 'temp_normalization_range', 'h_normalization_range'.")
        
        if all([ variable is None for variable in [ temp_tolerance, temp_normalization_range, h_tolerance, h_normalization_range ] ]):
            raise ValueError("StorageTank.set_convergence_criteria: At least one of the following parameters must be provided: 'temp_tolerance', 'temp_normalization_range', 'h_tolerance', 'h_normalization_range'.")
        
        elif temp_tolerance is not None and temp_normalization_range is not None:
            raise ValueError("StorageTank.set_convergence_criteria: Parameters 'temp_tolerance' and 'temp_normalization_range' cannot be provided together.")
        
        elif h_tolerance is not None and h_normalization_range is not None:
            raise ValueError("StorageTank.set_convergence_criteria: Parameters 'h_tolerance' and 'h_normalization_range' cannot be provided together.")
            
        if temp_tolerance is not None:
            try:
                temp_tolerance = float( temp_tolerance )
            except:
                raise TypeError("StorageTank.set_convergence_criteria: 'temp_tolerance' must be convertible to type 'float'.")
            self._temp_tolerance = temp_tolerance
            
        elif temp_normalization_range is not None:
            try:
                temp_normalization_range = float( temp_normalization_range )
            except:
                raise TypeError("StorageTank.set_convergence_criteria: 'temp_normalization_range' must be convertible to type 'float'.")
            self._temp_tolerance = relative_tolerance*temp_normalization_range
        
        else:
            self._temp_tolerance = None
        
        if h_tolerance is not None:
            try:
                h_tolerance = float( h_tolerance )
            except:
                raise TypeError("StorageTank.set_convergence_criteria: 'h_tolerance' must be convertible to type 'float'.")
            self._h_tolerance = h_tolerance
        elif h_normalization_range is not None:
            try:
                h_normalization_range = float( h_normalization_range )
            except:
                raise TypeError("StorageTank.set_convergence_criteria: 'h_normalization_range' must be convertible to type 'float'.")
            self._h_tolerance = relative_tolerance*h_normalization_range
        
        else:
            self._h_tolerance = None
        
        if self._temp_tolerance is not None and not ( self._temp_tolerance >= 1e-5 and self._temp_tolerance <= 1 ):
            raise ValueError(f"StorageTank.set_convergence_criteria: 'temp_tolerance' value ( equal to {self._temp_tolerance} ) is out of the allowed range: 1e-5 to 1.")
        
        if self._h_tolerance is not None and not ( self._h_tolerance >= 1e-2 and self._h_tolerance <= 5000 ):
            raise ValueError(f"StorageTank.set_convergence_criteria: 'h_tolerance' value ( equal to {self._h_tolerance} ) is out of the allowed range: 1e-2 to 5000.")
    
    def _compute_convergence(self, flowrate_list, state_in_list ):
        """
        Method that compares the current inputs with the last inputs received, and determines whether the convergence criteria are met.

        Parameters
        ----------
        flowrate_list : list of float
            List of flowrate values received by the storage tank (one per inlet) (kg/s).
        state_in_list : sercpy.fluids.FluidState
            List of fluid states received by the solar field (one per inlet).
        
        Returns
        -------
        None.
        
        """
        convergence = True
        
        for i, flowrate in enumerate( flowrate_list ):
            
            if flowrate == 0 or self._flowrate_last == 0:
                convergence = convergence and flowrate == self._flowrate_last[ i ]
            elif flowrate != self._flowrate_last:
                convergence = convergence and abs( flowrate - self._flowrate_last[ i ] ) / min( [ flowrate  , self._flowrate_last[ i ] ] ) <= self._relative_tolerance
        
        for i, state_in in enumerate( state_in_list ):
            if self._h_tolerance is not None:
                convergence = convergence and abs( state_in.h - self._state_in_last[ i ].h ) <= self._h_tolerance
            
            if self._temp_tolerance is not None:
                convergence = convergence and abs( state_in.T - self._state_in_last[ i ].T ) <= self._temp_tolerance
            
        self._convergence = convergence
        
    def _set_last_inputs( self, inlet_flowrates, inlet_states ):
        """
        Method that updates the last inputs received by the SolarField instance. These attributes are then used to evaluate the whether convergence is achieved.
        
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
        
        self._flowrate_last = inlet_flowrates
        self._state_in_last = inlet_states
    
    def compute_outputs(self, operating_conditions, iteration_number, *,
                        inlet_flowrates = None, inlet_states = None,
                        Tamb = None, time_step = None):
        """
        Method that determines the average temperatures of the nodes during the current time step and the temperatures of the nodes at the end of the time step.
        It also yields energetic results, the number of iterations, and information on whether convergence was achieved.
        ATTENTION: This method does NOT update the nodes' temperatures when it is used. I.e. the attribute Tank.node_temperatures continues to be the same after using this method.
        In order to update the nodes' temperatures to the values determined by this method, the Tank.update_temperature method has to be used after using this method.

        Parameters
        ----------
            - inlet_1_mass_flow : float or int (positive or zero)
                  mass flow rate entering the tank through inlet 1
            - inlet_1_h : float or int
                  enthalpy of the flow entering the tank through inlet 1
            - inlet_2_mass_flow : float or int (positive or zero)
                  mass flow rate entering the tank through inlet 2
            - inlet_2_h : float or int
                  enthalpy of the flow entering the tank through inlet 2
            - Tamb : float or int
                  ambient temperature
            - time_step : float or int  (positive)
                  time step value (time units)

        Returns
        -------
            dictionary
                the returned object is a dictionary with the following keys:
                    - 'outlet_1_h' : enthalpy of the flow leaving the tank through outlet 1
                    - 'outlet_2_h' : enthalpy of the flow leaving the tank through outlet 2
                    - 'flow_1_Q' : thermal power RECEIVED BY THE TANK from flow 1 (i.e. the flow entering through inlet 1 and leaving through outlet 1)
                    - 'flow_2_Q' : thermal power RECEIVED BY THE TANK from flow 2 (i.e. the flow entering through inlet 2 and leaving through outlet 2)
                    - 'Q_loss' : Heat losses through the walls of the tank (in power units). It is positive when the tank loses energy.
                    - 'iterations' : Number of iterations executed.
                    - 'maxIt' : Boolean value which is True if the maximum number of allowed iterations was reached without achieving convergence, and False otherwise
        """
        
        if operating_conditions is None and iteration_number is None:
            if any([ variable is None for variable in [ inlet_flowrates, inlet_states, Tamb, time_step ] ]):
                raise TypeError("StorageTank.compute_outputs: Not all parameters needed for manual mode were provided. Parameters needed: inlet_flowrates, inlet_states, Tamb, time_step.")
            self._convergence = False
            
        elif operating_conditions is None or iteration_number is None:
            raise TypeError("StorageTank.compute_outputs: Both 'operating_conditions' and 'operating_conditions' must be provided in simulation mode. None of them must be provided in manual mode.")
        
        else:
            
            if type( operating_conditions ) is not dict:
                raise TypeError("StorageTank.compute_outputs: Parameter 'operating_conditions' must be a dictionary.")
            if not ( type( iteration_number ) is int and iteration_number >= 0 ):
                raise TypeError("StorageTank.compute_outputs: Parameter 'iteration_number' must be an 'int'. Its value msut be >= 0.")
            
            inlet_flowrates = []
            inlet_states = []
            for i in range( len( self._inlet_nodes ) ):
                if not hasattr( self, "_inlet_" + str( i + 1 ) ):
                    raise AttributeError( f"StorageTank.compute_outputs: Attribute '{ 'inlet_' + str( i + 1 ) }' is not defined. Use the method StorageTank.set_connections." )
                outlet = getattr( self, "_inlet_" + str( i + 1 ) )
                inlet_flowrates.append( outlet.flowrate )
                inlet_state = outlet.state
                if not inlet_state.fluid is self._stored_fluid:
                    raise ValueError(f"StorageTank.compute_outputs: Fluid entering through inlet {i + 1} is not the same fluid that is stored by the tank.")
                inlet_states.append( inlet_state )
                
            if iteration_number == 0:
                self._set_last_inputs(inlet_flowrates, inlet_states)
                self._convergence = False
            else:
                self._compute_convergence(inlet_flowrates, inlet_states)
                if self._convergence:
                    return
                else:
                    self._set_last_inputs(inlet_flowrates, inlet_states)
            
            Tamb = operating_conditions[ 'Tamb' ]
            time_step = operating_conditions[ 'time_step' ]
        
        inlet_temps = [ state_in.T for state_in in inlet_states ]
        
        distributions_list = self.set_inlet_flows( inlet_flowrates, inlet_temps )
        
        # The result of the "iteration 0" is defined as the current nodes' temperatures
        previous_result = [ {'T_avg': self._node_temperatures[ node ], 'T_final': self._node_temperatures[ node ] } for node in range( self._n_nodes ) ]
        # Outputs are determined by using the Tank.iteration method iteratively
        it = 0
        while True:
            new_result = self._iteration( inlet_flowrates, inlet_temps,
                                          Tamb, previous_result, time_step,
                                          distributions_list )
            it = it + 1
            if self._compute_internal_convergence(previous_result, new_result):
                self._internal_convergence = True
                self._iterations = it
                break
            if it == self._max_iterations:
                self._internal_convergence = False
                self._iterations = it
                break
            previous_result = new_result
        # Nodes are mixed if temperature inversions are detected (see StorageTank._mix_nodes method)
        new_result = self._mix_nodes( new_result )
        # Outputs are defined
        
        for i in range( len( self._outlet_nodes ) ):
            outlet = getattr( self, "_outlet_" + str( i + 1 ) )
            outlet.flowrate = inlet_flowrates[ i ]
            outlet.state = self._stored_fluid.state( T = new_result[ self._outlet_nodes[ i ] ][ 'T_avg' ] )
        
        self._new_temperatures = [ node_temps[ 'T_final' ] for node_temps in new_result ]
        
        self._dE = self._node_thermal_capacity * sum( [  self._new_temperatures[ node ] - self._node_temperatures[ node ] for node in range( len( self._new_temperatures ) )  ] )
        
        Heat_Loss_Rate = self._nodal_edge_area * self._edge_loss_coeff * sum([ new_result[ node ][ 'T_avg' ] - Tamb for node in range( len( new_result ) ) ] )
        Heat_Loss_Rate = Heat_Loss_Rate + self._cross_area * self._top_loss_coeff * ( new_result[ 0 ][ 'T_avg' ] - Tamb )
        Heat_Loss_Rate = Heat_Loss_Rate + self._cross_area * self._bottom_loss_coeff * ( new_result[ self._n_nodes - 1 ][ 'T_avg' ] - Tamb )
        
        self._Q_loss = Heat_Loss_Rate
        self._iterations = it
    
    def update_state( self ):
        """
        Method to update the nodes' temperatures to the result computed the last time the method Tank.compute_outputs was used.
        If only the Tank is being simulated, this method should be used right after the Tank.compute_outputs method.
        If a whole system is being simulated, this method should be used when the rest of the system achieves convergence.
        """
        self._node_temperatures = self._new_temperatures