# -*- coding: utf-8 -*-
"""
Created on Thu Oct 15 10:54:10 2026

@author: Adrian Riebel Brummer
"""

from CoolProp.CoolProp import PropsSI
import numpy as np
import warnings

warnings.simplefilter('ignore', np.exceptions.RankWarning)

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
        "Get sercpy.fluids.Fluid object from which the FluidState instance was constructed."
        return self._fluid
        
    @property
    def T(self):
        "Get temperature in °C."
        if not hasattr(self, '_T'):
            self._T = self._fluid.h_to_T( self._h)
            
        return self._T
    
    @property
    def h(self):
        "Get enthalpy in J/kg."
        if not hasattr( self, '_h' ):
            self._h = self._fluid.T_to_h( self._T )
        
        return self._h
    
    @property
    def H(self):
        "Get enthalpy in J/kg."
        return self.h
    
    @property
    def D(self):
        "Get density in kg/m3."
        if not hasattr( self, '_D' ):
            self._D = self._fluid.h_to_D( self.h )
            
        return self._D
    
    @property
    def density(self):
        "Get density in kg/m3."
        return self.D
    
    @property
    def d(self):
        "Get density in kg/m3."
        return self.D
    
    @property
    def Q(self):
        "Get mixture quality (i.e. vapor fraction in the range 0 - 1)."
        if not hasattr(self, "_Q"):
            self._Q = self._fluid.h_to_Q( self.h )
                
        return self._Q
    
    @property
    def quality(self):
        "Get mixture quality (i.e. vapor fraction in the range 0 - 1)."
        return self.Q
    
def _extrapolate_missing_values( x_array: np.array, y_values: list ) -> np.array:
    
    y_values = np.array( y_values )
    
    if len( y_values ) == len( x_array ):
        return y_values
    
    index_1 = len( y_values ) - 2
    index_2 = len( y_values ) - 1
    
    dy_dx = ( y_values[ index_2 ] - y_values[ index_1 ] ) / ( x_array[ index_2 ] - x_array[ index_1 ] )
    
    y_values_new = []
    for index in range( len( y_values ), len( x_array ) ):
        y_values_new.append( y_values[ index_2 ] + dy_dx*( x_array[ index ] - x_array[ index_2 ] ) )
    
    y_values = np.concatenate( ( y_values, np.array( y_values_new ) ), )
    
    assert len( y_values ) == len( x_array )
    
    return y_values
    
def _define_polyfit( max_degree, x_axis, y_axis ):
    
    for degree in range( 1, max_degree + 1 ):
        poly_func = np.poly1d( np.polyfit( x_axis, y_axis, degree ) )
        estimated_y_axis = [ poly_func( x ) for x in x_axis ]
        error = float( np.max( np.abs( np.array( estimated_y_axis ) - np.array( y_axis ) ) ) )
        if degree == 1:
            best_result = error
            best_poly_func = poly_func
            continue
        if error < best_result:
            best_result = error
            best_poly_func = poly_func 
    return best_poly_func

# Database of thermal oils
# Key: Simplified name (upper case only, no spaces, no hyphens, etc)
# First string in tuple: Name of the substance in CoolProp
# Second string in the tuple: Official high-level (user-level) name
_thermal_oils = {
    
    'THERMINOL55': ('PGLT', 'Therminol 55'),
    'THERMINOL66': ('T66', 'Therminol 66'),
    'THERMINOL72': ('T72', 'Therminol 72'),
    'THERMINOLVP1': ('TVP1', 'Therminol VP-1'),
    'THERMINOLD12': ('TD12', 'Therminol D-12'),
    'DOWTHERMA': ('TVP1', 'Dowtherm A'), # Therminol VP-1
    'DOWTHERMJ': ('DowJ', 'Dowtherm J'),
    'DOWTHERMQ': ('DowQ', 'Dowtherm Q'),
    'DYNALENEHC10': ('HC10', 'Dynalene HC10'),
    'DYNALENEHC20': ('HC20', 'Dynalene HC20'),
    'DYNALENEHC30': ('HC30', 'Dynalene HC30'),
    'DYNALENEHC40': ('HC40', 'Dynalene HC40'),
    'DYNALENEHC50': ('HC50', 'Dynalene HC50'),
    'DYNALENESF': ('DSF', 'Dynalene SF'),
    'PARATHERMCR': ('PCR', 'Paratherm CR'),
    'PARATHERMGLT': ('PGLT', 'Paratherm GLT'), #Therminol 55
    'PARATHERMHE': ('PHE', 'Paratherm HE'),
    'PARATHERMHR': ('PHR', 'Paratherm HR'),
    'PARATHERMLR': ('PLR', 'Paratherm LR'),
    'PARATHERMMR': ('PMR', 'Paratherm MR'),
    'PARATHERMNF': ('PNF2', 'Paratherm NF'),
    'SYLTHERM800': ('S800', 'Syltherm 800'),
    'SYLTHERMXLT': ('XLT2', 'Syltherm XLT'),
    'TEXATHERM22': ('TX22', 'Texatherm 22'),
    
    }
    
