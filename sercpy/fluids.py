# -*- coding: utf-8 -*-
"""
Created on Thu Oct 15 10:54:10 2026

@author: Adrian Riebel Brummer
"""

from CoolProp.CoolProp import PropsSI
import numpy as np
import warnings

class StateError(Exception):
    pass

class FluidError(Exception):
    pass

class FluidState:
    """
    Class that stores the properties of a fluid at a single temperature/enthalpy.
    
    Parameters
    ----------
    fluid : sercpy.fluids.Fluid instance
        Instance that computes the properties of the fluid.
        
    kwargs: float
        Allowed keyword arguments are `T`, `h`, and `H`. The first one must be specified if the state is going to be defined from temperature (in °C). Any of the other two must be specified if the state is going to be defined from enthalpy. Only one of these keyword arguments must be provided.
    
    Attributes
    ----------
    fluid : sercpy.fluids.Fluid instance
        Object from which the fluid properties are computed. It is the same object provided at initialization.
    
    T : float
        Temperature in °C.
        
    h : float
        Specific enthalpy in J/kg.
        
    H : float
        Alias for h.
        
    D : float
        Density.
        
    density : float
        Alias for D.
        
    d : float
        Alias for D.
        
    Q : float
        Liquid-vapor mixture quality. It is a value in the range 0 - 1 representing the vapor fraction. It is 0 for completely liquid substances, and 1 for completely gaseous substances.
        
    quality : float
        Alias for Q.
    
    """
    
    def __init__( 
            
            self,
            fluid,
            **kwargs
            
            ):
        
        if not isinstance(fluid, Fluid):
            raise TypeError("FluidState: Argument 'fluid' must be an instance of sercpy.fluids.Fluid.")
        
        self._fluid = fluid
        
        if 'h' in kwargs or 'H' in kwargs:
            if 'h' in kwargs:
                enthalpy_name = 'h'
            elif 'H' in kwargs:
                enthalpy_name = 'H'
            if kwargs[ enthalpy_name ] < self._fluid.h_min:
                warnings.warn(f"Fluid.state: An enthalpy value below the minimum available ({self._fluid.h_min} J/kg) was provided. Minimum value available will be considered.")
                kwargs[ enthalpy_name ] = self._fluid.h_min
            elif kwargs[ enthalpy_name ] > self._fluid.h_max:
                warnings.warn(f"Fluid.state: An enthalpy value above the maximum available ({self._fluid.h_max} J/kg) was provided. Maximum value available will be considered.")
                kwargs[ enthalpy_name ] = self._fluid.h_max
        elif 'T' in kwargs:
            if kwargs[ 'T' ] < self._fluid.T_min:
                warnings.warn(f"Fluid.state: A temperature value below the minimum available ({self._fluid.T_min} J/kg) was provided. Minimum value available will be considered.")
                kwargs[ 'T' ] = self._fluid.T_min
            elif kwargs[ 'T' ] > self._fluid.T_max:
                warnings.warn(f"Fluid.state: A temperature value above the maximum available ({self._fluid.T_max} J/kg) was provided. Maximum value available will be considered.")
                kwargs[ 'T' ] = self._fluid.T_max
            
        if sum( [ variable in kwargs for variable in [ 'h', 'H', 'T' ] ] ) != 1:
            raise StateError( "FluidState: One and only one of the keyword arguments 'h', 'H' and 'T' must be provided." )
            
        if 'h' in kwargs:
            self._h = kwargs[ 'h' ]
        elif 'H' in kwargs:
            self._h = kwargs[ 'H' ]
        elif 'T' in kwargs:
            self._T = kwargs[ 'T' ]
        else:
            raise StateError("FluidState: Unexpected error.")
            
    @property
    def fluid(self):
        return self._fluid
        
    @property
    def T(self):
        
        if not hasattr(self, '_T'):
            self._T = self._fluid.h_to_T( self._h)
            
        return self._T
    
    @property
    def h(self):
        
        if not hasattr( self, '_h' ):
            self._h = self._fluid.T_to_h( self._T )
        
        return self._h
    
    @property
    def H(self):
        return self.h
    
    @property
    def D(self):
        
        if not hasattr( self, '_D' ):
            self._D = self._fluid.h_to_D( self.h )
            
        return self._D
    
    @property
    def density(self):
        return self.D
    
    @property
    def d(self):
        return self.D
    
    @property
    def Q(self):
        
        if not hasattr(self, "_Q"):
            self._Q = self._fluid.h_to_Q( self.h )
                
        return self._Q
    
    @property
    def quality(self):
        return self.Q
    
