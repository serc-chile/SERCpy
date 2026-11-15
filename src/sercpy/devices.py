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
    
    After doing this, `solar_field` will compute its outputs using the flow data extracted from `heat_exchanger.outlet_source`, which is one of the two outlets of `heat_exchanger`.
    
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
    
    @property
    def input_convergence(self):
        if hasattr( self, "_convergence" ):
            return self._input_convergence
        return True
    
    @input_convergence.setter
    def input_convergence(self, value):
        try:
            value = bool( value )
        except:
            raise TypeError("Device: convergence must be a boolean value.")
        self._input_convergence = value
    
    def update_state(self):
        return
    
    def set_convergence_criteria( self, *,
                                  relative_tolerance,
                                  temp_tolerance,
                                  h_tolerance,
                                  temp_normalization_range,
                                  h_normalization_range ):
        """
        Establish the convergence criteria of the `Device` instance in the context of a simulation.
        
        When used in the context of a simulation, a `Device` instance determines that "input convergence"
        has been achieved when the inputs received by it in
        consecutive iterations of the same time step differ in less that a certain margin.
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
              A normalization range may also be specified as a pair (i.e. a tuple or list of two numbers);
              in that case the two numbers are interpreted as the minimum and maximum value of the range,
              and therefore the difference between them is used.
        
        **Only the first parameter is always needed. At least one of the four latter parameters is needed. See the method's descritpion above for more details.**
        
        Parameters
        ----------
        relative_tolerance : float
            Maximum relative difference allowed for all input types except
            temperature and specific enthalpy. Valid range: `1e-8` to `1e-2`.
        
        temp_tolerance : float, optional
            Absolute temperature difference allowed (°C). Valid range: `1e-5` to `1`.
        
        h_tolerance : float, optional
            Absolute enthalpy difference allowed (J/kg). Valid range: `1e-2` to `5000`.
        
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
            
        if not ( relative_tolerance >= 1e-8 and relative_tolerance <= 1e-2 ):
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
        
        if self._temp_tolerance is not None and not ( self._temp_tolerance >= 1e-5 and self._temp_tolerance <= 1 ):
            raise ValueError( f"{ class_name }.set_convergence_criteria: 'temp_tolerance' value ( equal to {self._temp_tolerance} ) is out of the allowed range: 1e-5 to 1.")
        
        if self._h_tolerance is not None and not ( self._h_tolerance >= 1e-2 and self._h_tolerance <= 5000 ):
            raise ValueError( f"{ class_name }.set_convergence_criteria: 'h_tolerance' value ( equal to {self._h_tolerance} ) is out of the allowed range: 1e-2 to 5000.")

    def _compute_input_convergence( self, *, relative_inputs = None, state_inputs = None ):
        """
        Method that compares the current inputs with the last inputs received, and determines whether the convergence criteria are met.
        
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
        
        if not hasattr( self, "_relative_tolerance" ):
            raise AttributeError(f"{ class_name }._compute_input_convergence: Attribute '_relative_tolerance' has not been defined. Use the method { class_name }.set_convergence_criteria.")
        
        convergence = True
        
        if relative_inputs is not None and hasattr( self, "_relative_inputs_last" ):
            for i in range( len( relative_inputs ) ):
                current_input = relative_inputs[ i ]
                last_input = self._relative_inputs_last[ i ]
                
                if current_input == 0 or last_input == 0:
                    convergence = convergence and current_input == last_input
                elif current_input != last_input:
                    convergence = convergence and abs( current_input - last_input ) / min( [ current_input  , last_input ] ) <= self._relative_tolerance
        
        if self._temp_tolerance is not None and state_inputs is not None:
            
            for i in range( len( state_inputs ) ):
                convergence = convergence and abs( state_inputs[ i ].T - self._state_inputs_last[ i ].T ) <= self._temp_tolerance
        
        if self._h_tolerance is not None and state_inputs is not None:
            
            for i in range( len( state_inputs ) ):
                convergence = convergence and abs( state_inputs[ i ].h - self._state_inputs_last[ i ].h ) <= self._h_tolerance
        
        self._input_convergence = convergence
        
        if self._input_convergence is False:
            self._relative_inputs_last, self._state_inputs_last = relative_inputs, state_inputs
    
    def set_connections( self, **kwargs ):
        return
    
    def compute_outputs( self, operating_conditions, iteration_number, **kwargs ):
        return