class Fluid:
    """
    Class that stores the properties of a heat transfer fluid, at a fixed pressure.
    
    The class can convert specific enthalpy to temperature, and it most cases, also viceversa (unless the saturation temperature is provided as argument).
    
    In the case of water, the instances of this class also store the saturation temperature and the vaporization enthalpy, and the properties of vapor up to 350 °C.
    
    Class instances also store the density as a function of temperature/enthalpy.

    Parameters
    ----------
    fluid_name : str
        String defining the type of substance. For pure water, valid names are `"w"` and `"water"`. See the :doc:`document on fluid naming <fluid_naming>` for other options such as water-glycol mixtures and other commercial heat transfer fluids.
    
    p_abs_Pa : float, optional
        Absolute pressure in Pascal. Only needed for water. Valid range: 20,000 to 4,000,000.
    
    T_ref : float, optional
        Temperature at which to compute the reference density, thermal conductivity, and specific heat capacity.
        This is needed, in particular, for fluids that will be stored in storage tanks, for whose calculations constant fluid properties are assumed.
    
    mixture_type : str, optional
        A string specifying whether the glycol percentage introduced for a water-glycol mixture defines the mass-based- or the volume-based percentage in the mixture.
        Accepted values for volume-based percentages are `"v"`, `"v/v"`, `"volume"`, and `"volume-based"`.
        Accepted values for mass-based percentages are `"m"`, `"m/m"`, `"mass"`, and `"mass-based"`.
        If not specified, this parameter defaults to `"m"`.
        **Warning:** For volumetric percentage values close the the maximum allowed of 60%, the mass-based percentage, which must be computed internally, slightly surpasses 60%. Therefore, in these cases, the mass-based percentage value is approximated to 60%, in order for the model to work.
        In the worst-case scenario of ethylene glycol with a volumetric percentage of 60%, this correction amounts to changing the mass-based percentage from 62.58% to 60%. A warning is thrown when this correction is carried out.
    
    Attributes
    ----------
    fluid_name : str
        Name identifying the fluid.
    
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
    
    glycol_percentage : int
        Only for water-glycol mixtures. Glycol percentage of the mixture.
        
    glycol_type : str
        Only for water-glycol mixtures. Either 'Ethylene Glycol' or 'Propylene Glycol'. It is actually an alias for `fluid_name`, only when valid.
    
    mixture_type : str
        Only for water-glycol mixtures. Either 'mass-based' or 'volume-based'.
        
        
    Methods
    -------
    h_to_T( h )
        Convert specific enthalpy (J/kg) to temperature (°C). Accepts both single numeric values and array-like objects as arguments. Returns either float or np.array.
    
    T_to_h( T )
        Convert temperature (°C) to specific enthalpy (J/kg). Fails when the temperature provided is too close to saturation (tolerance: 1e-8 °C). Accepts both single numeric values and array-like objects as arguments. Returns either float or np.array.
    
    h_to_Q( h )
        Get mixture quality (float in the range 0 - 1) from specific enthalpy (J/kg). Mixture quality is defined as the vapor fraction in a liquid-vapor saturated mixture. Outside saturation, this method returns 0 for liquids and 1 for gases. Accepts both single numeric values and array-like objects as arguments. Returns either float or np.array.
    
    Q_to_h( Q )
        Convert mixture quality to average specific enthalpy (J/kg). Mixture quality is defined as the vapor fraction in a liquid-vapor saturated mixture, and must be a value in the range 0 - 1. Accepts both single numeric values and array-like objects as arguments. Returns either float or np.array.
    
    T_to_D( T )
        Get density (kg/m3) from temperature (°C). Fails when the temperature provided is too close to saturation (tolerance: 1e-8 °C). Accepts both single numeric values and array-like objects as arguments. Returns either float or np.array.
    
    h_to_D( h )
        Get density (kg/m3) from specific enthalpy (J/kg). Accepts both single numeric values and array-like objects as arguments. Returns either float or np.array.
    
    state( **kwargs )
        This method returns a `sercpy.fluids.FluidState` instance, defined from the `Fluid` instance and `kwargs`.
    
    """
    
    
    def __init__(
            
            self,
            fluid_name,
            *,
            p_abs_Pa = None,
            T_ref = None,
            mixture_type = 'm',
            
            ):
        # ' -_.,:;%'
        try:
            fluid_name_corrected = str( fluid_name ).upper().translate(str.maketrans( '', '', ' -_%' ) )
            print( fluid_name_corrected )
        except:
            raise FluidError("Fluid: Argument 'fluid_name' must be convertible to string.")
        
        if fluid_name_corrected in [ 'WATER', 'W' ]:
            
            self._fluid_name = 'Water'
            self.__init__water( p_abs_Pa, T_ref )
            
        elif fluid_name_corrected in _thermal_oils:
            
            self._fluid_name = _thermal_oils[ fluid_name_corrected ][ 1 ]
            self._CP_name = _thermal_oils[ fluid_name_corrected ][ 0 ]
            self.__init__oil( T_ref )
            
        elif any( [ fluid_name_corrected.startswith( word ) for word in [
                
                'EG',
                'ETHYLENEGLYCOL',
                'PG',
                'PROPYLENEGLYCOL',
                
                ] ] ):
            
            glycol_name = [
                
                'EG',
                'ETHYLENEGLYCOL',
                'PG',
                'PROPYLENEGLYCOL', ][ [ fluid_name_corrected.startswith( word ) for word in [
                    
                    'EG',
                    'ETHYLENEGLYCOL',
                    'PG',
                    'PROPYLENEGLYCOL', ] ].index( True ) ]
                    
            try:
                glycol_percentage = int( fluid_name_corrected[ len( glycol_name ) : ] )
            except:
                raise FluidError( "Glycol percentage could not be extracted from fluid name." )
            
            if glycol_name in [ 'EG', 'ETHYLENEGLYCOL' ]:
                glycol_type = "EG"
            elif glycol_name in [ 'PG', 'PROPYLENEGLYCOL' ]:
                glycol_type = "PG"
            else:
                raise FluidError( "Unexpected error." )
            self.__init__glycol( glycol_type = glycol_type, glycol_percentage = glycol_percentage, mixture_type = mixture_type, T_ref = T_ref )
            
        else:
            
            raise ValueError(f"Fluid name not recognized: {fluid_name}")
    
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
            if not ( T_ref > self._T_min and T_ref < self._T_max ):
                raise FluidError(f"Fluid: T_ref must be larger than T_min: {self._T_min}, and smaller than T_max: {self._T_max}.")
            self._ref_conditions = True
            self._cp_ref = float( PropsSI( 'C', 'T', T_ref + 273.15, 'P', p_abs_Pa, 'water' ) )
            self._D_ref = float( PropsSI( 'D', 'T', T_ref + 273.15, 'P', p_abs_Pa, 'water' ) )
            self._k_ref = float( PropsSI( 'conductivity', 'T', T_ref + 273.15, 'P', p_abs_Pa, 'water' ) )
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
        
    def __init__oil( self, T_ref = None, ):
        
        self._can_boil = False
        self._Q = 0
        fluid_name = 'INCOMP::' + self._CP_name
        p_abs_Pa = 2000000
        ##
        
        # Define available range and properties in the limits
        self._T_min = PropsSI( 'Tmin', fluid_name ) - 273.15
        self._T_max = PropsSI( 'Tmax', fluid_name ) - 273.15
        
        self._h_min = float( PropsSI( 'H', 'T', self._T_min + 273.15, 'P', p_abs_Pa, fluid_name ) )
        self._h_max = float( PropsSI( 'H', 'T', self._T_max + 273.15, 'P', p_abs_Pa, fluid_name ) )
        self._D_min = float( PropsSI( 'D', 'T', self._T_min + 273.15, 'P', p_abs_Pa, fluid_name ) )
        self._D_max = float( PropsSI( 'D', 'T', self._T_max + 273.15, 'P', p_abs_Pa, fluid_name ) )
        
        # Reference conditions
        if T_ref is not None:
            if not ( T_ref > self._T_min and T_ref < self._T_max ):
                raise FluidError(f"Fluid: T_ref must be larger than T_min: {self._T_min}, and smaller than T_max: {self._T_max}.")
            self._ref_conditions = True
            self._cp_ref = float( PropsSI( 'C', 'T', T_ref + 273.15, 'P', p_abs_Pa, fluid_name ) )
            self._D_ref = float( PropsSI( 'D', 'T', T_ref + 273.15, 'P', p_abs_Pa, fluid_name ) )
            self._k_ref = float( PropsSI( 'conductivity', 'T', T_ref + 273.15, 'P', p_abs_Pa, fluid_name ) )
        else:
            self._ref_conditions = False
                
        T_liq_array = np.linspace( self._T_min + 273.15, self._T_max + 273.15, 200 )
        h_liq_array = PropsSI( 'H', 'T', T_liq_array, 'P', p_abs_Pa, fluid_name )
        D_liq_array = PropsSI( 'D', 'T', T_liq_array, 'P', p_abs_Pa, fluid_name )
        
        self._T_to_h_poly = _define_polyfit(7, T_liq_array, h_liq_array)
        self._h_to_T_poly = _define_polyfit(7, h_liq_array, T_liq_array)
        self._T_to_D_poly = _define_polyfit(7, T_liq_array, D_liq_array)
        
    def __init__glycol( self, glycol_type, glycol_percentage, mixture_type, T_ref = None ):
        
        if not glycol_type in [ "EG", "PG" ]:
            raise FluidError("Fluid: Glyicol type not known.")
        
        try:
            mixture_type = str( mixture_type )
        except:
            raise FluidError("Fluid: Argument 'mixture_type' must be a string.")
        
        mixture_type_corrected = str( mixture_type ).upper().translate(str.maketrans( '', '', ' -_.,:;%' ))
        
        if not mixture_type_corrected in [ 'M', 'M/M', 'MASS', 'MASSBASED', 'V', 'V/V', 'VOLUME', 'VOLUMEBASED' ]:
            raise FluidError("Fluid: Argument 'mixture_type' is not valid.")
            
        if mixture_type_corrected in [ 'M', 'M/M', 'MASS', 'MASSBASED', ]:
            self._mixture_type = 'mass-based'
        else:
            self._mixture_type = 'volume-based'
        
        if glycol_percentage > 60:
            raise FluidError("Fluid: Glycol percentage must be <= 60.")
        elif glycol_percentage <= 0:
            raise FluidError("Fluid: Glycol percentage must be positive.")
            
        self._glycol_percentage = glycol_percentage
        
        if self._mixture_type == 'mass-based':
            mm_vv = 'm/m'
        else:
            mm_vv = 'v/v'
        
        if glycol_type == "EG":
            self._fluid_name = f"Ethylene Glycol { self._glycol_percentage }% {mm_vv}"
        if glycol_type == "PG":
            self._fluid_name = f"Propylene Glycol { self._glycol_percentage }% {mm_vv}"
        
        if self._mixture_type == 'volume-based':
            # Mass fraction is computed at 20°C
            if glycol_type == "EG":
                glycol_density = 1113
            else:
                glycol_density = 1036
            water_density = 998.3
            glycol_volume_fraction = glycol_percentage/100
            water_volume_fraction = 1 - glycol_volume_fraction
            
            glycol_mass_fracion = glycol_density*glycol_volume_fraction/( glycol_density*glycol_volume_fraction + water_density*water_volume_fraction )
            
        else:
            glycol_mass_fracion = glycol_percentage/100
        
        if self._mixture_type == 'volume-based' and glycol_mass_fracion > 0.6:
            warnings.warn(f"Fluid: Glycol mass fraction computed from volumetric fraction is {np.round( glycol_mass_fracion, 4 )}. The value will be approximated to 0.6 since the model does not support values larger than this.")
            glycol_mass_fracion = min( [ glycol_mass_fracion, 0.6 ] )
            
        fraction_str = str( float( np.round( glycol_mass_fracion, 2 ) ) )
            
        self._T_min = 1
        self._T_max = 120
        
        self._can_boil = False
        self._Q = 0
        fluid_name = 'INCOMP::M' + glycol_type + '[' + fraction_str + ']'
        p_abs_Pa = 300000
        
        T_liq_array = np.linspace( self._T_min + 273.15, self._T_max + 273.15, 200 )
        
        h_liq_array = []
        D_liq_array = []
        cp_liq_array = []
        k_liq_array = []
        for T in T_liq_array:
            try:
                h = PropsSI( 'H', 'T', T, 'P', p_abs_Pa, fluid_name )
                D = PropsSI( 'D', 'T', T, 'P', p_abs_Pa, fluid_name )
                cp = PropsSI( 'C', 'T', T, 'P', p_abs_Pa, fluid_name )
                k = PropsSI( 'CONDUCTIVITY', 'T', T, 'P', p_abs_Pa, fluid_name )
                h_liq_array.append( h )
                D_liq_array.append( D )
                cp_liq_array.append( cp )
                k_liq_array.append( k )
            except:
                break
        assert len( h_liq_array ) > 0 and len( D_liq_array ) > 0
        h_liq_array = _extrapolate_missing_values(T_liq_array, h_liq_array)
        D_liq_array = _extrapolate_missing_values(T_liq_array, D_liq_array)
        cp_liq_array = _extrapolate_missing_values(T_liq_array, cp_liq_array)
        k_liq_array = _extrapolate_missing_values(T_liq_array, k_liq_array)
        
        self._h_min = h_liq_array[0]
        self._h_max = h_liq_array[-1]
        self._D_min = D_liq_array[0]
        self._D_max = D_liq_array[-1]
        
        self._T_to_h_poly = _define_polyfit(7, T_liq_array, h_liq_array)
        self._h_to_T_poly = _define_polyfit(7, h_liq_array, T_liq_array)
        self._T_to_D_poly = _define_polyfit(7, T_liq_array, D_liq_array)
        
        T_to_cp_poly = _define_polyfit(7, T_liq_array, cp_liq_array)
        T_to_k_poly = _define_polyfit(7, T_liq_array, k_liq_array)
        
        if T_ref is not None:
            if not ( T_ref > self._T_min and T_ref < self._T_max ):
                raise FluidError(f"Fluid: T_ref must be larger than T_min: {self._T_min}, and smaller than T_max: {self._T_max}.")
            self._ref_conditions = True
            self._cp_ref = float( T_to_cp_poly( T_ref + 273.15 ) )
            self._D_ref = float( self._T_to_D_poly( T_ref + 273.15 ) )
            self._k_ref = float( T_to_k_poly( T_ref + 273.15 ) )
        else:
            self._ref_conditions = False
    
    @property
    def fluid_name(self):
        "Get name of the substance (str)."
        return self._fluid_name
            
    @property
    def h_sat_liq(self):
        "Get specific enthalpy of liquid at saturation, in J/kg."
        if self._can_boil:
            return self._h_sat_liq
        raise AttributeError("Boiling is not modeled for this fluid type.")
    
    @property
    def h_sat_vap(self):
        "Get specific enthalpy of vapor at saturation, in J/kg."
        if self._can_boil:
            return self._h_sat_vap
        raise AttributeError("Boiling is not modeled for this fluid type.")
    
    @property
    def T_sat(self):
        "Get saturation temperature, in °C."
        if self._can_boil:
            return self._T_sat
        raise AttributeError("Boiling is not modeled for this fluid type.")
    
    @property
    def T_min(self):
        "Get minimum temperature available for the fluid's model, in °C."
        return self._T_min
    
    @property
    def T_max(self):
        "Get maximum temperature available for the fluid's model, in °C."
        return self._T_max
    
    @property
    def h_min(self):
        "Get minimum specific enthalpy available for the fluid's model, in J/kg."
        return self._h_min
        
    @property
    def h_max(self):
        "Get maximum specific enthalpy available for the fluid's model, in J/kg."
        return self._h_max
    
    @property
    def cp_ref(self):
        "Get specific heat capacity at the reference temperature, in J/kg °C."
        if not self._ref_conditions:
            raise FluidError("Fluid.cp_ref: Reference temperature must be provided at initialization.")
        return self._cp_ref
        
    @property
    def D_ref(self):
        "Get density at the reference temperature, in J/kg °C."
        if not self._ref_conditions:
            raise FluidError("Fluid.D_ref: Reference temperature must be provided at initialization.")
        return self._D_ref
        
    @property
    def k_ref(self):
        "Get thermal conductivity at the reference temperature, in J/kg °C."
        if not self._ref_conditions:
            raise FluidError("Fluid.k_ref: Reference temperature must be provided at initialization.")
        return self._k_ref
    
    @property
    def glycol_percentage(self):
        "Get glycol percentage of a water-glycol mixture."
        if self.fluid_name.startswith( "Ethylene Glycol" ) or self.fluid_name.startswith( "Propylene Glycol" ):
            return self._glycol_percentage
        else:
            raise FluidError("Fluid is not a water-glycol mixture.")
    
    @property
    def glycol_type(self):
        "Get glycol type of a water-glycol mixture (either Ethylene Glycol or Propylene Glycol)."
        if self.fluid_name in [ "Ethylene Glycol", "Propylene Glycol" ]:
            return self.fluid_name
        else:
            raise FluidError("Fluid is not a water-glycol mixture.")
    
    @property
    def mixture_type(self):
        "Get mixture type of a water-glycol mixture (either 'volume-based' or 'mass-based')."
        if self.fluid_name in [ "Ethylene Glycol", "Propylene Glycol" ]:
            return self._mixture_type
        else:
            raise FluidError("Fluid is not a water-glycol mixture.")
    
    def _process_array( self, method, array ):
        """
        Private method that changes the functionality of other conversion methods (such as h_to_T, T_to_h, etc) in order to process arrays of data instead of single numbers.

        Parameters
        ----------
        method : Fluid method
            Method/function that will process the elements of the array.
        array : array-like
            Array of values to process.

        Returns
        -------
        np.array
            Array of converted values.

        """
        return np.array( [ method( v ) for v in array ] )
            
    def h_to_T( self, h ):
        """
        Convert specific enthalpy to temperature.

        Parameters
        ----------
        h : float or array-like
            Specific enthalpy value(s) in J/kg.

        Raises
        ------
        TypeError
            If the argument cannot be interpreted as a number nor as a list.

        Returns
        -------
        float or np.array
            Temperature value(s) in °C.

        """
        
        try:
            h = float( h )
        except TypeError:
            try:
                h = list( h )
                return self._process_array(self.h_to_T, h)
            except TypeError:
                raise TypeError( "Fluid.h_to_T: Value 'h' must be numeric or array-like." )
        
        if h < self._h_min:
            if abs( h - self.h_min ) > 0.005*(self._h_max - self._h_min):
                warnings.warn(f"Fluid.h_to_T: An enthalpy value below the minimum available ({self._h_min} J/kg) was provided. Minimum temperature value ({self._T_min} °C) is returned.")
            return self._T_min
        if h > self._h_max:
            if abs( h - self._h_max ) > 0.005*(self._h_max - self._h_min):
                warnings.warn(f"Fluid.h_to_T: An enthalpy value above the maximum available ({self._h_max} J/kg) was provided. Maximum temperature value ({self._T_max} °C) is returned.")
            return self._T_max
        
        if self._can_boil:
        
            if h < self._h_sat_liq:
                return float( self._h_to_T_liq( h ) - 273.15 )
            
            if h > self.h_sat_vap:
                return float( self._h_to_T_vap( h ) - 273.15 )
            
            return self._T_sat
        
        return float( self._h_to_T_poly( h ) - 273.15 )
    
    def T_to_h( self, T ):
        """
        Convert temperature to specific enthalpy.
        
        Parameters
        ----------
        T : float or array-like
            Temperature value(s) in °C.
        
        Raises
        ------
        TypeError
            If the argument cannot be interpreted as a number nor as a list.
        
        Returns
        -------
        float or np.array
            Specific enthalpy value(s) in J/kg.
        
        """
        
        try:
            T = float( T )
        except TypeError:
            try:
                T = list( T )
                return self._process_array(self.T_to_h, T)
            except TypeError:
                raise TypeError( "Fluid.T_to_h: Value 'T' must be numeric or array-like." )
        
        if T < self._T_min:
            if abs( T - self._T_min ) > 0.005*( self._T_max - self._T_min ):
                warnings.warn(f"Fluid.T_to_h: A temperature value below the minimum available ({self._T_min} °C) was provided. Minimum enthalpy value ({self._h_min} J/kg) is returned.")
            return self._h_min
        if T > self._T_max:
            if abs( T - self._T_max ) > 0.005*( self._T_max - self._T_min ):
                warnings.warn(f"Fluid.T_to_h: A temperature value above the maximum available ({self._T_max} °C) was provided. Maximum enthalpy value ({self._h_max} J/kg) is returned.")
            return self._h_max
        
        T_K = T + 273.15
        
        if self._can_boil:
        
            if abs( T - self._T_sat ) < 1e-8:
                raise ValueError(f"Fluid.T_to_h: Temperature provided ({T} °C) is less than 1e-8 °C from saturation temperature ({self._Tsat} °C).")
            
            if T < self._T_sat:
                return float( self._T_to_h_liq( T_K ) )
            
            else:
                return float( self._T_to_h_vap( T_K ) )
        
        return float( self._T_to_h_poly( T_K ) )
        
    def h_to_Q( self, h ):
        """
        Convert specific enthalpy to quality, i.e., the vapor fraction in a mixture. This value is represented as a number in the range 0 - 1. For liquids under saturation temperature, the method returns 0. For gases over saturation temeprature, the method returns 1.

        Parameters
        ----------
        h : float or array-like
            Specific enthalpy value(s) in J/kg.

        Raises
        ------
        TypeError
            If the argument cannot be interpreted as a number nor as a list.

        Returns
        -------
        float or np.array
            Value(s) in the range 0 - 1 representing the vapor fraction of the mixture.

        """
        
        try:
            h = float( h )
        except TypeError:
            try:
                h = list( h )
                return self._process_array(self.h_to_Q, h)
            except TypeError:
                raise TypeError( "Fluid.h_to_Q: Value 'h' must be numeric or array-like." )
                
        if not self._can_boil:
            return self._Q
        
        if h <= self._h_sat_liq:
            return 0
        if h >= self._h_sat_vap:
            return 1
        return float( ( h - self._h_sat_liq )/( self._h_sat_vap - self._h_sat_liq ) )
    
    def Q_to_h( self, Q ):
        """
        Convert mixture quality to average specific enthalpy (J/kg).
        
        Mixture quality is defined as the fraction of vapor in a saturated liquid-vapor mixture.
        
        Parameters
        ----------
        Q : float or array-like
            Mixture quality value(s). Valid range: 0 to 1.
        
        Raises
        ------
        FluidError
            If the fluid model does not support boiling.
        TypeError
            If the argument cannot be interpreted as a number nor as a list..
        ValueError
            If the argument is not within the expected range (0 - 1).
        
        Returns
        -------
        float or np.array
            Average specific enthalpy of the mixture (single number or array) in J/kg.
        
        """
        
        if not self._can_boil:
            raise FluidError("Fluid: Model for {self._fluid_name} does support boiling.")
        
        try:
            Q = float( Q )
        except TypeError:
            try:
                Q = list( Q )
                return self._process_array(self.Q_to_h, Q)
            except TypeError:
                raise TypeError( "Fluid.Q_to_h: Value 'Q' must be numeric or array-like." )
                
        if not (Q >= 0 and Q <= 1 ):
            raise ValueError("Fluid.Q_to_h: Value of 'Q' must be in the range 0 - 1.")
        
        if Q == 0:
            return self._h_sat_liq
        elif Q == 1:
            return self._h_sat_vap
        return self._h_sat_vap*Q + self._h_sat_liq*( 1 - Q )
            
        
    def T_to_D( self, T ):
        """
        Convert temperature to density.

        Parameters
        ----------
        T : float or array-like
            Temperature value(s) in °C.

        Raises
        ------
        TypeError
            If the argument cannot be interpreted as a number nor as a list.
        ValueError
            If the temperature introduced is too close to saturation temperature (tolerance: 1e-8 °C).

        Returns
        -------
        float or np.array
            Density of the fluid (single number or array) in kg/m3.

        """
        
        try:
            T = float( T )
        except TypeError:
            try:
                T = list( T )
                return self._process_array(self.T_to_D, T)
            except TypeError:
                raise TypeError( "Fluid.T_to_D: Value 'T' must be numeric or array-like." )
                
        if self._can_boil and abs( T - self._T_sat ) < 1e-8:
            raise ValueError(f"Fluid.T_to_D: Temperature provided ({T} °C) is less than 1e-8 °C from saturation temperature ({self._Tsat} °C).")
        
        if T < self._T_min:
            if abs( T - self.T_min ) > 0.005*(self._T_max - self._T_min):
                warnings.warn(f"Fluid.T_to_D: A temperature value below the minimum available ({self._T_min} J/kg) was provided. Density for minimum temperature available is returned ({self._D_min} kg/m3).")
            return self._D_min
        if T > self._T_max:
            if abs( T - self._T_max ) > 0.005*(self._T_max - self._T_min):
                warnings.warn(f"Fluid.T_to_D: A temperature value above the maximum available ({self._T_max} J/kg) was provided. Density for maximum temperature available is returned ({self._D_max} kg/m3).")
            return self._D_max
        
        if self._can_boil:
            
            if T < self._T_sat:
                return float( self._T_to_D_liq( T + 273.15 ) )
            else:
                return float( self._T_to_D_vap( T + 273.15 ) )
            
        return float( self._T_to_D_poly( T + 273.15 ) )
    
    def h_to_D( self, h ):
        """
        Convert specific enthalpy to density.

        Parameters
        ----------
        h : float or array-like
            Specific enthalpy value(s) in J/kg.

        Raises
        ------
        TypeError
            If the argument cannot be interpreted as a number nor as a list.

        Returns
        -------
        float or np.array
            Density of the fluid (single number or array) in kg/m3.

        """
        
        try:
            h = float( h )
        except TypeError:
            try:
                h = list( h )
                return self._process_array(self.h_to_D, h)
            except TypeError:
                raise TypeError( "Fluid.h_to_D: Value 'h' must be numeric or array-like." )
        
        if h < self._h_min:
            if abs( h - self.h_min ) > 0.005*(self._h_max - self._h_min):
                warnings.warn(f"Fluid.h_to_D: An enthalpy value below the minimum available ({self._h_min} J/kg) was provided. Density for minimum enthalpy available is returned ({self._D_min} kg/m3).")
            return self._D_min
        if h > self._h_max:
            if abs( h - self._h_max ) > 0.005*(self._h_max - self._h_min):
                warnings.warn(f"Fluid.h_to_D: An enthalpy value above the maximum available ({self._h_max} J/kg) was provided. Density for maximum enthalpy available is returned ({self._D_max} kg/m3).")
            return self._D_max
        
        T_C = self.h_to_T( h )
        
        if self._can_boil:
        
            if h >= self._h_sat_liq and h <= self._h_sat_vap:
                x = self.h_to_Q( h )
                v_mixture = ( 1 - x )*self._v_sat_liq + x*self._v_sat_vap
                return 1/v_mixture
            
            if T_C < self._T_sat:
                return float( self._T_to_D_liq( T_C + 273.15 ) )
            else:
                return float( self._T_to_D_vap( T_C + 273.15 ) )
            
        return float( self._T_to_D_poly( T_C + 273.15 ) )
        
    def state( self, **kwargs ):
        """
        Obtain a `sercpy.fluid.FluidState` instance from a temperature or enthalpy value.

        Parameters
        ----------
        **kwargs : float
            Accepted keyword arguments are `T`, `h`, `H`. The first argument must be provided when state is being defined from temperature. Either of the two latter arguments can be provided to define the state from specific enthalpy. One and only one of these three arguments must be provided.

        Returns
        -------
        sercpy.fluid.FluidState instance

        """
        
        return FluidState(self, **kwargs)