def _define_polyfit( max_index, x_axis, y_axis ):
    
    for index in range( 1, max_index + 1 ):
        poly_func = np.poly1d( np.polyfit( x_axis, y_axis, index ) )
        estimated_y_axis = [ poly_func( x ) for x in x_axis ]
        error = float( np.max( np.abs( np.array( estimated_y_axis ) - np.array( y_axis ) ) ) )
        if index == 1:
            best_result = error
            best_poly_func = poly_func
            continue
        if error < best_result:
            best_result = error
            best_poly_func = poly_func 
    return best_poly_func
    
class Fluid:
    """
    Class that stores the properties of a heat transfer fluid, at a fixed pressure.
    
    The class can convert specific enthalpy to temperature, and it most cases, also viceversa (unless the saturation temperature is provided as argument).
    
    In the case of water, the instances of these class also store the saturation temperature and the vaporization enthalpy.
    
    Class instances also store the density aas a function of temperature/enthalpy.

    Parameters
    ----------
    fluid_name : str
        Only positional parameter. Valid values are: `"water"`, `"air"`, `"therminol 66"`. 
    
    p_abs_Pa : float, optional
        Absolute pressure in Pascal. Only needed for water and air.
        
    T_ref : float, optional
        Temperature at which to compute the reference density, thermal conductivity, and specific heat capacity. This is needed, in particular, for fluids that will be stored in storage tanks, for whose calculations constant fluid properties are assumed.
    
    Attributes
    ----------
    fluid_name : str
        Name identifying the fluid. Possible values are: `"water"`, `"air"`, `"therminol 66"`, 
    
    h_sat_liq : float
        Specific enthalpy of liquid at saturation (J/kg).
    
    h_sat_vap : float
        Specific enthalpy of vapor at saturation (J/kg).
    
    T_sat : float
        Saturation temperature (°C).
    
    T_min : float
        Minimum temperature for which the properties can be computed (°C).
        
    T_max : float
        Maximum temperature for which the properties can be computed (°C).
    
    h_min : float
        Minimum specific enthalpy for which the properties can be computed (J/kg). It is equal to specific enthalpy at T_min.
    
    h_max : float
        Maximum specific enthalpy for which the properties can be computed (J/kg). It is equal to specific enthalpy at T_max.
    
    cp_ref : float
        Reference specific heat capacity (J/kg °C). It is computed at the temperature given by the argument T_ref.
    
    D_ref : float
        Reference density (kg/m3). It is computed at the temperature given by the argument T_ref.
    
    k_ref : float
        Reference thermal conductivity (W/m °C). It is computed at the temperature given by the argument T_ref.
        
        
    Methods
    -------
    h_to_T( h: float ) -> float
        Convert specific enthalpy (J/kg) to temperature (°C).
    
    T_to_h( T: float ) -> float
        Convert temperature (°C) to specific enthalpy (J/kg). This method fails only when the temperature provided is too close to saturation.
    
    h_to_Q( h: float ) -> float
        Get mixture quality (float in the range 0 - 1) from specific enthalpy (J/kg). Outside saaturation, this method returns 0 for liquids and 1 for gases.
    
    h_to_D( h: float ) -> float
        Get density (kg/m3) from specific enthalpy (J/kg). 
    
    state( **kwargs: float ) -> float
        This method returns a `sercpy.fluids.FluidState` instance, defined from the `Fluid` instance and `kwargs`.
    
    """
    
    
    def __init__(
            
            self,
            fluid_name,
            *,
            p_abs_Pa = None,
            T_ref = None,
            
            ):
        
        try:
            fluid_name = str( fluid_name ).upper()
        except:
            raise FluidError("Fluid: Argument 'fluid_name' must be convertible to string.")
        
        if fluid_name in [ 'WATER', 'W' ]:
            
            self._fluid_name = 'water'
            self.__init__water( p_abs_Pa, T_ref )
            
            
    def __init__water(
            
            self,
            p_abs_Pa = None,
            T_ref = None,
            
            ):
        
        if p_abs_Pa is None:
            raise FluidError("Fluid: Argument 'p_abs_Pa' must be a numeric value between 20,000 and 4,000,000.")
        if not ( p_abs_Pa >= 2e4 and p_abs_Pa <= 4e6 ):
            raise FluidError("Fluid: Argument 'p_abs_Pa' must be a numeric value between 20,000 and 4,000,000.")
        
        self._can_boil = True
        
        # Define available range and properties in the limits
        self._T_min = 1
        self._T_max = 350
        self._h_min = float( PropsSI( 'H', 'T', self._T_min + 273.15, 'P', p_abs_Pa, 'water' ) )
        self._h_max = float( PropsSI( 'H', 'T', self._T_max + 273.15, 'P', p_abs_Pa, 'water' ) )
        self._D_min = float( PropsSI( 'D', 'T', self._T_min + 273.15, 'P', p_abs_Pa, 'water' ) )
        self._D_max = float( PropsSI( 'D', 'T', self._T_max + 273.15, 'P', p_abs_Pa, 'water' ) )
        
        # Saturation conditions
        self._T_sat = float( PropsSI( 'T', 'P', p_abs_Pa, 'Q', 0.5, 'water' ) - 273.15 )
        
        self._h_sat_liq = float( PropsSI( 'H', 'P', p_abs_Pa, 'Q', 0, 'water' ) )
        self._h_sat_vap = float( PropsSI( 'H', 'P', p_abs_Pa, 'Q', 1, 'water' ) )
        self._D_sat_liq = float( PropsSI( 'D', 'P', p_abs_Pa, 'Q', 0, 'water' ) )
        self._D_sat_vap = float( PropsSI( 'D', 'P', p_abs_Pa, 'Q', 1, 'water' ) )
        self._v_sat_liq = 1/self._D_sat_liq
        self._v_sat_vap = 1/self._D_sat_vap
        
        # Reference conditions
        if T_ref is not None:
            self._ref_conditions = True
            self._cp_ref = PropsSI( 'C', 'T', T_ref + 273.15, 'P', p_abs_Pa, 'water' )
            self._D_ref = PropsSI( 'D', 'T', T_ref + 273.15, 'P', p_abs_Pa, 'water' )
            self._k_ref = PropsSI( 'conductivity', 'T', T_ref + 273.15, 'P', p_abs_Pa, 'water' )
        else:
            self._ref_conditions = False
        
        #Find temperatures near saturation that do not throw errors
        T_liq_max = self._T_sat + 273.15 - 1e-2
        while True:
            try:
                h_liq_max = PropsSI( 'H', 'P', p_abs_Pa, 'T', T_liq_max, 'water' )
                break
            except:
                T_liq_max = T_liq_max - 1e-2
                
        T_vap_min = self._T_sat + 273.15 + 1e-2
        while True:
            try:
                h_vap_min = PropsSI( 'H', 'P', p_abs_Pa, 'T', T_vap_min, 'water' )
                break
            except:
                T_vap_min = T_vap_min + 1e-2
                
        T_liq_array = np.linspace( self._T_min + 273.15, T_liq_max, 200 )
        h_liq_array = PropsSI( 'H', 'T', T_liq_array, 'P', p_abs_Pa, 'water' )
        D_liq_array = PropsSI( 'D', 'T', T_liq_array, 'P', p_abs_Pa, 'water' )
        
        self._T_to_h_liq = _define_polyfit(7, T_liq_array, h_liq_array)
        self._h_to_T_liq = _define_polyfit(7, h_liq_array, T_liq_array)
        self._T_to_D_liq = _define_polyfit(7, T_liq_array, D_liq_array)
        
        T_vap_array = np.linspace( T_vap_min, self._T_max + 273.15, 200 )
        h_vap_array = PropsSI( 'H', 'T', T_vap_array, 'P', p_abs_Pa, 'water' )
        D_vap_array = PropsSI( 'D', 'T', T_vap_array, 'P', p_abs_Pa, 'water' )
        
        self._T_to_h_vap = _define_polyfit(7, T_vap_array, h_vap_array)
        self._h_to_T_vap = _define_polyfit(7, h_vap_array, T_vap_array)
        self._T_to_D_vap = _define_polyfit(7, T_vap_array, D_vap_array)
        
    @property
    def fluid_name(self):
        return self._fluid_name
            
    @property
    def h_sat_liq(self):
        if self._can_boil:
            return self._h_sat_liq
        raise AttributeError("Boiling is not modeled for this fluid type.")
    
    @property
    def h_sat_vap(self):
        if self._can_boil:
            return self._h_sat_vap
        raise AttributeError("Boiling is not modeled for this fluid type.")
    
    @property
    def T_sat(self):
        if self._can_boil:
            return self._T_sat
        raise AttributeError("Boiling is not modeled for this fluid type.")
    
    @property
    def T_min(self):
        return self._T_min
    
    @property
    def T_max(self):
        return self._T_max
    
    @property
    def h_min(self):
        return self._h_min
        
    @property
    def h_max(self):
        return self._h_max
    
    @property
    def cp_ref(self):
        if not self._ref_conditions:
            raise FluidError("Fluid.cp_ref: Reference temperature must be provided at initialization.")
        return self._cp_ref
        
    @property
    def D_ref(self):
        if not self._ref_conditions:
            raise FluidError("Fluid.D_ref: Reference temperature must be provided at initialization.")
        return self._D_ref
        
    @property
    def k_ref(self):
        if not self._ref_conditions:
            raise FluidError("Fluid.k_ref: Reference temperature must be provided at initialization.")
        return self._k_ref
            
    def h_to_T( self, h ):
        
        if h < self._h_min:
            warnings.warn(f"Fluid.h_to_T: An enthalpy value below the minimum available ({self._h_min} J/kg) was provided. Minimum temperature value ({self._T_min} °C) is returned.")
            return self._T_min
        if h > self._h_max:
            warnings.warn(f"Fluid.h_to_T: An enthalpy value above the maximum available ({self._h_max} J/kg) was provided. Maximum temperature value ({self._T_max} °C) is returned.")
            return self._T_max
        
        if h < self._h_sat_liq:
            return float( self._h_to_T_liq( h ) - 273.15 )
        
        if h > self.h_sat_vap:
            return float( self._h_to_T_vap( h ) - 273.15 )
        
        return self._T_sat
    
    def T_to_h( self, T ):
        
        if T < self._T_min:
            warnings.warn(f"Fluid.T_to_h: A temperature value below the minimum available ({self._T_min} °C) was provided. Minimum enthalpy value ({self._h_min} J/kg) is returned.")
            return self._h_min
        if T > self._T_max:
            warnings.warn(f"Fluid.T_to_h: A temperature value above the maximum available ({self._T_max} °C) was provided. Maximum enthalpy value ({self._h_max} J/kg) is returned.")
            return self._h_max
        
        if abs( T - self._T_sat ) < 1e-8:
            raise ValueError(f"Fluid.T_to_h: Temperature provided ({T} °C) is less than 1e-8 °C from saturation temperature ({self._Tsat} °C).")
        
        T_K = T + 273.15
        
        if T < self._T_sat:
            return float( self._T_to_h_liq( T_K ) )
        
        else:
            return float( self._T_to_h_vap( T_K ) )
        
    def h_to_Q( self, h ):
        
        if h <= self._h_sat_liq:
            return 0
        if h >= self._h_sat_vap:
            return 1
        return float( ( h - self._h_sat_liq )/( self._h_sat_vap - self._h_sat_liq ) )
    
    def h_to_D( self, h ):
        
        if h < self._h_min:
            warnings.warn(f"Fluid.h_to_T: An enthalpy value below the minimum available ({self._h_min} J/kg) was provided. Density for minimum enthalpy available is returned ({self._D_min} kg/m3).")
            return self._D_min
        if h > self._h_max:
            warnings.warn(f"Fluid.h_to_T: An enthalpy value above the maximum available ({self._h_max} J/kg) was provided. Density for maximum enthalpy available is returned ({self._D_max} kg/m3).")
            return self._D_max
        
        if h >= self._h_sat_liq and h <= self._h_sat_vap:
            x = self.h_to_Q( h )
            v_mixture = ( 1 - x )*self._v_sat_liq + x*self._v_sat_vap
            return 1/v_mixture
        
        T_C = self.h_to_T( h )
        
        if T_C < self._T_sat:
            return float( self._T_to_D_liq( T_C + 273.15 ) )
        else:
            return float( self._T_to_D_vap( T_C + 273.15 ) )
        
    def state( self, **kwargs ):
        
        return FluidState(self, **kwargs)