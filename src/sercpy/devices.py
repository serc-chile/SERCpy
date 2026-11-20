# -*- coding: utf-8 -*-
"""
Created on Wed Oct 14 09:46:22 2026

@author: Adrian Riebel Brummer
"""

from .fluids import FluidState

class Outlet:
    """
    This very simple class has two concrete goals:
        
        1. To store the conditions of the flow that is leaving a device. These conditions are: its thermodynamic state and its flowrate.
        2. To pass the aforementioned information to the device that receives the flow.
        
    Instances of this class are meant to be attributes of the devices that make up a thermal system. A connection between two devices can be set in the following way:
    
    .. code-block:: python
    
        from sercpy.solar import SolarField
        from sercpy.heat_exchanger import HeatExchanger
        
        #Create SolarField instance
        solar_field = SolarField( ... )
        
        #Create HeatExchanger instance
        heat_exchanger = HeatExchanger( ... )
        
        # Connect an outlet of the heat exchanger to the inlet of the solar field
        solar_field.set_connections( inlet = heat_exchanger.outlet_source )
    
    After doing this, `solar_field` will compute its outputs using the flow data
    extracted from `heat_exchanger.outlet_source`,
    which is one of the two outlets of `heat_exchanger`.
    The structure of the `SolarField` class would roughly look as follows:
        
    .. code-block:: python
    
        class SolarField:
            
            def __init__(self):
                
                # Set attribute 'outlet'
                self.outlet = Outlet()
            
            # Method to define the inlet (i.e. another device's outlet from which the inputs are extracted)
            
            def set_connections( self, *, inlet ):
                
                # Check the class of the argument 'inlet'
                if not isinstance(inlet, Outlet):
                    raise TypeError("SolarField.set_connections: Argument 'inlet' must be an instance of Outlet.")
                
                # Set the attribute
                self.inlet = inlet
            
            # compute_outputs : the main method of any device
            def compute_outputs( self, operating_conditions, iteration_number ):
                
                # Extract inputs
                flowrate = self.inlet.flowrate
                state_in = self.inlet.state
                
                # Compute power
                power = self._compute_power( operating_conditions, flowrate, state_in )
                
                # Compute outlet enthalpy and outlet state
                h_out = state_in.h + power / flowrate
                state_out = state_in.fluid.state( h = h_out )
                
                # Set outlet conditions
                self.outlet.flowrate = flowrate
                self.outlet.state = state_out
    
    """
    
    @property
    def state(self):
        if not hasattr( self, "_state" ):
            raise AttributeError("Outlet: Attribute 'state' has not been defined.")
        return self._state
    
    @state.setter
    def state( self, state ):
        if not isinstance(state, FluidState):
            raise TypeError("Outlet: state must be an instance of sercpy.fluids.FluidState.")
        self._state = state
    
    @property
    def flowrate(self):
        if not hasattr( self, "_flowrate" ):
            raise AttributeError("Outlet: Attribute 'flowrate' has not been defined.")
        return self._flowrate
    
    @flowrate.setter
    def flowrate(self, flowrate):
        if flowrate is None:
            self._flowrate = None
            return
        try:
            flowrate = float(flowrate)
        except:
            raise TypeError("Outlet: flowrate must be a numeric value.")
        if flowrate < 0:
            raise ValueError(f"Outlet: Flowrate cannot be negative. Flowrate value introduced: {flowrate}")
        self._flowrate = flowrate
        
    @property
    def T(self):
        if not hasattr( self, "_state" ):
            raise AttributeError("Outlet: Attribute 'state' has not been defined.")
        return self._state.T
    
    @property
    def temp(self):
        return self.T
    
    @property
    def h(self):
        if not hasattr( self, "_state" ):
            raise AttributeError("Outlet: Attribute 'state' has not been defined.")
        return self._state.h
    


class Device:
    """
    Base class for the objects that model
    the individual components of a thermal system.
    
    This class is not meant to be used as-is,
    but to define inherited device-type classes.
    
    The default initializing function takes no parameters,
    sets the attribute `convergence` to `True`,
    and assigns an :ref:`Outlet <class_outlet>`
    instance which is accessible with
    the attribute name `outlet`.
    
    The method `compute_outputs`, which
    is the most relevant for devices in **SERCpy**,
    is empty in this base class, and
    should be overriden in inherited classes.
    
    Attributes
    ----------
    convergence : bool
        This boolean value should become
        `True` when the device-type object
        is in the right conditions to stop
        the iterations for the current time step.
        For most devices, this implies that the input
        values used to compute the outputs were
        similar enough in consecutive iterations.
        Some devices, however, such as :doc:`pumps <pump/pump>`
        and :doc:`controllers <controller/controller>`,
        require additional conditions to be satisfied.
        
    outlet : :ref:`class_outlet`
        The base `Device` class has an outlet by default, which can be used to
        store the device's outputs and pass them to other devices. More outlets
        can be assigned in inherited classes,
        and all of them must have names that begin with 'outlet'.
        
    inlet_1, inlet_2, ... : :ref:`class_outlet`
        Outlets of other devices from which the `Device` instance
        extracts its inputs. These attributes must be assigned through the
        method `Device.set_connections`.
        
    controller : :doc:`Controller <controller/controller>`
        :doc:`Controller <controller/controller>` instance
        that controls the device's operation.
        Not all devices must have a controller.
        This attribute must be assigned through the
        method `Device.set_connections`.
    
    """
    
    def __init__(self):
        
        self._convergence = True
        self.outlet = Outlet()
    
    @property
    def convergence(self):
        if not hasattr( self, "_convergence" ):
            class_name = self.__class__.__name__
            raise AttributeError(f"{ class_name }: Attribute 'convergence' has not been defined.")
        return self._convergence
    
    @convergence.setter
    def convergence(self, value):
        if not ( type( value ) is bool or value in [ 0, 1 ] ):
            class_name = self.__class__.__name__
            raise TypeError(f"{class_name}: Attribute 'convergence' must be a boolean value (True or False).")
        self._convergence = bool( value )
    
    def set_convergence_criteria( self, *,
                                  relative_tolerance,
                                  temp_tolerance = None,
                                  h_tolerance = None,
                                  temp_normalization_range = None,
                                  h_normalization_range = None ):
        """
        Establish the convergence criteria of the `Device` instance inside a simulation.
        
        When used in the context of a simulation, a `Device`
        instance determines that "input convergence"
        has been achieved when the inputs received by it in
        consecutive iterations of the same time
        step differ in less that a certain margin.
        The aforementioned "margin" or "tolerance" is set by this method.
        When covergence is achieved for all components of a simulation,
        the results are recorded for the current time step
        and the simulation proceeds to the following time step.
        
        The argument `relative_tolerance` is the relative discrepancy allowed
        between any type of input (flowrate, control signal, etc.)
        but temperature and specific enthalpy.
        
        For temperature and specific enthalpy, convergence is not evaluated
        in terms of relative differences but in terms of absolute
        differences (°C for temperature, J/kg for specific enthalpy).
        Moreover, it is only mandatory to set a tolerance for **ONE**
        of these two quantities (though the user may also specify values for both of them).
        
        There are two ways of setting the tolerances for temperature and specific enthalpy:
            
            - By directly setting their values (e.g. 0.01 °C for temperature, 50 J/kg for enthalpy).
            - By setting a "normalization range". The absolute tolerance is
              then determined with the result `relative_tolerance * normalization_range`.
              E.g.: if the value of `relative_tolerance` has been set to 1e-3,
              and the normalization range for temperature is set to 30 °C
              (which may be the difference between the maximum and
              minimum temperatures at which the system operates),
              then the absolute tolerance for temperature would be 0.03 °C.
              A normalization range may also be specified as a
              pair (i.e. a tuple or list of two numbers);
              in that case the two numbers are interpreted
              as the minimum and maximum value of the range,
              and therefore the difference between them is used.
        
        **Only the first parameter is always needed. At least one of the four
        latter parameters is needed. See the method's descritpion above for more details.**
        
        Parameters
        ----------
        relative_tolerance : float
            Maximum relative difference allowed for all input types except
            temperature and specific enthalpy. Valid range: `1e-8` to `5e-2`.
        
        temp_tolerance : float, optional
            Absolute temperature difference allowed (°C). Valid range: `1e-5` to `2`.
        
        h_tolerance : float, optional
            Absolute enthalpy difference allowed (J/kg). Valid range: `1e-2` to `10000`.
        
        temp_normalization_range : float or pair, optional
            Normalization range for temperature. See the description above for more details.
        
        h_normalization_range : float or pair, optional
            Normalization range for specific enthalpy. See the description above for more details.
        
        Returns
        -------
        None.
        
        """
        
        class_name = self.__class__.__name__
        
        try:
            relative_tolerance = float( relative_tolerance )
        except:
            raise TypeError( f"{ class_name }.set_convergence_criteria: 'relative_tolerance' must be convertible to type 'float'." )
            
        if not ( relative_tolerance >= 1e-8 and relative_tolerance <= 5e-2 ):
            raise ValueError( f"{ class_name }.set_convergence_criteria: Argument 'relative_tolerance' must be in the range 1e-8 <= relative_tolerance <= 1e-1." )
        
        self._relative_tolerance = relative_tolerance
        
        if all([ variable is None for variable in [ temp_tolerance, temp_normalization_range, h_tolerance, h_normalization_range ] ]):
            raise ValueError( f"{ class_name }.set_convergence_criteria: At least one of the following arguments must be provided: 'temp_tolerance', 'temp_normalization_range', 'h_tolerance', 'h_normalization_range'.")
        
        elif temp_tolerance is not None and temp_normalization_range is not None:
            raise ValueError( f"{ class_name }.set_convergence_criteria: Arguments 'temp_tolerance' and 'temp_normalization_range' cannot be provided together.")
        
        elif h_tolerance is not None and h_normalization_range is not None:
            raise ValueError( f"{ class_name }.set_convergence_criteria: Arguments 'h_tolerance' and 'h_normalization_range' cannot be provided together.")
            
        if temp_tolerance is not None:
            try:
                temp_tolerance = float( temp_tolerance )
            except:
                raise TypeError( f"{ class_name }.set_convergence_criteria: 'temp_tolerance' must be convertible to type 'float'.")
            self._temp_tolerance = temp_tolerance
            
        elif temp_normalization_range is not None:
            try:
                temp_normalization_range = float( temp_normalization_range )
            except TypeError:
                try:
                    temp_normalization_range = list( temp_normalization_range )
                    assert len( temp_normalization_range ) == 2
                    assert temp_normalization_range[ 1 ] > temp_normalization_range[0]
                    temp_normalization_range = float( temp_normalization_range[ 1 ] - temp_normalization_range[ 0 ] )
                except:
                    raise TypeError( f"{ class_name }.set_convergence_criteria: 'temp_normalization_range' must be a number of a pair of two numbers. In the latter case, the second number must be larger than the first one.")
            self._temp_tolerance = relative_tolerance*temp_normalization_range
        
        else:
            self._temp_tolerance = None
        
        if h_tolerance is not None:
            try:
                h_tolerance = float( h_tolerance )
            except:
                raise TypeError( f"{ class_name }.set_convergence_criteria: 'h_tolerance' must be convertible to type 'float'.")
            self._h_tolerance = h_tolerance
        elif h_normalization_range is not None:
            try:
                h_normalization_range = float( h_normalization_range )
            except TypeError:
                try:
                    h_normalization_range = list( h_normalization_range )
                    assert len( h_normalization_range ) == 2
                    assert h_normalization_range[ 1 ] > h_normalization_range[0]
                    h_normalization_range = float( h_normalization_range[ 1 ] - h_normalization_range[ 0 ] )
                except:
                    raise TypeError( f"{ class_name }.set_convergence_criteria: 'h_normalization_range' must be a number of a pair of two numbers. In the latter case, the second number must be larger than the first one.")
            self._h_tolerance = relative_tolerance*h_normalization_range
        
        else:
            self._h_tolerance = None
        
        if self._temp_tolerance is not None and not ( self._temp_tolerance >= 1e-5 and self._temp_tolerance <= 2 ):
            raise ValueError( f"{ class_name }.set_convergence_criteria: 'temp_tolerance' value ( equal to {self._temp_tolerance} ) is out of the allowed range: 1e-5 to 1.")
        
        if self._h_tolerance is not None and not ( self._h_tolerance >= 1e-2 and self._h_tolerance <= 10000 ):
            raise ValueError( f"{ class_name }.set_convergence_criteria: 'h_tolerance' value ( equal to {self._h_tolerance} ) is out of the allowed range: 1e-2 to 5000.")

    def compute_input_convergence( self, *, relative_inputs = None, state_inputs = None, prior = True ):
        """
        Method that compares the current inputs with the last inputs received,
        and determines whether the convergence criteria are met.
        
        Parameters
        ----------
        flowrate_list : list of float
            List of flowrate values received by the storage tank (one per inlet) (kg/s).
        state_in_list : sercpy.fluids.FluidState
            List of fluid states received by the storage tank (one per inlet).
        
        Returns
        -------
        None.
        
        """
        class_name = self.__class__.__name__
        from .controller import Controller
        
        if not hasattr( self, "_relative_tolerance" ):
            raise AttributeError(f"{ class_name }.compute_input_convergence: Attribute '_relative_tolerance' has not been defined. Use the method { class_name }.set_convergence_criteria.")
        
        if relative_inputs is None:
            relative_inputs = []
        
        if state_inputs is None:
            state_inputs = []
        
        if hasattr( self, "_connections_dict" ):
            try:
                for name in self._connections_dict:
                    if isinstance( self._connections_dict[ name ], Outlet ):
                        relative_inputs.append( self._connections_dict[ name ].flowrate )
                        state_inputs.append( self._connections_dict[ name ].state )
                    if isinstance( self._connections_dict[ name ], Controller ):
                        relative_inputs.append( self._connections_dict[ name ].control_signal )
            except:
                self._convergence = False
                return
        
        if not prior:
            self._relative_inputs_last, self._state_inputs_last = relative_inputs, state_inputs
            self._convergence = False
            return
        
        if len( relative_inputs ) == 0 and len( state_inputs ) == 0:
            self._convergence = True
            return
        elif not hasattr( self, "_relative_inputs_last" ):
            self._relative_inputs_last, self._state_inputs_last = relative_inputs, state_inputs
            self._convergence = False
            return
        
        convergence = True
        for i in range( len( relative_inputs ) ):
            current_input = relative_inputs[ i ]
            last_input = self._relative_inputs_last[ i ]
            
            if current_input == 0 or last_input == 0:
                convergence = convergence and current_input == last_input
            elif current_input != last_input:
                convergence = convergence and abs( current_input - last_input ) / min( [ current_input  , last_input ] ) <= self._relative_tolerance
        
        if self._temp_tolerance is not None:
            for i in range( len( state_inputs ) ):
                convergence = convergence and abs( state_inputs[ i ].T - self._state_inputs_last[ i ].T ) <= self._temp_tolerance
        
        if self._h_tolerance is not None:
            for i in range( len( state_inputs ) ):
                convergence = convergence and abs( state_inputs[ i ].h - self._state_inputs_last[ i ].h ) <= self._h_tolerance
        
        self._convergence = convergence
        
        if self._convergence is False:
            self._relative_inputs_last, self._state_inputs_last = relative_inputs, state_inputs
            
    def __setattr__(self, name, value):
        """
        Custom method to set the attributes of the `Device` instance.
        
        It handles the following special cases:
            
            - If the attribute's name starts with 'inlet' or es equal to 'controller',
              it throws an error since inlets and the controller must be set through the method
              'Device.set_connections'.
            
            - If the attribute's name starts with 'outlet', it puts an underscore before
              the name of the attribute that is actually assigned.
        
        Returns
        -------
        None.
        
        """
        
        class_name = self.__class__.__name__
        
        if name.startswith( "inlet" ):
            raise TypeError(f"{class_name}: Attributes whose names start with 'inlet' must be specified with the method '{class_name}.set_connections'.")
        elif name == 'controller':
            raise TypeError(f"{class_name}: 'controller' is a reserved attribute name. This attribute must be specified with the method '{class_name}.set_connections'.")
        
        if isinstance( value, Outlet ) and not name.startswith( "outlet" ):
            raise TypeError(f"{class_name}: Outlet instance assigned as attributes must have names starting with 'outlet'.")
        
        if name.startswith( "outlet" ):
            if hasattr( self, "_" + name ):
                raise TypeError(f"{class_name}: Attributes whose names start with 'outlet' are special attributes that can not be re-defined.")
            elif not isinstance( value, Outlet ):
                raise TypeError(f"{class_name}: Attributes whose names start with 'outlet' must be instances of sercpy.devices.Outlet.")
            name = "_" + name
        
        super().__setattr__(name, value)
        
    def __getattr__(self, name):
        """
        Custom method that returns the following attributes:
            
            - Inlets, which are set through the method 'Device.set_connections'
            - Controller, which is set through the method 'Device.set_connections'
            - Outlets

        """
        
        class_name = self.__class__.__name__
        
        if name.startswith( "inlet" ) or name == 'controller':
            if hasattr( self, "_" + name ):
                return getattr( self, "_" + name )
            raise AttributeError(f"{class_name}: Attribute {name} has not been defined. This attribute should be specified with {class_name}.set_connections.")
        
        if name.startswith( "outlet" ):
            if hasattr( self, "_" + name ):
                return getattr( self, "_" + name )
            raise AttributeError(f"'{class_name}' instance does not have an outlet called '{name}'")
        
        raise AttributeError(f"'{class_name}' object has no attribute '{name}'")
    
    def set_connections( self, **kwargs ):
        """
        Set the connections with other devices of the thermal system.
        
        This method allows the user to specify other device-type objects from
        which the `Device` instance receives its inputs during a simulation.
        
        The arguments passed to this function should be either
        :ref:`Outlet <class_outlet>` or :doc:`Controller </controller/controller>`
        instances.
        
        Parameters
        ----------
        **kwargs : TYPE
            DESCRIPTION.

        Raises
        ------
        TypeError
            DESCRIPTION.

        Returns
        -------
        None.

        """
        
        from .controller import Controller
        class_name = self.__class__.__name__
        
        for name in kwargs:
            
            if name.startswith( "inlet" ):
                if not ( kwargs[ name ] is None or isinstance( kwargs[ name ], Outlet ) ):
                    raise TypeError(f"{class_name}.set_connections: Keyword arguments starting with 'inlet' are expected to be instances of sercpy.devices.Outlet.")
            elif name == "controller":
                if not ( kwargs[ name ] is None or isinstance( kwargs[ name ], Controller ) ):
                    raise TypeError(f"{class_name}.set_connections: Keyword argument 'controller' is expected to be an instance of sercpy.devices.Controller.")
            else:
                raise TypeError(f"{class_name}.set_connections: Keyword arguments are expected to be 'controller' or to begin with 'inlet'.")
                
            if kwargs[ name ] is None:
                continue
                
            if hasattr( self, "_connections_dict" ):
                self._connections_dict[ name ] = kwargs[ name ]
            else:
                self._connections_dict = { name: kwargs[ name ] }
            
            attr_name = "_" + name
        
            super().__setattr__(attr_name, kwargs[ name ])
    
    def compute_outputs( self, operating_conditions = None, iteration_number = None, **kwargs ):
        """
        This empty method should be overriden in any functional inherited class.
        
        It is the method that is called during a
        simulation to compute the outputs that are passed
        to other devices in order to
        simulate the device operating as part of a
        thermal system.
        
        **The first two parameters are meant to be used to call the method
        when the device is used as part of a system simulation.**

        Parameters
        ----------
        operating_conditions : dict
            Dictionary returned by a .
        iteration_number : TYPE
            DESCRIPTION.
        **kwargs : any
            Extra parameters that will **NOT** be considered when the device is
            used in a system simulation. These parameters can be used, for instance,
            to obtain results from the device outside of simulations.

        Returns
        -------
        None.

        """
        return
    
    def update_state(self):
        return
    
class SystemInlet( Device ):
    
    def __init__(self):
        
        self.outlet = Outlet()
    
    def compute_outputs( self, operating_conditions, iteration_number ):
        
        if iteration_number == 0:
            
            self.outlet.flowrate = operating_conditions[ "flowrate" ]
            self.outlet.state = operating_conditions[ "fluid" ].state( T = operating_conditions[ "T_in" ] )
            self._convergence = False
            return
        
        self._convergence = True