# -*- coding: utf-8 -*-
"""
Created on Thu Sep 24 09:42:44 2026

@author: Adrian Riebel Brummer
"""

from typing import Optional
import numpy as np
from .fluids import Fluid
from .devices import Device, Outlet
import warnings
from math import log, exp
from scipy.interpolate import RegularGridInterpolator
from scipy.integrate import quad, nquad
from pvlib.irradiance import perez, get_extra_radiation
from pvlib.atmosphere import get_relative_airmass

def _dblquad(func, a, b, gfun, hfun, args=()):
    """Modified version of dblquad by scipy (scipy.integrate.dblquad). URL: https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.dblquad.html
    
    LICENSE
    -------
    
    Copyright © 2001, 2002 Enthought, Inc.
    All rights reserved.
    
    Copyright © 2003-2019 SciPy Developers.
    All rights reserved.
    
    Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:
    
    - Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
    
    - Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
    
    - Neither the name of Enthought nor the names of the SciPy Developers may be used to endorse or promote products derived from this software without specific prior written permission.
    
    THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS “AS IS” AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
    """
    def temp_ranges(*args):
        return [gfun(args[0]) if callable(gfun) else gfun,
                hfun(args[0]) if callable(hfun) else hfun]
    return nquad(func, [temp_ranges, [a, b]], args=args,
                  opts={"epsabs": 1e-3, "limit": 200, "epsrel": 1e-3})[0]

collector_allowed_arguments = [
    
    "model_name",
    "area",
    "length",
    "width",
    "n0",
    "a1",
    "a2",
    "IAM",
    "test_flowrate_per_m2",
    "test_fluid",
    
    ]

class NonConvertibleToArray(Exception):
    pass

def _to_array( array_like_or_number ):
    """
    Function that converts scalar numbers and lists to 1-dimensional numpy arrays.

    Parameters
    ----------
    array_like_or_number : float or array-like
        Value to convert.

    Returns
    -------
    array : np.array
        Converted value.

    """
    
    try:
        array_like_or_number_float = float( array_like_or_number )
        array = np.array([ array_like_or_number_float ])
    except:
        try:
            array = np.array( array_like_or_number )
            assert len( array ) >= 1
        except:
            raise NonConvertibleToArray("_to_array: 'array_like_or_number' could not be interpreted as a number nor as an array.")
    if array.ndim > 1:
        shape = array.shape
        if sum([ dim > 1 for dim in shape ]) > 1:
            raise ValueError("The resulting array has more than one dimension larger than 1.")
        index_len = [ dim > 1 for dim in shape ].index( True )
        len_array = shape[ index_len ]
        array = np.reshape( array, shape = ( len_array, ) )
    return array

class SolarCollector:
    r"""
    Class that models the performance of an individual solar collector.
    
    The collector's efficiency is computed with the formula:
    
    .. math::
        
       \eta = \eta_0 \; K \left( \, \theta, \, \theta_l , \, \theta_t \, \right )-a_1 \frac{T_{in} - T_{amb}}{G} - a_2 \frac{ \left ( T_{in} - T_{amb} \right ) ^2 }{G}
       
    where:
    
        - :math:`\eta_0` the nominal efficiency of the collector.
        - :math:`K( \, \theta, \, \theta_l , \, \theta_t \, )` is the IAM (Incidence angle modifier) correction factor.
        - :math:`\theta` is the incidence angle, and :math:`\theta_l` and :math:`\theta_t` are its longitudinal and transversal components, respectively.
        - :math:`a_1` and :math:`a_2` are the linear and the quadratic heat loss coefficiencts of the collector, respectively.
        - :math:`T_{in}` is the temperature with which the heat transfer fluid enters the solar collector.
        - :math:`T_{amb}` is the temperature of the environment surroinding the collector.
        - :math:`G` is the irradiance on the collector's plane.
          
    On the other hand, the efficiency :math:`\eta` is defined as:
        
    .. math::
        
       \eta = \frac{ \dot{Q} }{A \, G}
      
    where:
        
        - :math:`\dot{Q}` is the thermal power produced by the collector.
        - :math:`A` is the area of the collector.
    
    Moreover, the efficiency is corrected considering the flowrate that the collector is operating with. See :meth:`SolarCollector.compute_flowrate_correction_factor` for more information.
    
    Parameters
    ----------
    model_name : str, optional
        Name to identify the brand and model of the collector on which the model is based. Its only purpose is to be retrieved as an attribute in the future for convenience of the user.
    
    area : float, optional
        Area of the collector (m2). It can be the gross area or the aperture area. It has to be the area for which the efficiency parameters `n0`, `a1`, and `a2` have been defined. If not provided, it can be computed from `length` and `width`.
    
    length : float, optional
        Gross length of the collector (m). It is by definition the longest side of the collector. If not provided, `area` must be provided. If `area` and `width` are provided, it is computed from `area/width`.
    
    width : float, optional
        Gross width of the collector (m). It is by definition the shortest side of the collector. If not provided, `area` must be provided. If `area` and `length` are provided, it is computed from `area/length`.
    
    n0 : float
        Intercept efficiency, sometimes referred to as 'optical efficiency'. Valid range: 0.1 - 0.99. It is the nominal efficiency with which the collector operates when (1) the angle of incidence of the irradiance is null, and (2) the heat transfer fluid enters the collector with the same temperature as the environment surroinding the collector.
    
    a1 : float
        First order (linear) loss coefficient (W/m2 K). Valid range: `1e-2` to `1e2`.
    
    a2 : float, optional
        Second order (quadratic) loss coefficient (W/m2 K2). If not provided, it is assumed to be null. Valid range: `0.0` to `1.0`.
    
    IAM : float, list, or dict
        Object defining the shape of the IAM (Incidence Angle Modifier) curve of the collector. See the section :ref:`iam_argument` for information on the possible formats of this argument.
    
    test_flowrate_per_m2 : float, optional
        Flowrate per area unit with wich the collector has been tested (kg/m2 s). It is used to correct the efficiency of the collector considering the operation flowrate. If not provided, its value is assumed to be 0.02.
    
    test_fluid : :doc:`Fluid </fluids/fluid_class>` or str, optional
        Instance of :doc:`Fluid </fluids/fluid_class>`, or a valid name to initialize an instance of this class. If not provided, `"water"` is assumed.
    
    Attributes
    ----------
    model_name : str
        String identifying the collector model. Only available if the user provides it when initializing the class instance.
    
    area : float
        Area of the collector. If not provided by the user as initialization argument, it is computed from `length` and `width`.
    
    length : float
        Long side of the collector (m). Only available if enough data is provided at initialization.
    
    width : float
        Short side of the collector (m). Only available if enough data is provided at initialization.
    
    n0 : float
        Intercept efficiency, sometimes referred to as 'optical efficiency'. 
    
    a1 : float
        First order (linear) loss coefficient (W/m2 K).
    
    a2 : float
        Second order (quadratic) loss coefficient (W/m2 K2).
    
    IAM : float, list, dict, or None
        Object specifying the shape of the IAM (Incidence Angle Modifier) curve. It is the same object provided as `IAM` argument at initialization.
    
    test_flowrate_per_m2 : float
        Flowrate per area unit with wich the collector has been tested (kg/m2 s).
    
    test_fluid : :doc:`Fluid </fluids/fluid_class>`
        :doc:`Fluid </fluids/fluid_class>` instance that models the fluid used to test the collector.
    """
    
    def __init__(self, *,
                 
                 model_name: Optional[ str ] = None,
                 area: Optional[ float ] = None,
                 length: Optional[ float ] = None,
                 width: Optional[ float ] = None,
                 n0: float,
                 a1: float,
                 a2: Optional[ float ] = None,
                 IAM: float | list | dict | None,
                 test_flowrate_per_m2: Optional[ float ] = None,
                 test_fluid: Optional[ str ]  = None,
                 
                 ):
        
        self._model_name = self._validate_argument("model_name", model_name)
        
        if area is not None and length is not None and width is not None:
            self._length = self._validate_argument("length", length)
            self._width = self._validate_argument("width", width)
            self._area = self._validate_argument("area", area)
            if self._width > self._length:
                raise ValueError("SolarCollector: length must be equal to or larger than width.")
        elif area is None and ( length is None or width is None ):
            raise ValueError("SolarCollector: Either the collector's area or its length and width must be provided.")
        elif area is None:
            self._length = self._validate_argument("length", length)
            self._width = self._validate_argument("width", width)
            if self._width > self._length:
                raise ValueError("SolarCollector: length must be equal to or larger than width.")
            self._area = self._length*self._width
        else:
            self._area = self._validate_argument("area", area)
            if length is not None:
                self._length = self._validate_argument("length", length)
                self._width = self._area/self._length
                if self._width > self._length:
                    warnings.warn("SolarCollector: The length provided will be ignored because the width computed from 'area' and 'length' is larger than 'length'.")
                    self._length = None
                    self._width = None
            elif width is not None:
                self._width = self._validate_argument("width", width)
                self._length = self._area/self._width
                if self._width > self._length:
                    warnings.warn("SolarCollector: The width provided will be ignored because the length computed from 'area' and 'length' is smaller than 'width'.")
                    self._length = None
                    self._width = None
            else:
                self._length = None
                self._width = None
                
        self._n0 = self._validate_argument("n0", n0)
        self._a1 = self._validate_argument("a1", a1)
        
        if a2 is not None:
            self._a2 = self._validate_argument("a2", a2)
        else:
            self._a2 = 0
            
        self._IAM = self._validate_argument("IAM", IAM)
        
        if test_flowrate_per_m2 is not None:
            self._test_flowrate_per_m2 = self._validate_argument("test_flowrate_per_m2", test_flowrate_per_m2)
        else:
            self._test_flowrate_per_m2 = 0.02
            
        if test_fluid is not None:
            self._test_fluid = self._validate_argument( "test_fluid", test_fluid )
        else:
            self._test_fluid = Fluid( 'water', p = 300000, T_ref = 60 )
            
        test_flow = self._test_flowrate_per_m2*self._area
        test_fluid_cp = self._test_fluid.cp_ref
        
        log_argument = 1 - self._a1 / ( self._test_flowrate_per_m2*test_fluid_cp )
        
        if log_argument >= 0.5:
            self._FpUL = -( test_flow * test_fluid_cp / self._area )*log( log_argument )
            self._test_conditions = ( test_flow*test_fluid_cp / ( self._area * self._FpUL ) ) * ( 1 - exp( - self._area * self._FpUL / ( test_flow * test_fluid_cp ) ) )
        else:
            warnings.warn("SolarCollector: The flowrate correction algorithm cannot be applied because (1) the loss coefficient a1 is too big, or (2) the test flowrate is too small.")
            self._test_conditions = None
            
    @property
    def model_name(self):
        "String identifying the collector model. Only available if the user provides it when initializing the class instance."
        return self._model_name
            
    @property
    def area(self):
        "Area of the collector. If not provided by the user as initialization argument, it is computed from `length` and `width`."
        return self._area
    
    @property
    def length(self):
        "Long side of the collector (m). Only available if enough data is provided at initialization."
        return self._length
    
    @property
    def width(self):
        "Short side of the collector (m). Only available if enough data is provided at initialization."
        return self._width
    
    @property
    def n0(self):
        "Intercept efficiency, sometimes referred to as 'optical efficiency'."
        return self._n0
    
    @property
    def a1(self):
        "First order (linear) loss coefficient (W/m2 K)."
        return self._a1
    
    @property
    def a2(self):
        "Second order (quadratic) loss coefficient (W/m2 K2)."
        return self._a2
    
    @property
    def IAM(self):
        "Object specifying the shape of the IAM (Incidence Angle Modifier) curve. It is the same object provided as `IAM` argument at initialization."
        return self._IAM
    
    @property
    def test_flowrate_per_m2(self):
        "Flowrate per area unit with wich the collector has been tested (kg/m2 s)."
        return self._test_flowrate_per_m2
    
    @property
    def test_fluid(self):
        "sercpy.fluids.Fluid` instance that models the fluid used to test the collector."
        return self._test_fluid
    
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
        
        if type(argument_name) is not str:
            raise TypeError("SolarCollector._validate_argument: Argument 'argument_name' must be a string.")
        
        if not argument_name in collector_allowed_arguments:
            raise Exception(f"SolarCollector: Unknown argument name: {argument_name}")
            
        if value is None:
            return None
        
        if argument_name == 'model_name':
            try:
                value = str(value)
            except:
                raise TypeError("SolarCollector: Argument 'model_name' must be a string.")
        
        if argument_name in [  
                "area",
                "length",
                "width", ]:
            try:
                value = float( value )
            except:
                raise TypeError(f"SolarCollector: Argument '{argument_name}' must be convertible to type 'float'.")
            if not value > 0:
                raise ValueError(f"SolarCollector: Argument '{argument_name}' must be > 0.")
        
        if argument_name == 'n0':
            try:
                value = float( value )
            except:
                raise TypeError("SolarCollector: Argument 'n0' must be convertible to type 'float'.")
            if not ( value >= 0.1 and value <= 0.99 ):
                raise ValueError("SolarCollector: Argument 'n0' is out of the allowed range: 0.1 <= n0 <= 0.99.")
                
        if argument_name == 'a1':
            try:
                value = float( value )
            except:
                raise TypeError("SolarCollector: Argument 'a1' must be convertible to type 'float'.")
            if not ( value >= 1e-2 and value <= 1e2 ):
                raise ValueError("SolarCollector: Argument 'a1' is out of the allowed range: 0.01 <= a1 <= 100.")
                
        if argument_name == 'a2':
            try:
                value = float( value )
            except:
                raise TypeError("SolarCollector: Argument 'a2' must be convertible to type 'float'.")
            if not ( value >= 0 and value <= 1 ):
                raise ValueError("SolarCollector: Argument 'a2' must be >= 0.")
                
        if argument_name == 'IAM':
            
            if type( value ) in [ list, np.ndarray ]:
                
                try:
                    value = [ float(v) for v in value ]
                    assert all( [ v >= 0 and v <= 1 for v in value ] )
                    assert value[0] == 1 and value[-1] == 0
                except:
                    raise ValueError("SolarCollector: If argument 'IAM' is a list, it must be a list of numeric values >= 0 and <= 1. The first value must be 1. The last value must be 0.")
            
            elif type(value) is dict:
                
                if 'Kl' in value or 'Kt' in value:
                    if not ('Kl' in value and 'Kt' in value):
                        raise ValueError("SolarCollector: If argument 'IAM' is a dictionary containing 'Kl' or 'Kt', it must contain both.")
                    if len( value ) > 2:
                        raise ValueError("SolarCollector: If argument 'IAM' is a dictionary containing 'Kl' and 'Kt', it must not have more components.")
                    for component_name in [ 'Kl', 'Kt' ]:
                        IAM_list = value[ component_name ]
                        try:
                            IAM_list = [ float(v) for v in IAM_list ]
                            assert all( [ v >= 0 and v <= 1 for v in IAM_list ] )
                            assert IAM_list[0] == 1 and IAM_list[-1] == 0
                        except:
                            raise ValueError("SolarCollector: If argument 'IAM' is a dictionary containing 'Kl' and 'Kt', both components must be lists of numeric values >= 0 and <= 1. The first value must be 1. The last value must be 0.")
                        value[ component_name ] = IAM_list
                else:
                    if len( value ) == 0:
                        raise ValueError("SolarCollector: Argument 'IAM' cannot be an empty dictionary.")
                    if not 'b0' in value:
                        raise ValueError("SolarCollector: If argument 'IAM' is a dictionary, it must either contain the keys 'Kt' and 'Kl', or the keys 'b0', 'b1', ...")
                    for b_index in range( len(value) ):
                        if not 'b' + str(b_index) in value:
                            raise ValueError("SolarCollector: Argument 'IAM' is expected to contain the keys 'b0', 'b1', 'b2', ...")
                        try:
                            value[ 'b' + str( b_index ) ] = float( value[ 'b' + str( b_index ) ] )
                        except:
                            raise ValueError(f"SolarCollector: Argument 'IAM' is expected to have a numeric value associated to the key '{'b' + str(b_index)}'.")
                        if not ( value[ 'b' + str( b_index ) ] >= 0 and value[ 'b' + str( b_index ) ] <= 1 ):
                            raise ValueError(f"SolarCollector: Value '{'b' + str(b_index)}' of IAM must be in the range 0 <= {'b' + str(b_index)} <= 1.")
            
            else:
                
                try:
                    value = float( value )
                except:
                    raise TypeError("SolarCollector: Argument 'IAM' must be either a list, a dictionary, or a float.")
                if not ( value >= 0 and value <= 1 ):
                    raise ValueError("SolarCollector: Value of IAM must be in the range 0 <= IAM <= 1.")
        
        if argument_name == 'test_flowrate_per_m2':
            
            try:
                value = float( value )
            except:
                raise TypeError("SolarCollector: Argument 'test_flowrate_per_m2' must be convertible to type 'float'.")
            if not ( value > 0 and value <= 1 ):
                raise ValueError("SolarCollector: Argument 'test_flowrate_per_m2' must be in the range 0 < test_flowrate_per_m2 <= 1.")
        
        if argument_name == 'test_fluid':
            
            if not ( isinstance(value, Fluid) or type( value ) is str ):
                raise TypeError("SolarCollector: Argument 'test_fluid' must be a string or an instance of sercpy.fluids.Fluid.")
            if type( value ) is str:
                value = Fluid( value, p = 300000, T_ref = 60 )
                
        return value
    
    def compute_flowrate_correction_factor( self, fluid, flowrate ):
        """
        Method to compute the flowrate correction factor.
        
        **What does this value do?**
        
        The standard formula for the efficiency of the collector, based on the parameters `n0`, `a1`, and `a2`, does not take into account the flowrate that the collector is operating with.
        
        The aforementioned parameters were determined under a certain "test flowrate".
        
        If the operation flowrate is larger than the test flowrate, the temperature change inside the collector decreases. Thus, the collector operates at a lower temperature. This increases its efficiency. The opposite happens when the operation flowrate is less than the test flowrate.
        
        To take this into account, the value returned by this method should be multiplied by the efficiency determined with the "standard formula" mentioned above.
        
        The correction factor is obtained with the method discussed on page 307 (Section 6.20) of the book **Solar Engineering of Thermal Processes** by John A. Duffie and William A. Beckman, 3rd Edition. ISBN: `978-0-471-69867-8 <https://search.worldcat.org/title/427546132>`_.
        
        Parameters
        ----------
        fluid : :doc:`Fluid </fluids/fluid_class>`
            Fluid being used as heat transfer fluid.
        flowrate : float
            Flowrate flowing through the collector (kg/s).

        Returns
        -------
        float
            Correction factor for the efficiency of the collector.
        
        """
        
        if not hasattr( fluid, 'cp_ref' ):
            if not isinstance(fluid, Fluid):
                raise TypeError("SolarCollector.compute_flowrate_correction_factor: Argument 'fluid' must be an instance of sercpy.fluids.Fluid.")
            raise AttributeError("SolarCollector.compute_flowrate_correction_factor: Argument 'fluid' does not have the attribute 'cp_ref'. In order for the object to have this attribute, the argument 'T_ref' must be provided at initialization.")
        
        if self._test_conditions is None:
            return 1
        
        use_conditions = ( flowrate*fluid.cp_ref/(self._area*self._FpUL) )*( 1 - exp( - self._area*self._FpUL/( flowrate*fluid.cp_ref ) ) )
        flowrate_correction_factor = use_conditions/self._test_conditions
        
        return flowrate_correction_factor
    
    def compute_IAM( self, *, aoi = None, longi = None, trans = None ):
        """
        Compute the IAM (Incidence Angle Modifier) correction factor.

        Parameters
        ----------
        aoi : float, optional
            aoi: Angle of indicence with respect to a vector that is normal to the collector's plane. Only needed for collectors with monoaxial IAM functions. If not provided, it can be derived from `longi` and `trans`. The default is None.
        longi : float, optional
            Projection of aoi on a plane that is perpendicular to the collector's plane and parallel to the tubes' direction (assuming the collector is tubular). Only needed for collectors with biaxial IAM functions. The default is None.
        trans : float, optional
            Projection of aoi on a plane that is normal to the tubes' direction (assuming the collector is tubular). Only needed for collectors with biaxial IAM functions. The default is None.

        Returns
        -------
        float
            IAM correction factor.

        """
        
        if aoi is not None:
            try:
                aoi = _to_array( aoi )
            except NonConvertibleToArray:
                raise TypeError("SolarCollector.compute_IAM: 'aoi' could not be interpreted as a number nor as an array.")
                
        if trans is not None:
            try:
                trans = _to_array( trans )
            except NonConvertibleToArray:
                raise TypeError("SolarCollector.compute_IAM: 'trans' could not be interpreted as a number nor as an array.")
                
        if longi is not None:
            try:
                longi = _to_array( longi )
            except NonConvertibleToArray:
                raise TypeError("SolarCollector.compute_IAM: 'longi' could not be interpreted as a number nor as an array.")
        
        if not hasattr( self, "_IAM_type" ):
            if self._IAM is None:
                self._IAM_type = 0
            elif type( self._IAM ) is list:
                self._IAM_type = 1
                self._K_values = self._IAM
            elif type( self._IAM ) is dict and 'b0' in self._IAM:
                self._IAM_type = 2
            elif type( self._IAM ) is float:
                self._IAM_type = 3
            elif type( self._IAM ) is dict and 'Kl' in self._IAM:
                self._IAM_type = 4
                self._Kl_values = self._IAM[ 'Kl' ]
                self._Kt_values = self._IAM[ 'Kt' ]
            else:
                raise ValueError("SolarCollector.compute_IAM: IAM format coud not be identified.")
        
        if aoi is None and trans is None and longi is None:
            raise ValueError("SolarCollector.compute_IAM: No angle data was provided.")
        
        lengths = { len( x ) for x in [ aoi, trans, longi ] if x is not None }
        if len( lengths ) != 1:
            raise ValueError("SolarCollector.compute_IAM: All arrays must have the same length.")
        
        if self._IAM_type == 0:
            return np.ones( lengths.pop() )
        
        elif self._IAM_type in [ 1, 2, 3 ]:
            
            if aoi is None:
                if ( trans is None or longi is None ):
                    raise ValueError("SolarCollector.compute_IAM: transversal and longitudinal angle data is needed if aoi is not provided.")
                
                trans_rad = ( np.pi/180 )*trans
                longi_rad = ( np.pi/180 )*longi
                
                tg2_aoi = np.tan( trans_rad ) ** 2 + np.tan( longi_rad ) ** 2
                aoi_rad = np.arctan( np.sqrt( tg2_aoi ) )
                aoi = ( 180/np.pi )*aoi_rad
                
            if self._IAM_type == 1:
                
                result = np.interp( aoi, np.linspace( 0, 90, len( self._K_values ) ), self._K_values )
            
            else: 
                
                aoi_masked = np.asarray( aoi, dtype=float ).copy()
                aoi_masked[ aoi_masked > 85 ] = np.nan
                aoi_masked_rad = ( np.pi/180 )*aoi_masked
                
                if self._IAM_type == 2:
                    result = 1 - sum( [ self._IAM[ 'b' + str( index ) ] * ( 1/np.cos( aoi_masked_rad ) - 1 ) ** ( index + 1 )  for index in range( len( self._IAM ) ) ] )
                elif self._IAM_type == 3:
                    result = 1 - self._IAM * ( 1/np.cos( aoi_masked_rad ) - 1 )
                else:
                    raise Exception("SolarCollector.compute_IAM: Unexpected error.")
                
                result[ np.isnan( result ) | ( result < 0 ) ] = 0                
                
        elif self._IAM_type == 4:
            if trans is None or longi is None:
                raise ValueError("SolarCollector.compute_IAM: 'trans' and 'longi'. must be provided for biaxial IAM functions.")
            
            result = np.interp( trans, np.linspace( 0, 90, len( self._Kt_values ) ), self._Kt_values ) * np.interp( longi, np.linspace( 0, 90, len( self._Kt_values ) ), self._Kl_values )
            
        else:
            raise Exception("SolarCollector.compute_IAM: Unexpected error: _IAM_type not valid.")
        
        if len( result ) == 1:
            result = float( result[0] )
        
        return result
    
    def compute_outlet_state(self, flowrate, state_in, irradiance, IAM_factor, Tamb, flowrate_correction_factor):
        """
        Compute the state of the fluid leaving the collector.
        
        This method takes the operating conditions of the collector (irradiance, flowrate, inlet state, etc.) and computes the state of the fluid as it leaves the collector.
        
        Parameters
        ----------
        flowrate : float
            Mass flowrate entering the collector (kg/s).
        
        state_in : :doc:`FluidState </fluids/fluidstate_class>`
            State of the fluid as it enters the collector.
        
        irradiance : float
            Solar irradiance on the collector's plane (W/m2).
        
        IAM_factor : float
            Dimensionless quantity defining the correction factor associated to IAM (Incidence Angle Modifier).
        
        Tamb : float
            Ambient temperature (°C).
        
        flowrate_correction_factor : float
            Dimensionless quantity defining the correction factor associated to the flowrate. See :meth:`SolarCollector.compute_flowrate_correction_factor`.
        
        Returns
        -------
        state_out : :doc:`FluidState </fluids/fluidstate_class>`
            State of the fluid leaving the collector.
        """
        
        T_in = state_in.T
        h_in = state_in.h
        efficiency = flowrate_correction_factor*max( [ self._n0*IAM_factor - self._a1*( T_in - Tamb )/irradiance - self._a2*(T_in - Tamb)*abs( T_in - Tamb )/irradiance , 0 ] )
        power = efficiency*irradiance*self._area
        h_out = h_in + power/flowrate
        return state_in.fluid.state( h = h_out )

field_allowed_arguments = [
    
    "collector",
    "coll_tilt",
    "coll_azimuth",
    "ground_albedo",
    "total_colls",
    "coll_rows",
    "colls_per_row",
    "coll_disposition",
    "tube_direction",
    "non_shadeable_rows",
    "non_shadeable_colls",
    "ground_fraction_covered",
    "row_spacing",
    "clear_horizon",
    "row_mode",
    "release_vapor",
    "vapor_tolerance",
    "max_iterations",
    
    ]

class SolarField( Device ):
    """
    Class that models a solar collector field.
    
    Parameters
    ----------
    collector : :doc:`SolarCollector <solar_collector_class>`
        Object that models each indidual collector of the solar field.
    
    coll_tilt : float, optional
        Tilt angle of each collector with respect to the ground. If not provided,
        it will be set automatically by a :doc:`MeteoProfile </meteo_profile/meteo_profile_class>` instance when the
        method `MeteoProfile.compute_poa_irradiance` gets called using the `SolarField` instance as argument.
    
    coll_azimuth : float, optional
        Azimuthal angle of the collectors. If not provided, it will be set
        automatically by a :doc:`MeteoProfile </meteo_profile/meteo_profile_class>` instance when the method
        `MeteoProfile.compute_poa_irradiance` gets called using the `SolarField` instance as argument.
        
    ground_albedo : float, optional
        Albedo of the ground, i.e., irradiance fraction reflected by it.
        The fraction is expressed as a decimal value in the range 0 - 1.
        If not provided, this parameter will be automatically set by a
        `MeteoProfile` instance when the method `MeteoProfile.compute_poa_irradiance` is called.
    
    total_colls : int, optional
        Number of collectors that make up the solar field. If not provided,
        it can be computed as `coll_rows*colls_per_row`.
    
    coll_rows : int, optional
        Number of collector groups that make up the solar field. This parameter
        only matters for the model's results if the argument `row_mode` is set to
        `"series"`, or if the argument `non_shadeable_rows` is provided. If not provided,
        its value can be determined as `total_cols/colls_per_row` (this result must be an integer).
    
    colls_per_row : int, optional
        Number of collectors making up each collector row. This parameter only
        matters for the model's results if the argument `row_mode` is set to `"series"`,
        or if the argument `non_shadeable_rows` is provided. If not provided, its value
        can be determined as `total_cols/coll_rows` (this result must be an integer).
        
    row_mode : str, optional
        Parameter defining whether the collectors in a row are arranged in series or in parallel.
        Possible values for this argument: `"series"`, `"parallel"`.
        If arranged in series (common for heat pipe evacuated tube collectors), the heat transfer
        fluid passes from one collector to another one,
        entering each one of them with the
        temperature it left the previous one with.
        If arranged in parallel (common for flat plate collectors), the heat transfer
        fluid flow gets equally distributed among all
        the collectors, entering all of them with the same temperature.
        In the latter case, it is actually not
        mandatory to specify `coll_rows` or `colls_per_row`,
        since the number of collectors per row only
        makes a difference when they are arranged in series.
        IF not provided, this parpameter defaults to `"parallel"`.
    
    coll_disposition : str, optional
        String identifying whether the tilted side of the collector is the short
        side or the long side. The former case can be identified with the strings
        `"horizontal"` and `"landscape"`. The latter case can be identified
        with the strings `"vertical"` and `"portrait"`.
    
    tube_direction : str, optional
        This parameter only makes a difference for collectors that have biaxial IAM
        (Incidence Angle Modifier) functions, which in most cases are evacuated tube collectors.
        This parameter can have the values `"vertical"`, `"tilted"`, or `"horizontal"`.
        In the two former cases (both are interpreted exactly the same way),
        the tubes point towards the ground
        (not perpendicularly; the angle depends on the tilt of the collector),
        whereas in the latter case, the tubes are parallel to the ground. 
    
    non_shadeable_rows : int, optional
        Number of collector rows that are not subject to self-shading.
        Note that more than one collector row may be at the front of the collector field,
        since a collector row may be defined as a group of collectors connected in series
        (see the argument `row_mode`). This argument cannot be provided together with `non_shadeable_colls`,
        since both arguments provide the same information in different ways.
    
    non_shadeable_colls : int, optional
        Number of collectors that are not subject to self-shading.
        If the number of collectors per row has been specified, this
        argument must be equivalent to an entire number of rows
        (i.e. `non_shadeable_colls/colls_per_row` must be a whole number).
        This argument is useful when the number of rows
        is not being taken into account. This argument cannot be provided
        together with `non_shadeable_rows`, since both arguments provide the same
        information in different ways.
    
    ground_fraction_covered : float, optional
        Ratio between the tilted side of the solar collectors and the row spacing between them.
        This parameter is relevant for modeling of self-shading. This value can be computed internally if
        the attributes `length` and `width` of the object `collector` have been correctly defined,
        and if the arguments `coll_disposition` and `row_spacing` are provided for this class.
    
    row_spacing : float, optional
        Distance between collector rows (m).
        
    clear_horizon : bool
        Boolean value defining whether the non-shadeable rows receive diffuse irradiance from the horizon.
    
    release_vapor : bool, optional
        If this parameter is set to `True`, the vapor produced when the saturation
        temperature of the heat transfer fluid is achieved will be released and
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
    outlet : :ref:`Outlet <class_outlet>`
        Instance of the class :ref:`sercpy.devices.Outlet <class_outlet>` representing the main fluid outlet of the solar field.
    
    collector : :doc:`SolarCollector </devices/solar/solar_collector_class>`
        Object that models each indidual collector of the solar field.
    
    input_convergence : bool
        Boolean value stating whether input convergence was achieved the last time the method
        `SolarField.compute_outputs` was called. The concept of "input convergence"
        refers to whether the inputs of the SolarField instance are similar enough
        in consecutive iterations of a time step, so that no further computation is needed.
    
    useful_power : float
        Useful power transferred to the heat transfer fluid (W). The word
        'useful' is used to differentiate this value from the power used to
        generate undesired vapor that is then released. This attribute gets
        updated every time the method `SolarField.compute_outputs` is called.
    
    wasted_power : float
        Thermal power used to generate undesired vapor that is then released (W).
        This attribute gets updated every time the method `SolarField.compute_outputs` is called.
    
    vapor_flowrate : float
        Undesired vapor being released from the solar field (kg/s). This attribute
        gets updated every time the method `SolarField.compute_outputs` is called.
    
    efficiency : float
        Ratio between the useful power and the total available energy,
        which is computed as the irradiance on the collectors' plane,
        multiplied by the solar field's total area. This attribute
        gets updated every time the method `SolarField.compute_outputs` is called.
    
    iterations : int
        Number of iterations carried out the last time the method
        `SolarField.compute_outputs` was called. An iteration process is only
        necessary when undesired vapor is being produced and
        released due to overheating of the collectors.
    
    vapor_release_convergence : bool
        Boolean value stating whether convergence for the vapor release modeling
        was achieved the last time the method `SolarField.compute_outputs` was called.
        If no vapor is released, this value is set to True.
    
    coll_tilt : float
        Tilt of the collectors with respect to the ground (degree, °).
    
    coll_azimuth : float
        Azimuthal angle of the collectors. Degrees east of north. See the
        :doc:`documentation on azimuthal angles <azimuthal_angle>`
        for more information on how the value is defined.
    
    coll_disposition : str
        One of the following strings: 'HORIZONTAL', 'LANDSCAPE',
        'VERTICAL', 'PORTRAIT'. See the argument with the same name in the class' documentation.
    
    tube_direction : str
        One of the following strings: 'HORIZONTAL', 'VERTICAL',
        'TILTED'. See the argument with the same name in the class' documentation.
    
    ground_fraction_covered : float
        Ratio between the row spacing of the solar field and the
        length of the collectors' tilted size. It is used by the self-shading modeling algorithm.
    
    ready_to_simulate : bool
        Boolean value stating whether all attributes needed for
        the collector to be used in a simulation have been established.
    
    """
    
    def __init__( self, *,
            
            collector: SolarCollector,
            coll_tilt: Optional[ float ] = None,
            coll_azimuth: Optional[ float ] = None,
            total_colls: Optional[ int ] = None,
            coll_rows: Optional[ int ] = None,
            colls_per_row: Optional[ int ] = None,
            ground_albedo: Optional[ int ] = None,
            row_mode: Optional[ str ] = None,
            coll_disposition: Optional[ str ] = None,
            tube_direction: Optional[ str ] = None,
            non_shadeable_rows: Optional[ int ] = None,
            non_shadeable_colls: Optional[ int ] = None,
            ground_fraction_covered: Optional[ float ] = None,
            row_spacing: Optional[ float ] = None,
            clear_horizon: Optional[ bool ] = None,
            release_vapor: Optional[ bool ] = None,
            vapor_tolerance: Optional[ float ] = None,
            max_iterations: Optional[ int ] = None, ):
        
        self._collector = self._validate_argument("collector", collector)
        self._coll_tilt = self._validate_argument("coll_tilt", coll_tilt)
        self._coll_azimuth = self._validate_argument("coll_azimuth", coll_azimuth)
        self._ground_albedo = self._validate_argument( "ground_albedo", ground_albedo )
        
        if self._coll_tilt is not None and self._coll_azimuth is not None:
            self._compute_rotation_matrix()
        if self._coll_tilt is not None:
            self._compute_diffuse_IAM()
            self._compute_shadeable_rows_visible_sky_dome_fraction()
        
        if self._coll_tilt is None:
            self._tilt_mode = 'auto'
        else:
            self._tilt_mode = 'manual'
        
        if self._coll_azimuth is None:
            self._azimuth_mode = 'auto'
        else:
            self._azimuth_mode = 'manual'
            
        if self._ground_albedo is None:
            self._albedo_mode = 'auto'
        else:
            self._albedo_mode = 'manual'
        
        if row_mode is None:
            self._row_mode = 'PARALLEL'
        else:
            self._row_mode = self._validate_argument("row_mode", row_mode)
        
        if total_colls is not None and coll_rows is not None and colls_per_row is not None:
            self._total_colls = self._validate_argument("total_colls", total_colls)
            self._coll_rows = self._validate_argument("coll_rows", coll_rows)
            self._colls_per_row = self._validate_argument("colls_per_row", colls_per_row)
            if not ( self._total_colls%self._coll_rows == 0  and  self._total_colls // self._coll_rows == self._colls_per_row ):
                raise ValueError("SolarField: Values of 'total_colls', 'coll_rows' and 'colls_per_row' are inconsistent. colls_per_row must be equal to total_colls/coll_rows.")
        
        elif total_colls is not None and coll_rows is not None:
            self._total_colls = self._validate_argument("total_colls", total_colls)
            self._coll_rows = self._validate_argument("coll_rows", coll_rows)
            if not ( self._total_colls%self._coll_rows == 0 ):
                raise ValueError("SolarField: 'total_colls' must be divisible by 'coll_rows'.")
            self._colls_per_row = self._total_colls // self._coll_rows
        
        elif coll_rows is not None and colls_per_row is not None:
            self._coll_rows = self._validate_argument("coll_rows", coll_rows)
            self._colls_per_row = self._validate_argument("colls_per_row", colls_per_row)
            self._total_colls = self._coll_rows*self._colls_per_row
        
        elif total_colls is not None and colls_per_row is not None:
            self._total_colls = self._validate_argument("total_colls", total_colls)
            self._colls_per_row = self._validate_argument("colls_per_row", colls_per_row)
            if not self._total_colls%self._colls_per_row == 0:
                raise ValueError("SolarField: 'total_colls' must be divisible by 'colls_per_row'.")
            self._coll_rows = self._total_colls // self._colls_per_row
        
        elif total_colls is not None:
            if self._row_mode == 'SERIES':
                raise ValueError("SolarField: Number of collectors per row, or number of rows, must be provided along with 'total_colls' if argument 'row_mode' is set to 'series'.")
            if non_shadeable_rows is not None:
                raise ValueError("SolarField: Argument 'non_shadeable_rows' was provided but not the number of collector rows nor the number of collectors per row.")
            self._total_colls = self._validate_argument("total_colls", total_colls)
            self._coll_rows = self._total_colls
            self._colls_per_row = 1
        
        elif coll_rows is not None:
            raise ValueError("SolarField: Number of collectors cannot be determined. 'coll_rows' must be provided along with 'total_colls' or 'colls_per_row'.")
        
        elif colls_per_row is not None:
            raise ValueError("SolarField: Number of collectors cannot be determined. 'colls_per_row' must be provided along with 'total_colls' or 'coll_rows'.")
        
        else:
            raise ValueError("SolarField: Number of collectors was not provided. Arguments: 'total_colls', 'coll_rows', 'colls_per_row'.")
        
        if tube_direction is not None:
            self._tube_direction = self._validate_argument( "tube_direction", tube_direction )
        else:
            self._tube_direction = 'VERTICAL'
            
        if non_shadeable_rows is not None and non_shadeable_colls is not None:
            raise ValueError( "SolarField: The arguments 'non_shadeable_rows' and 'non_shadeable_colls' cannot be provided together." )
        elif non_shadeable_rows is not None:
            self._non_shadeable_rows = self._validate_argument("non_shadeable_rows", non_shadeable_rows)
            if self._non_shadeable_rows > self._coll_rows:
                raise ValueError(f"SolarField: 'non_shadeable_rows' ({self._non_shadeable_rows}) cannot be larger than 'coll_rows' ({self._coll_rows}).")
        elif non_shadeable_colls is not None:
            non_shadeable_colls = self._validate_argument("non_shadeable_colls", non_shadeable_colls)
            if not non_shadeable_colls%self._colls_per_row == 0:
                raise ValueError(f"SolarField: 'non_shadeable_colls' must correspond to an entire number of rows (i.e. it must be a multiple of 'colls_per_row' which is { self._colls_per_row }).")
            self._non_shadeable_rows = non_shadeable_colls // self._colls_per_row
            if self._non_shadeable_rows > self._coll_rows:
                raise ValueError(f"SolarField: 'non_shadeable_rows' ({self._non_shadeable_rows}) cannot be larger than 'coll_rows' ({self._coll_rows}).")
        else:
            self._non_shadeable_rows = max( [ int( self._coll_rows * 0.5 ) , 1 ] )
            
        self._shadeable_rows = self._coll_rows - self._non_shadeable_rows
        
        
        ground_fraction_covered = self._validate_argument("ground_fraction_covered", ground_fraction_covered)
        row_spacing = self._validate_argument("row_spacing", row_spacing)
        coll_disposition = self._validate_argument("coll_disposition", coll_disposition)
        
        if ground_fraction_covered is not None:
            self._ground_fraction_covered = self._validate_argument("ground_fraction_covered", ground_fraction_covered)
        
        elif row_spacing is not None and (  ( coll_disposition in [ 'HORIZONTAL', 'LANDSCAPE' ] and self._collector.width  is not None )  or
                                            ( coll_disposition in [ 'VERTICAL',   'PORTRAIT'  ] and self._collector.length is not None )      ):
            
            if coll_disposition in [ 'HORIZONTAL', 'LANDSCAPE' ]:
                self._ground_fraction_covered = self._collector.width / row_spacing
            else:
                self._ground_fraction_covered = self._collector.length / row_spacing
        
        else:
            warnings.warn("SolarField: Not enough data was provided to determine parameters for self-shading modeling. Default conditions are assumed.")
            self._ground_fraction_covered = 0.5
        
        if self._coll_tilt is not None and self._ground_fraction_covered is not None and self._ground_fraction_covered * np.cos( ( np.pi/180 )*self._coll_tilt ) >= 1:
            raise ValueError("SolarField: Collector rows are overlapped. Ground factor covered must be reduced, or row spacing must be increased.")
            
        self._coll_disposition = self._validate_argument("coll_disposition", coll_disposition)
        
        if clear_horizon is not None:
            self._clear_horizon = self._validate_argument("clear_horizon", clear_horizon)
        else:
            self._clear_horizon = True
        
        if release_vapor is not None:
            self._release_vapor = self._validate_argument("release_vapor", release_vapor)
        else:
            self._release_vapor = True
            
        if vapor_tolerance is not None:
            self._vapor_tolerance = self._validate_argument("vapor_tolerance", vapor_tolerance)
        else:
            self._vapor_tolerance = 1e-3
        
        if max_iterations is not None:
            self._max_iterations = self._validate_argument("max_iterations", max_iterations)
        else:
            self._max_iterations = 30
        
        self._outlet = Outlet()
    
    @property
    def outlet(self):
        "Instance of the class sercpy.devices.Outlet representing the main fluid outlet of the solar field."
        return self._outlet
    
    @property
    def collector(self):
        "Instance of the class sercpy.solar.Collector. It models the individual collectors used to build the solar field."
        return self._collector
    
    @property
    def input_convergence(self):
        "Boolean value stating whether convergence was achieved the last time the method SolarField.compute_outputs was called. The concept of 'convergence' refers to whether the inputs of the SolarField instance are similar enough in consecutive iterations of a simulation time step, so that no further computation is needed."
        if not hasattr( self, "_input_convergence" ):
            raise AttributeError("SolarField: Attribute 'convergence' has not been computed yet. This attribute gets updated when the method 'SolarField.compute_outputs' is called.")
        return self._input_convergence
    
    @property
    def useful_power(self):
        "Useful power transferred to the heat transfer fluid (W). The word 'useful' is used to differentiate this value from the power used to generate undesired vapor that is then released. This attribute gets updated every time the method 'SolarField.compute_outputs' is called."
        if not hasattr( self, "_useful_power" ):
            raise AttributeError("SolarField: Attribute 'useful_power' has not been computed yet. This attribute gets updated when the method 'SolarField.compute_outputs' is called.")
        return self._useful_power
    
    @property
    def wasted_power(self):
        "Thermal power used to generate undesired vapor that is then released (W). This attribute gets updated every time the method 'SolarField.compute_outputs' is called."
        if not hasattr( self, "_wasted_power" ):
            raise AttributeError("SolarField: Attribute 'wasted_power' has not been computed yet. This attribute gets updated when the method 'SolarField.compute_outputs' is called.")
        return self._wasted_power
    
    @property
    def vapor_flowrate(self):
        "Undesired vapor being released from the solar field (kg/s). This attribute gets updated every time the method 'SolarField.compute_outputs' is called."
        if not hasattr( self, "_vapor_flowrate" ):
            raise AttributeError("SolarField: Attribute 'vapor_flowrate' has not been computed yet. This attribute gets updated when the method 'SolarField.compute_outputs' is called.")
        return self._vapor_flowrate
    
    @property
    def efficiency(self):
        "Ratio between the useful power and the total available energy, which is computed as the irradiance on the collectors' plane, multiplied by the solar field's total area."
        if not hasattr( self, "_efficiency" ):
            raise AttributeError("SolarField: Attribute 'efficiency' has not been computed yet. This attribute gets updated when the method 'SolarField.compute_outputs' is called.")
        return self._efficiency
    
    @property
    def iterations(self):
        "Number of iterations carried out the last time the method SolarField.compute_outputs was called. An iteration process is only necessary when undesired vapor is being produced and released due to overheating of the collectors."
        if not hasattr( self, "_iterations" ):
            raise AttributeError("SolarField: Attribute 'iterations' has not been computed yet. This attribute gets updated when the method 'SolarField.compute_outputs' is called.")
        return self._iterations
    
    @property
    def vapor_release_convergence(self):
        "Boolean value stating whether convergence for the vapor release modeling was achieved the last time the method SolarField.compute_outputs was called. If no vapor is released, this value will be True."
        if not hasattr( self, "_vapor_release_convergence" ):
            raise AttributeError("SolarField: Attribute 'vapor_release_convergence' has not been computed yet. This attribute gets updated when the method 'SolarField.compute_outputs' is called.")
        return self._vapor_release_convergence
    
    @property
    def coll_tilt(self):
        "Tilt of the collectors with respect to the ground (degree, °)."
        if self._coll_tilt is None:
            raise AttributeError("SolarField: Attribute 'coll_tilt' has not been defined yet. This attribute can be defined automatically with the method 'MeteoProfile.compute_poa_irradiance' using this SolarField instance as argument.")
        return self._coll_tilt
    
    @property
    def coll_azimuth(self):
        "Azimuthal angle of the collectors. Degrees east of north."
        if self._coll_azimuth is None:
            raise AttributeError("SolarField: Attribute 'coll_azimuth' has not been defined yet. This attribute can be defined automatically with the method 'MeteoProfile.compute_poa_irradiance' using this SolarField instance as argument.")
        return self._coll_azimuth
    
    @property
    def ground_albedo(self):
        "Irradiance fraction reflected by the ground in front of the solar field."
        if self._ground_albedo is None:
            raise AttributeError("SolarField: Attribute 'ground_albedo' has not been defined yet. This attribute can be defined automatically with the method 'MeteoProfile.compute_poa_irradiance' using this SolarField instance as argument.")
        return self._ground_albedo
    
    @property
    def coll_disposition(self):
        "One of the following strings: 'HORIZONTAL', 'LANDSCAPE', 'VERTICAL', 'PORTRAIT'. See the argument with the same name in the class' documentation."
        if self._coll_disposition is None:
            raise AttributeError("SolarField: 'coll_disposition' has not been specified.")
        return self._coll_disposition
    
    @property
    def tube_direction(self):
        "One of the following strings: 'HORIZONTAL', 'VERTICAL', 'TILTED'. See the argument with the same name in the class' documentation."
        return self._tube_direction
    
    @property
    def ground_fraction_covered(self):
        "Ratio between the row spacing of the solar field and the length of the collectors' tilted size. It is used by the self-shading modeling algorithm."
        return self._ground_fraction_covered
    
    @property
    def row_width_to_coll_length_ratio(self):
        return 100
    
    @property
    def ready_to_simulate(self):
        "Boolean value stating whether all attributes needed for the SolarField instance to be used in a simulation have been established."
        return all( [
            
            self._coll_tilt is not None,
            self._coll_azimuth is not None,
            hasattr( self, "_h_tolerance" ) or hasattr( self, "_temp_tolerance" ),
            hasattr( self, "_relative_tolerance" ),
            hasattr( self, "_inlet" ),
            
            ] )
    
    @coll_tilt.setter
    def coll_tilt(self, value):
        "Set the attribute 'coll_tilt'."
        if value is None:
            raise TypeError("SolarField: 'coll_tilt' must be a floating point number in the range: 0 <= coll_tilt <= 90.")
        self._coll_tilt = self._validate_argument("coll_tilt", value)
        self._compute_diffuse_IAM()
        self._compute_shadeable_rows_visible_sky_dome_fraction()
        if self._coll_azimuth is not None:
            self._compute_rotation_matrix()
    
    @coll_azimuth.setter
    def coll_azimuth(self, value):
        "Set the attribute 'coll_azimuth'."
        if value is None:
            raise TypeError("SolarField: 'coll_azimuth' must be a floating point number in the range: 0 <= coll_tilt < 360.")
        self._coll_azimuth = self._validate_argument("coll_azimuth", value)
        if self._coll_tilt is not None:
            self._compute_rotation_matrix()
    
    def set_auto_attributes( self, *, coll_tilt, coll_azimuth, ground_albedo ):
        """
        Method used by :doc:`MeteoProfile </meteo_profile/meteo_profile_class>` to set the attributes
        'coll_tilt' and 'coll_azimuth' based on the geographical location
        to which the `MeteoProfile` instance corresponds.
        
        This method **only** changes the attributes of the `SolarField`
        that have not been defined by the user at initialization.

        Parameters
        ----------
        coll_tilt : float
            Collector tilt with respect to the ground (degrees, °). Valid range: `0` - `90`
        coll_azimuth : float
            Collector azimuth. Degrees east of north. See the
            :doc:`documentation on azimuthal angles <azimuthal_angle>`
            for more information on how the value is defined.

        Returns
        -------
        None.

        """
        if self._tilt_mode == 'auto':
            if coll_tilt is None:
                raise ValueError("SolarField.set_auto_orientation: 'coll_tilt' was expected to be defined.")
            self._coll_tilt = self._validate_argument( "coll_tilt", coll_tilt )
            if self._ground_fraction_covered is not None and self._ground_fraction_covered * np.cos( ( np.pi/180 )*self._coll_tilt ) >= 1:
                raise ValueError("SolarField: Collector rows are overlapped. Ground factor covered must be reduced, or row spacing must be increased.")
        if self._azimuth_mode == 'auto':
            if coll_azimuth is None:
                raise ValueError("SolarField.set_auto_orientation: 'coll_azimuth' was expected to be defined.")
            self._coll_azimuth = self._validate_argument( "coll_azimuth", coll_azimuth )
            
        if self._albedo_mode == 'auto':
            self._ground_albedo = ground_albedo
            
        if self._tilt_mode == 'auto' or self._azimuth_mode == 'auto':
            self._compute_rotation_matrix()
        
        if self._tilt_mode == 'auto':
            self._compute_diffuse_IAM()
            self._compute_shadeable_rows_visible_sky_dome_fraction()
    
    def _compute_rotation_matrix( self ):
        """
        Method to compute an attribute called '_rotation_matrix'.
        
        This attribute converts vectors from one reference system to another.
        
        In particular, it converts vectors from a cartesian system whose axes
        are parallel to the north-south,
        east-west, and vertical directions, to a cartesian system
        whose axes are parallel to the collector sides
        and normal to the collector plane.
        
        This matrix is then used to convert the solar position to a system based on the collector.
        The result is then used to determine the incidence angles.
        
        Raises
        ------
        AttributeError
            If not all attributes necessary to compute the matrix have been defined.
        
        Returns
        -------
        None.
        
        """
        if self._coll_tilt is None:
            raise AttributeError("SolarField._compute_rotation_matrix: Rotation matrix cannot be computed because coll_tilt is not defined.")
        if self._coll_azimuth is None:
            raise AttributeError("SolarField._compute_rotation_matrix: Rotation matrix cannot be computed because coll_azimuth is not defined.")
        
        coll_tilt_rad = self._coll_tilt*np.pi/180
        coll_azimuth_rad = self._coll_azimuth*np.pi/180
            
        self._rotation_matrix = np.linalg.inv(np.array([[  np.cos( coll_azimuth_rad )*np.cos( coll_tilt_rad ), -np.sin( coll_azimuth_rad ), np.cos( coll_azimuth_rad )*np.sin( coll_tilt_rad ) ],
                                                        [  np.sin( coll_azimuth_rad )*np.cos( coll_tilt_rad ),  np.cos( coll_azimuth_rad ), np.sin( coll_azimuth_rad )*np.sin( coll_tilt_rad ) ],
                                                        [ -np.sin( coll_tilt_rad ),                             0,                          np.cos( coll_tilt_rad )         ] ] ) )
    
    def compute_poa_irradiance( self, GHI, DNI, DHI, apparent_solar_zenith, solar_azimuth, ground_albedo = None, doy = None, dni_extra = None, diffuse_irradiance_model = None  ):
        """
        Compute the irradiance on the plane of the collectors and the IAM correction factor.
        
        The method can compute the results for single numeric values and for data arrays.
        
        Both irradiance and IAM are computed for the collector
        rows that are subject to self-shading, and the ones that are not.
        If no enough data is provided at initialization for
        the self-shading algorithm to work, it is assumed
        that all collector rows are not subject to self-shading.
        
        **The first four arguments (`GHI` to `solar_azimuth`) are not
        optional and must have the same length, in the case that they are arrays of data.**
        
        Parameters
        ----------
        GHI : float or array-like
            Global horizontal irradiance (W/m2).
        
        DNI : float or array-like
            Direct normal irradiance (W/m2).
        
        DHI : float or array-like
            Diffuse horizontal irradiance (W/m2).
        
        apparent_solar_zenith : float or array-like
            Zenithal angle of the solar position (degree, °).
        
        solar_azimuth : float or array-like
            Azimuthal angle of the solar position (degree, °).
        
        ground_albedo : float or array-like, optional
            Albedo of the ground in front of the solar collector field.
            Unlike the previous arguments, `ground_albedo` can be a single numeric
            value despite the first four argument being data arrays. It can also
            be an array with the same length as the other arrays.
            If not provided, this argument defaults to the attrbiute
            `ground_albedo` of the `SolarField` instance.
            If this attribute has not been defined, it defaults to `0.2`.
        
        doy : int or array-like, optional
            Integer value identifying the day of the year. If provided, it must
            have the same length as the irradiance and solar position data. The default is None.
        
        dni_extra : float or array-like, optional
            Extraterrestrial normal irradiance. It can be a single numeric
            value or an array with the same length as the irradiance and
            solar position data. If not provided, it defaults to 1366.1.
        
        diffuse_irradiance_model : str, optional
            Model used for computing the diffuse irradiance. Valid
            values: `"isotropic"`, `"perez"`. If not provided, it defaults to `"perez"`.

        Returns
        -------
        irradiance_first_row : float or np.array
            Irradiance on the collector rows that are not subject to self-shading.
        IAM_first_row : float or np.array
            IAM correction factor for the collector rows that are not subject to self-shading.
        irradiance_shadeable_rows : float or np.array
            Irradiance on the collector rows that are subject to self-shading.
        IAM_shadeable_rows : float or np.array
            IAM correction factor for the collector rows that are subject to self-shading.

        """
        if not hasattr(self, "_coll_tilt"):
            raise AttributeError("SolarField.compute_poa_irradiance: coll_tilt has not been defined yet.")
            
        if not hasattr(self, "_coll_azimuth"):
            raise AttributeError("SolarField.compute_poa_irradiance: coll_azimuth has not been defined yet.")
            
        if ground_albedo is None and self._ground_albedo is None:
            ground_albedo = 0.2
        elif ground_albedo is None and self._ground_albedo is not None:
            ground_albedo = self._ground_albedo
        
        if dni_extra is None:
            dni_extra = 1366.1
            
        if diffuse_irradiance_model is None:
            diffuse_irradiance_model = 'perez'
        
        try:
            GHI = _to_array( GHI )
        except NonConvertibleToArray:
            TypeError("SolarField.compute_poa_irradiance: 'GHI' could not be interpreted as a number nor as an array.")
            
        try:
            DNI = _to_array( DNI )
        except NonConvertibleToArray:
            TypeError("SolarField.compute_poa_irradiance: 'DNI' could not be interpreted as a number nor as an array.")
            
        try:
            DHI = _to_array( DHI )
        except NonConvertibleToArray:
            TypeError("SolarField.compute_poa_irradiance: 'DHI' could not be interpreted as a number nor as an array.")
            
        try:
            solar_zenith = _to_array( apparent_solar_zenith )
        except NonConvertibleToArray:
            TypeError("SolarField.compute_poa_irradiance: 'apparent_solar_zenith' could not be interpreted as a number nor as an array.")
            
        try:
            solar_azimuth = _to_array( solar_azimuth )
        except NonConvertibleToArray:
            TypeError("SolarField.compute_poa_irradiance: 'solar_azimuth' could not be interpreted as a number nor as an array.")
        
        if type(diffuse_irradiance_model) is not str:
            raise TypeError("SolarField.compute_poa_irradiance: 'diffuse_irradiance_model' must be a string.")
        
        diffuse_irradiance_model = diffuse_irradiance_model.upper()
        
        if not diffuse_irradiance_model in [ 'PEREZ', 'ISOTROPIC' ]:
            raise TypeError("SolarField.compute_poa_irradiance: 'diffuse_irradiance_model' must be either 'perez' or 'isotropic'.")
            
        lengths = { len( x ) for x in [ GHI, DNI, DHI, solar_zenith, solar_azimuth ] if x is not None }
        if len( lengths ) != 1:
            raise ValueError("SolarCollector.compute_poa_irradiance: All arrays must have the same length.")
            
        array_length = lengths.pop()
        
        try:
            ground_albedo = _to_array( ground_albedo )
        except NonConvertibleToArray:
            TypeError("SolarField.compute_poa_irradiance: 'ground_albedo' could not be interpreted as a number nor as an array.")
        
        if len( ground_albedo ) == 1:
            ground_albedo = np.full( array_length, ground_albedo[0] )
        elif len( ground_albedo ) != array_length:
                ValueError("SolarField.compute_poa_irradiance: 'ground_albedo' must be either a single number or an array with the same length as the other ones.")
        
        if doy is not None:
            
            try:
                doy = _to_array( doy )
            except NonConvertibleToArray:
                TypeError("SolarField.compute_poa_irradiance: 'doy' could not be interpreted as a number nor as an array.")
            
            if len( doy ) != array_length:
                    ValueError("SolarField.compute_poa_irradiance: 'doy' must have the same length as the irradiance and solar position data.")
            
            dni_extra = get_extra_radiation( doy )
        
        else:
            
            try:
                dni_extra = _to_array( dni_extra )
            except NonConvertibleToArray:
                TypeError("SolarField.compute_poa_irradiance: 'dni_extra' could not be interpreted as a number nor as an array.")
            
            if len( dni_extra ) == 1:
                dni_extra = np.full( array_length, dni_extra[0] )
            elif len( dni_extra ) != array_length:
                    ValueError("SolarField.compute_poa_irradiance: 'dni_extra' must be either a single number or an array with the same length as the other ones.")
                    
        if np.min( GHI ) < 0:
            raise ValueError("SolarField.compute_poa_irradiance: GHI cannot be negative.")
        if np.min( DNI ) < 0:
            raise ValueError("SolarField.compute_poa_irradiance: DNI cannot be negative.")
        if np.min( DHI ) < 0:
            raise ValueError("SolarField.compute_poa_irradiance: DHI cannot be negative.")
        if not ( np.min( solar_zenith ) >= 0 and np.max( solar_zenith ) <= 180 ):
            raise ValueError("SolarField.compute_poa_irradiance: solar_zenith must be in the range 0 - 180.")
        if not ( np.min( solar_azimuth ) >= 0 and np.max( solar_azimuth ) < 360 ):
            raise ValueError("SolarField.compute_poa_irradiance: solar_azimuth must be in the range 0 - 360 (360 not included).")
    
        solar_zenith = ( np.pi/180 )*solar_zenith
        solar_azimuth = ( np.pi/180 )*solar_azimuth
        coll_tilt = ( np.pi/180 )*self._coll_tilt
        coll_azimuth = ( np.pi/180 )*self._coll_azimuth
        
        if diffuse_irradiance_model == 'ISOTROPIC':
            diff_isotropic = 0.5*( 1 + np.cos( coll_tilt ) )*np.maximum( DHI, 0 )
            diff_circumsolar = np.zeros( array_length )
            diff_horizon = np.zeros( array_length )
        else:
            relative_airmass = get_relative_airmass( solar_zenith, model = 'kastenyoung1989'  )
            diff_irradiance = perez( ( 180/np.pi )*coll_tilt,
                                     ( 180/np.pi )*coll_azimuth,
                                      DHI,
                                      DNI,
                                      dni_extra,
                                      ( 180/np.pi )*solar_zenith,
                                      ( 180/np.pi )*solar_azimuth,
                                      relative_airmass,
                                      model = 'allsitescomposite1990',
                                      return_components = True )
            
            try:
                diff_isotropic = diff_irradiance[ 'isotropic' ]
                diff_circumsolar = diff_irradiance['circumsolar']
                diff_horizon = diff_irradiance[ 'horizon' ]
            except KeyError:
                diff_isotropic = diff_irradiance[ 'poa_isotropic' ]
                diff_circumsolar = diff_irradiance['poa_circumsolar']
                diff_horizon = diff_irradiance[ 'poa_horizon' ]
            
            if self._clear_horizon is False:
                diff_horizon = np.zeros( array_length )
        
        aoi, longi, trans = self.compute_incidence_angles( ( 180/np.pi )*solar_zenith, ( 180/np.pi )*solar_azimuth )
        
        if self._tube_direction == 'HORIZONTAL':
            iam_beam = self._collector.compute_IAM( aoi = aoi, longi = trans, trans = np.abs( longi ) )
        else:
            iam_beam = self._collector.compute_IAM( aoi = aoi, longi = np.abs( longi ), trans = trans )
        
        aoi, longi, trans = ( np.pi/180 )*aoi, ( np.pi/180 )*longi, ( np.pi/180 )*trans
        
        beam = np.maximum( DNI + diff_circumsolar , 0 ) * np.cos( aoi )
        reflected = 0.5*( 1 - np.cos( coll_tilt ) )*ground_albedo*np.maximum( GHI, 0 )
        
        irradiance_first_row = beam + diff_isotropic + diff_horizon + reflected
        numerator = beam*iam_beam + self._diffuse_IAM[ 'isotropic_first_row' ]*diff_isotropic + self._diffuse_IAM[ 'horizon' ]*diff_horizon + self._diffuse_IAM[ 'ground' ]*reflected
        IAM_first_row = np.divide( numerator, irradiance_first_row, out = np.zeros_like(numerator, dtype=float), where = irradiance_first_row != 0 )
        
        irradiance_first_row[ np.isnan(irradiance_first_row) ] = 0
        IAM_first_row[ np.isnan(IAM_first_row) ] = 0
        
        if self._ground_fraction_covered is None:
            
            return irradiance_first_row, IAM_first_row, irradiance_first_row.copy(), IAM_first_row.copy()
        
        diff_isotropic_shadeable_rows = self._visible_sky_dome_fraction_shadeable_rows*diff_isotropic / ( 0.5*( 1 + np.cos( coll_tilt ) ) )
        
        F1 = ( np.cos( coll_tilt ) + np.sin( coll_tilt )*np.tan( longi ) )/self._ground_fraction_covered
        F2 = np.sin( coll_tilt ) * np.tan( trans )*( 1 - F1 )/( self.row_width_to_coll_length_ratio*self._ground_fraction_covered )
        shading_factor =  F1 + F2
        
        shading_factor = np.maximum( np.minimum( shading_factor, 1 ) , 0 )
        
        beam_shadeable_rows = beam*shading_factor
        
        irradiance_shadeable_rows = beam_shadeable_rows + diff_isotropic_shadeable_rows
        numerator = beam_shadeable_rows*iam_beam + self._diffuse_IAM[ 'isotropic_shadeable_rows' ]*diff_isotropic_shadeable_rows
        IAM_shadeable_rows = np.divide( numerator, irradiance_shadeable_rows, out = np.zeros_like(numerator, dtype=float), where = irradiance_shadeable_rows != 0 )
        
        irradiance_shadeable_rows[ np.isnan(irradiance_shadeable_rows) ] = 0
        IAM_shadeable_rows[ np.isnan(IAM_shadeable_rows) ] = 0
        
        return irradiance_first_row, IAM_first_row, irradiance_shadeable_rows, IAM_shadeable_rows
        
    def _compute_shadeable_rows_visible_sky_dome_fraction( self ):
        """
        Private method that computes an attribute of the object called '_visible_sky_dome_fraction_shadeable_rows'.
        
        This attribute corresponds to the fraction of a complete, half-spherical sky dome that is actually visible from a collector that has another collector in front of it, blocking a part of the sky.
        
        Since the visible fraction of the sky dome varies along the tilted direction of the collector, the value returned by this function is an average value.
        
        Returns
        -------
        float
            Visible sky dome fraction for a collector subject to self-shading.
        
        """
        
        if not hasattr(self, "_coll_tilt"):
            raise AttributeError("SolarField._compute_shadeable_rows_visible_sky_dome_fraction: coll_tilt has not been defined yet.")
        if not hasattr(self, "_ground_fraction_covered"):
            raise AttributeError("SolarField._compute_shadeable_rows_visible_sky_dome_fraction: ground_fraction_covered is not defined.")
            
        if self._ground_fraction_covered is None:
            self._visible_sky_dome_fraction_shadeable_rows = None
            return
            
        coll_tilt = ( np.pi/180 )*self.coll_tilt
            
        def visible_sky_fraction( x ):
            """
            Local function that computes the portion of the sky dome that is visible from a certain position of the solar collector, considering that another row is covering part of the sky.
            
            x = 0 corresponds to the upper part of the collector.
            
            x = 1 corresponds to the lower part of the collector.
            
            Parameters
            ----------
            x : float
                Number in the range 0 - 1 defining the position in the collector.

            Returns
            -------
            float
                Portion of the sky dome that is visible from the position of the collector defined by x.

            """
            delta = np.arctan( x*self._ground_fraction_covered*np.sin( coll_tilt )/( 1 - x*self._ground_fraction_covered*np.cos( coll_tilt ) ) )
            rho = coll_tilt + delta
            if rho >= np.pi/2:
                return ( 1 - np.cos( np.pi - rho ) )/2
            else:
                return ( 1 + np.cos( rho ) )/2
        
        self._visible_sky_dome_fraction_shadeable_rows = float( quad( visible_sky_fraction, 0, 1 )[0] )
        
    def compute_incidence_angles( self, solar_zenith, solar_azimuth ):
        """
        Method to compute the angles of incidence of direct irradiance from the solar position.
        
        The orientation of the solar field (coll_tilt, coll_azimuth) must be already defined.
        
        The values returned by this method are:
            
            - aoi: Angle of indicence with respect to a vector normal to the collector's plane.
            - longi: Longitudinal angle. It corresponds to the projection of aoi onto a plane that is normal to the collector's horizontal (i.e. non-tilted) sides.
            - trans: Transversal angle. It corresponds to the projection of aoi onto a plane that is normal to the collector's tilted sides.
        
        A subtlety needs to be clarified: The names 'longi' and 'trans' may suggest a relationship to the angles that are used to compute the IAM correction factor for tubular collectors.
        This is true, and it is the origin of the names that were given to these results.
        **Nevertheless, the names of the results returned by this method only match the transversal and longitudinal angles relative to a tubular collector when the tubes are tilted in the same direction as the collector.**
        When the tubes of the collector are horizontal, the values returned by this method must be swapped when used to call the method `SolarCollector.compute_IAM` factor.
        This is done internally by this class if the parameter `tube_direction` is set to `"horizontal"`.
        
        Parameters
        ----------
        solar_zenith : float or array-like
            Zenithal angle of the solar position (degree, °). Valid range: `0 <= solar_zenith <= 180`.
        solar_azimuth : float or array-like
            Azimuthal angle of the solar position (degree, °). Valid range: `0 <= solar_azimuth < 360`.
        
        Raises
        ------
        AttributeError
            If the attributes coll_tilt and coll_azimuth have not been defined yet.
        TypeError
            If the arguments cannot be interpreted as numbers or as arrays.
        ValueError
            If the arguments are outside of the allowed ranges.
        
        Returns
        -------
        aoi : float or np.array
            Angle of incidence (degree, °). See description of the method.
        longi : float or np.array
            Longitudinal angle of incidence (degree, °). See description of the method.
        trans : floar or np.array
            Transversal angle of incidence (degree, °). See description of the method.
        
        """
        
        if self._coll_tilt is None:
            raise AttributeError("SolarField._compute_rotation_matrix: Rotation matrix cannot be computed because coll_tilt is not defined.")
        if self._coll_azimuth is None:
            raise AttributeError("SolarField._compute_rotation_matrix: Rotation matrix cannot be computed because coll_azimuth is not defined.")
        
        try:
            solar_zenith = _to_array( solar_zenith )
        except NonConvertibleToArray:
            TypeError("SolarField.compute_incidence_angles: 'solar_zenith' could not be interpreted as a number nor as an array.")
            
        try:
            solar_azimuth = _to_array( solar_azimuth )
        except NonConvertibleToArray:
            TypeError("SolarField.compute_incidence_angles: 'solar_azimuth' could not be interpreted as a number nor as an array.")
        
        if len( solar_zenith ) != len( solar_azimuth ):
            raise ValueError("SolarField.compute_incidence_angles: Both arguments must have the same length.")
        
        if np.max( solar_zenith ) > 180 or np.min( solar_zenith ) < 0:
            raise ValueError("SolarField.compute_incidence_angles: 'solar_zenith' must be in the range 0 <= solar_zenith <= 180.")
        
        if np.max( solar_azimuth ) >= 360 or np.min( solar_azimuth ) < 0:
            raise ValueError("SolarField.compute_incidence_angles: 'solar_azimuth' must be in the range 0 <= solar_zenith < 360.")
        
        solar_N = np.cos( ( np.pi/180 )*solar_azimuth ) * np.sin( ( np.pi/180 )*solar_zenith )
        solar_E = np.sin( ( np.pi/180 )*solar_azimuth ) * np.sin( ( np.pi/180 )*solar_zenith )
        solar_Z = np.cos( ( np.pi/180 )*solar_zenith )
        
        vectors = np.stack([solar_N, solar_E, solar_Z], axis = 1)[:, :, np.newaxis]
        
        coll_coordinates = np.matmul( self._rotation_matrix, vectors )
        
        coll_N, coll_E, coll_Z = coll_coordinates[:, :, 0].T
        
        valid = coll_Z > 0
        north = coll_N > 0
        
        # Avoid division warnings where Z <= 0; those elements become NaN below.
        with np.errstate(divide="ignore", invalid="ignore"):
            trans = np.arctan( np.abs( coll_E ) / coll_Z )
            longi = np.arctan( np.abs( coll_N ) / coll_Z )
            
        coll_tilt_rad = ( np.pi/180 )*self._coll_tilt
     
        # Clip longi where it exceeds the limit and N > 0
        limit = np.pi / 2 - coll_tilt_rad
        longi = np.where( ( longi > limit ) & north, limit, longi )
     
        # Angle of incidence (computed after clipping, as in the original)
        tg2_aoi = np.tan( trans ) ** 2 + np.tan( longi ) ** 2
        aoi = np.arctan( np.sqrt( tg2_aoi ) )
     
        # Sign convention: negative longi when N > 0
        longi = np.where( north, -longi, longi )
     
        # Invalid elements (Z <= 0) -> NaN
        aoi = np.where( valid, aoi, np.nan )
        longi = np.where( valid, longi, np.nan )
        trans = np.where( valid, trans, np.nan )
        
        assert len( aoi ) == len( longi )
        assert len( aoi ) == len( trans )
        
        aoi = ( 180/np.pi )*aoi
        longi = ( 180/np.pi )*longi
        trans = ( 180/np.pi )*trans
        
        if len( aoi ) == 1:
            aoi = float( aoi[0] )
            longi = float( longi[0] )
            trans = float( trans[0] )
        
        return aoi, longi, trans
    
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
            raise TypeError("SolarField._validate_argument: Argument 'argument_name' must be a string.")
            
        if not argument_name in field_allowed_arguments:
            raise ValueError( f"SolarField: '{argument_name}' is not a valid argument." )
            
        if value is None:
            return None
        
        if argument_name == 'collector':
            if not isinstance( value, SolarCollector ):
                raise TypeError("SolarField: Argument 'collector' must be an instance of sercpy.solar.SolarCollector.")
        
        if argument_name == 'coll_tilt':
            try:
                value = float( value )
            except:
                raise TypeError("SolarField: Argument 'coll_tilt' must be converible to type 'float'.")
            if not ( value >= 0 and value <= 90 ):
                raise ValueError("SolarField: Argument 'coll_tilt' must be in the range 0 <= coll_tilt <= 90.")
                
        if argument_name == 'coll_azimuth':
            try:
                value = float( value )
            except:
                raise TypeError("SolarField: Argument 'coll_azimuth' must be converible to type 'float'.")
            if not ( value >= 0 and value < 360 ):
                raise ValueError("SolarField: Argument 'coll_azimuth' must be in the range 0 <= coll_azimuth < 360.")
        
        if argument_name in [ 'total_colls',
                              'coll_rows',
                              'colls_per_row',
                              'non_shadeable_rows',
                              'non_shadeable_colls',
                              ]:
            try:
                assert value.is_integer()
                value = int( value )
            except:
                raise ValueError(f"SolarField: Argument '{ argument_name }' must be an integer value.")
                
        if argument_name == 'ground_albedo':
            try:
                value = float( value )
            except:
                raise TypeError("SolarField: Argument 'ground_albedo' must be converible to type 'float'.")
            if not ( value >= 0 and value <= 1):
                raise TypeError("SolarField: Argument 'ground_albedo' must be in the range 0 <= ground_albedo <= 1.")
        
        if argument_name == 'coll_disposition':
            
            try:
                value = str(value).upper()
            except:
                raise TypeError("SolarField: Argument 'coll_disposition' must a string.")
            
            if not value in [ 'HORIZONTAL', 'VERTICAL', 'LANDSCAPE', 'PORTRAIT' ]:
                raise ValueError("SolarField: Argument 'coll_disposition' must be one of the strings: 'horizontal', 'vertical', 'landscape', or 'portrait'.")
        
        if argument_name == 'tube_direction':
            
            try:
                value = str(value).upper()
            except:
                raise TypeError("SolarField: Argument 'tube_direction' must a string.")
            
            if not value in [ 'HORIZONTAL', 'VERTICAL', 'TILTED' ]:
                raise ValueError("SolarField: Argument 'tube_direction' must be one of the strings: 'horizontal', 'vertical', or 'tilted'.")
        
        if argument_name in [ 'ground_fraction_covered', 'row_spacing' ]:
            try:
                value = float( value )
            except:
                raise TypeError(f"SolarField: Argument '{argument_name}' must be converible to type 'float'.")
            if not value > 0:
                raise TypeError(f"SolarField: Argument '{argument_name}' must be larger than zero.")
                
        if argument_name == 'row_mode':
            try:
                value = str(value).upper()
            except:
                raise TypeError("SolarField: Argument 'row_mode' must a string.")
            
            if not value in [ 'SERIES', 'PARALLEL' ]:
                raise ValueError("SolarField: Argument 'row_mode' must be one of the strings: 'series', or 'parallel'.")
                
        if argument_name == 'clear_horizon':
            try:
                value = bool(value)
            except:
                raise TypeError("SolarField: Argument 'clear_horizon' must be convertible to a boolean value.")
                
        if argument_name == 'release_vapor':
            try:
                value = bool( value )
            except:
                raise TypeError("SolarField: Argument 'release_vapor' must be convertible to a boolean value.")
        
        if argument_name == 'vapor_tolerance':
            try:
                value = float( value )
            except:
                raise TypeError("SolarField: Argument 'vapor_tolerance' must be converible to type 'float'.")
            if not ( value >= 1e-8 and value <= 1e-1 ):
                raise ValueError("SolarField: Argument 'vapor_tolerance' must be in the range 1e-8 <= vapor_tolerance <= 1e-1.")
                
        if argument_name == 'max_iterations':
            try:
                assert value.is_integer()
                value = int( value )
            except:
                raise TypeError("SolarField: Argument 'max_iterations' must be an integer value.")
                
            if not ( value >= 3 and value <= 300 ):
                raise ValueError("SolarField: Argument 'max_iterations' must be in the range 3 <= max_iterations <= 300.")
        
        return value
    
    def _compute_diffuse_IAM( self ):
        """
        Private method that computes an attribute of the object called '_diffuse_IAM'.
        
        This attribute is a dictionary that stores the IAM correction value associated to each diffuse irradiance component.
        
        The dictionary has the following components:
            
            - 'isotropic_first_row': Correction factor for the collectors that are not subject to self-shading, associated to isotropic diffuse irradiance.
            - 'isotropic_shadeable_rows': Correction factor for the collectors that are subject to self-shading, associated to isotropic diffuse irradiance. This component is only computed is the attribute 'ground_fraction_covered' has been provided at initialization, either directly or through the arguments 'row_spacing' and 'coll_disposition'.
            - 'ground': Correction factor associated to ground-reflected irradiance. It only applies to the non-shadeable collectors.
            - 'horizon': Correction factor associated to horizon diffuse irradiance. It only applies to the non-shadeable collectors.
        
        Raises
        ------
        Exception
            When the attribute _coll_tilt has not been defined.
        
        Returns
        -------
        None
        
        """
        if not hasattr( self, "_coll_tilt" ):
            raise Exception("SolarField._compute_diffuse_IAM: coll_tilt has not been defined yet.")
        
        arrays_length = 30
        trans_array = np.linspace( 0, 90, arrays_length )
        longi_array = np.linspace( 0, 90, arrays_length )
        
        TRANS, LONGI = np.meshgrid(trans_array, longi_array, indexing="ij")
        TRANS_flat = TRANS.ravel()
        LONGI_flat = LONGI.ravel()
        
        IAM_array_flat = self._collector.compute_IAM( trans = TRANS_flat, longi = LONGI_flat )
        
        IAM_array = IAM_array_flat.reshape(TRANS.shape)
        
        trans_array = ( np.pi/180 )*trans_array
        longi_array = ( np.pi/180 )*longi_array
        
        interpolator = RegularGridInterpolator(
            
            (trans_array, longi_array), IAM_array, method = "linear", bounds_error = False, fill_value = np.nan )
        
        def IAM_func(theta, phi):
            
            trans = np.arctan( np.tan( theta ) * np.sin( phi ) )
            longi = np.arctan( np.tan( theta ) * np.cos( phi ) )
            
            if self._tube_direction == 'HORIZONTAL':
                trans, longi = longi, trans
                
            return interpolator( [ trans, longi ] )[0]
        
        def function_to_integrate(theta, phi, mode):
            if mode == 'numerator':
                return IAM_func( theta, phi )*np.cos( theta )*np.sin( theta )
            if mode == 'denominator':
                return np.cos(theta)*np.sin(theta)
            
        coll_tilt_rad = ( np.pi / 180 ) * self._coll_tilt
        
        def integration_limit_first_row( phi ):
            return np.arctan( np.tan( np.pi/2 - coll_tilt_rad )/np.cos( phi ) )
        
        
        self._diffuse_IAM = {}
        if self._coll_tilt == 0 or self._coll_tilt == 90:
            numerator = _dblquad( function_to_integrate, 0, np.pi/2, 0, np.pi/2, args = ('numerator',) )
            denominator = _dblquad( function_to_integrate, 0, np.pi/2, 0, np.pi/2, args = ('denominator',) )
            self._diffuse_IAM[ 'isotropic_first_row' ] = numerator/denominator
            self._diffuse_IAM[ 'ground' ] = (self._coll_tilt == 90)*numerator/denominator
        else:
            numerator_sky_1 = _dblquad( function_to_integrate, 0, np.pi/2, 0, np.pi/2, args = ('numerator',) )
            denominator_sky_1 = _dblquad( function_to_integrate, 0, np.pi/2, 0, np.pi/2, args = ('denominator',) )
            numerator_sky_2 = _dblquad( function_to_integrate, 0, np.pi/2, 0, integration_limit_first_row, args = ('numerator',) )
            denominator_sky_2 = _dblquad( function_to_integrate, 0, np.pi/2, 0, integration_limit_first_row, args = ('denominator',) )
            numerator_ground = _dblquad( function_to_integrate, 0, np.pi/2, integration_limit_first_row, np.pi/2, args = ('numerator',) )
            denominator_ground = _dblquad( function_to_integrate, 0, np.pi/2, integration_limit_first_row, np.pi/2, args = ('denominator',) )
            self._diffuse_IAM[ 'isotropic_first_row' ] = (numerator_sky_1 + numerator_sky_2)/(denominator_sky_1 + denominator_sky_2)
            self._diffuse_IAM[ 'ground' ] = numerator_ground/denominator_ground
            
        if self._ground_fraction_covered is not None:
            
            delta_rad = np.arctan( self._ground_fraction_covered*np.sin( coll_tilt_rad )/( 2 - self._ground_fraction_covered*np.cos( coll_tilt_rad ) ) )
            if coll_tilt_rad + delta_rad >= np.pi/2:
                def integration_limit_shadeable_rows( phi ):
                    return np.arctan( np.tan( coll_tilt_rad + delta_rad - np.pi/2 )/np.cos( phi ) )
                numerator_sky = _dblquad( function_to_integrate, 0, np.pi/2, integration_limit_shadeable_rows, np.pi/2, args = ('numerator',) )
                denominator_sky = _dblquad( function_to_integrate, 0, np.pi/2, integration_limit_shadeable_rows, np.pi/2, args = ('denominator',) )
                self._diffuse_IAM[ 'isotropic_shadeable_rows' ] = numerator_sky/denominator_sky
            else:
                def integration_limit_shadeable_rows( phi ):
                    return np.arctan( np.tan( np.pi/2 - coll_tilt_rad - delta_rad )/np.cos( phi ) )
                numerator_sky_1 = _dblquad( function_to_integrate, 0, np.pi/2, 0, np.pi/2, args = ('numerator',) )
                denominator_sky_1 = _dblquad( function_to_integrate, 0, np.pi/2, 0, np.pi/2, args = ('denominator',) )
                numerator_sky_2 = _dblquad( function_to_integrate, 0, np.pi/2, 0, integration_limit_shadeable_rows, args = ('numerator',) )
                denominator_sky_2 = _dblquad( function_to_integrate, 0, np.pi/2, 0, integration_limit_shadeable_rows, args = ('denominator',) )
                self._diffuse_IAM[ 'isotropic_shadeable_rows' ] = (numerator_sky_1 + numerator_sky_2)/(denominator_sky_1 + denominator_sky_2)
            
        if self._coll_tilt == 90:
            def function_to_integrate(theta, mode):
                phi = np.pi/2
                if mode == 'numerator':
                    return IAM_func(theta, phi)*np.cos(theta)*np.sin(theta)
                if mode == 'denominator':
                    return np.cos(theta)*np.sin(theta)
            numerator = quad( function_to_integrate, 0, np.pi/2, args = ('numerator',), epsabs = 1e-3, limit = 200, epsrel = 1e-3 )[0]
            denominator = quad( function_to_integrate, 0, np.pi/2, args = ('denominator',), epsabs = 1e-3, limit = 200, epsrel = 1e-3 )[0]
            self._diffuse_IAM[ 'horizon' ] = numerator/denominator
        elif self._coll_tilt == 0:
            self._diffuse_IAM[ 'horizon' ] = 0
        else:
            def function_to_integrate(phi, mode):
                theta = np.arctan( np.tan( np.pi/2 - coll_tilt_rad )/np.cos( phi ) )
                if mode == 'numerator':
                    return IAM_func(theta, phi)*np.cos(theta)*np.sin(theta)
                if mode == 'denominator':
                    return np.cos(theta)*np.sin(theta)
            numerator = quad( function_to_integrate, 0, np.pi/2, args = ('numerator',), epsabs = 1e-3, limit = 200, epsrel = 1e-3 )[0]
            denominator = quad( function_to_integrate, 0, np.pi/2, args = ('denominator',), epsabs = 1e-3, limit = 200, epsrel = 1e-3 )[0]
            self._diffuse_IAM[ 'horizon' ] = numerator/denominator
            
    def _compute_row( self, flowrate_in, state_in, Tmains, irradiance, IAM_factor, Tamb, flowrate_correction_factor ):
        """
        Function that computes the power of a collector row and returns the state of the fluid leaving it.
        
        Parameters
        ----------
        flowrate_in : float
            Mass flowrate entering the collector row (kg/s).
        
        state_in : sercpy.fluids.FluidState
            State of the fluid as it enters the collector row.
        
        Tmains : float
            Mains water temperature (°C). This parameter is only used is water boiling and replacement from the distribution network is simulated by the solar field model.
        
        irradiance : float
            Solar irradiance on the collectors' plane (W/m2).
        
        IAM_factor : float
            Dimensionless quantity defining the correction factor associated to IAM (Incidence Angle Modifier).
            
        Tamb : float
            Ambient temperature (°C).
            
        flowrate_correction_factor : float
            Dimensionless quantity defining the correction factor associated to the flowrate.
        
        Returns
        -------
        state_out : sercpy.fluids.FluidState
            State of the fluid leaving the collector row.
            
        Q_wasted : float
            Power being used to evaporate the water that is entering the collector row from the distribution network (W). Only larger than zero if boiling occurs.
            
        vapor_flowrate : float
            Mass flowrate of vapor being released due to overheating (kg/s). Except for tolerance-associated errors, it is the same as the flow that enters the collector row from the distribution network.
        
        it : int
            Number of iterations carried out.
        
        convergence : bool
            Whether convergence between the flowrate entering the collector row from the distribution network and the vapor flowrate being released due to overheating was achieved.
        
        """
        fluid = state_in.fluid
        
        if self._release_vapor and fluid.can_boil:
            
            if Tmains is None:
                raise ValueError("SolarField: Tmains cannot be None if 'release_vapor' has been set to 'True' at initialization.")
            
            h_in = state_in.h
            h_mains = fluid.state( T = Tmains ).h
            
            flowrate_mains = 0
            it = 0
            while True:
                flowrate_mix = flowrate_in + flowrate_mains
                h_mix_init = ( flowrate_in*h_in + flowrate_mains*h_mains )/flowrate_mix
                
                mixture_state = fluid.state( h = h_mix_init )
                
                if self._row_mode == 'SERIES':
                    for i in range( self._colls_per_row ):
                        mixture_state = self._collector.compute_outlet_state(flowrate_mix, mixture_state, irradiance, IAM_factor, Tamb, flowrate_correction_factor)
                else:
                    mixture_state = self._collector.compute_outlet_state( flowrate_mix / self._colls_per_row , mixture_state, irradiance, IAM_factor, Tamb, flowrate_correction_factor)
                
                vapor_flowrate = mixture_state.Q*flowrate_mix
                
                it = it + 1
                if flowrate_mains == vapor_flowrate or abs(flowrate_mains - vapor_flowrate)/max([ flowrate_mains, vapor_flowrate ]) < self._vapor_tolerance:
                    maxIt = False
                    break
                if it == self._max_iterations:
                    maxIt = True
                    break
                if flowrate_mains > 0 and vapor_flowrate == 0:
                    vapor_flowrate = 0.5*vapor_flowrate
                else:
                    assert mixture_state.h > fluid.h_sat_liq
                    Q_useful = flowrate_in*( fluid.h_sat_liq - h_in )
                    Q_actual = flowrate_mix*( mixture_state.h - h_mix_init )
                    Q_waste = Q_actual - Q_useful
                    flowrate_mains = Q_waste/( fluid.h_sat_vap - h_mains )
            if vapor_flowrate > 0:
                return fluid.state( h = fluid.h_sat_liq ), vapor_flowrate*( fluid.h_sat_vap - h_mains ), vapor_flowrate, it, not maxIt
            else:
                return mixture_state, 0, 0, it, not maxIt
        
        else:
            
            fluid_state = state_in
            if self._row_mode == 'SERIES':
                for i in range(self._colls_per_row):
                    fluid_state = self._collector.compute_outlet_state( flowrate_in, fluid_state, irradiance, IAM_factor, Tamb, flowrate_correction_factor )
            else:
                fluid_state = self._collector.compute_outlet_state( flowrate_in / self._colls_per_row , fluid_state, irradiance, IAM_factor, Tamb, flowrate_correction_factor )
            return fluid_state, 0, 0, 0, True
        
    def set_connections( self, *, inlet ):
        """
        Method to specify the device to which the solar field's flow inlet is connected.
        
        The single argument of this method has to be an instance of `sercpy.devices.Outlet`, which is expected to belong to another device of the thermal system.
        
        Parameters
        ----------
        inlet : sercpy.devices.Outlet
            Outlet from which the flowrate that enters the solar field comes.
        
        Returns
        -------
        None.
        
        """
        if not isinstance( inlet, Outlet ):
            raise ValueError("SolarField.set_inputs: 'outlet' must be an instance of sercpy.devices.Outlet.")
        
        self._inlet = inlet
    
    def set_convergence_criteria( self, *,
                                  relative_tolerance: float,
                                  temp_tolerance: Optional[ float ] = None,
                                  h_tolerance: Optional[ float ] = None,
                                  temp_normalization_range: Optional[ float ] = None,
                                  h_normalization_range: Optional[ float ] = None ):
        """
        Establish the convergence criteria of the `SolarField` instance in the context of a simulation.
        
        When used in the context of a simulation, a `SolarField` instance determines that "input convergence" has been achieved when the inputs received by it in consecutive iterations of the same time step differ in less that a certain margin.
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
            Maximum relative difference allowed for all input types except temperature and specific enthalpy. In the case of the `SolarField`
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
            raise TypeError("SolarField.set_convergence_criteria: 'relative_tolerance' must be convertible to type 'float'.")
        
        self._relative_tolerance = relative_tolerance
        
        if sum( [ variable is not None for variable in [ 
                
                temp_tolerance,
                h_tolerance,
                temp_normalization_range,
                h_normalization_range,
                
                ] ] ) != 1:
            
            raise ValueError("SolarField.set_convergence_criteria: One and only one of the optional arguments must be provided: 'temp_tolerance', 'h_tolerance', 'temp_normalization_range', 'h_normalization_range'.")
        
        if all([ variable is None for variable in [ temp_tolerance, temp_normalization_range, h_tolerance, h_normalization_range ] ]):
            raise ValueError("SolarField.set_convergence_criteria: At least one of the following arguments must be provided: 'temp_tolerance', 'temp_normalization_range', 'h_tolerance', 'h_normalization_range'.")
        
        elif temp_tolerance is not None and temp_normalization_range is not None:
            raise ValueError("SolarField.set_convergence_criteria: Arguments 'temp_tolerance' and 'temp_normalization_range' cannot be provided together.")
        
        elif h_tolerance is not None and h_normalization_range is not None:
            raise ValueError("SolarField.set_convergence_criteria: Arguments 'h_tolerance' and 'h_normalization_range' cannot be provided together.")
            
        if temp_tolerance is not None:
            try:
                temp_tolerance = float( temp_tolerance )
            except:
                raise TypeError("SolarField.set_convergence_criteria: 'temp_tolerance' must be convertible to type 'float'.")
            self._temp_tolerance = temp_tolerance
            
        elif temp_normalization_range is not None:
            try:
                temp_normalization_range = float( temp_normalization_range )
            except:
                raise TypeError("SolarField.set_convergence_criteria: 'temp_normalization_range' must be convertible to type 'float'.")
            self._temp_tolerance = relative_tolerance*temp_normalization_range
        
        else:
            self._temp_tolerance = None
        
        if h_tolerance is not None:
            try:
                h_tolerance = float( h_tolerance )
            except:
                raise TypeError("SolarField.set_convergence_criteria: 'h_tolerance' must be convertible to type 'float'.")
            self._h_tolerance = h_tolerance
        elif h_normalization_range is not None:
            try:
                h_normalization_range = float( h_normalization_range )
            except:
                raise TypeError("SolarField.set_convergence_criteria: 'h_normalization_range' must be convertible to type 'float'.")
            self._h_tolerance = relative_tolerance*h_normalization_range
        
        else:
            self._h_tolerance = None
        
        if self._temp_tolerance is not None and not ( self._temp_tolerance >= 1e-5 and self._temp_tolerance <= 1 ):
            raise ValueError(f"SolarField.set_convergence_criteria: 'temp_tolerance' value ( equal to {self._temp_tolerance} ) is out of the allowed range: 1e-5 to 1.")
        
        if self._h_tolerance is not None and not ( self._h_tolerance >= 1e-2 and self._h_tolerance <= 5000 ):
            raise ValueError(f"SolarField.set_convergence_criteria: 'h_tolerance' value ( equal to {self._h_tolerance} ) is out of the allowed range: 1e-2 to 5000.")
            
    def _set_last_inputs( self, flowrate, state_in ):
        """
        Method that updates the last inputs received by the SolarField instance. These attributes are then used to evaluate the whether input convergence is achieved.

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
        
        self._flowrate_last = flowrate
        self._state_in_last = state_in
        
    def _compute_convergence(self, flowrate, state_in ):
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
        if flowrate == 0 or self._flowrate_last == 0:
            convergence = convergence and flowrate == self._flowrate_last
        elif flowrate != self._flowrate_last:
            convergence = convergence and abs( flowrate - self._flowrate_last ) / min( [ flowrate  , self._flowrate_last ] ) <= self._relative_tolerance
        
        if self._h_tolerance is not None:
            convergence = convergence and abs( state_in.h - self._state_in_last.h ) <= self._h_tolerance
        
        if self._temp_tolerance is not None:
            convergence = convergence and abs( state_in.T - self._state_in_last.T ) <= self._temp_tolerance
            
        self._input_convergence = convergence

    def compute_outputs( self, operating_conditions = None, iteration_number = None, *,
                         state_in = None, flowrate = None,
                         GHI = None, DNI = None, DHI = None,
                         solar_apparent_zenith = None, solar_azimuth = None, 
                         Tamb = None, Tmains = None,
                         doy = None ):
        """
        Method to compute the outputs of the solar field.
        
        The following attributes of the `SolarField` instance are updated when this method is called (unless input convergence is achieved; in that case only that attribute is updated):
            
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
        if operating_conditions is None and iteration_number is None:
            if any([ variable is None for variable in [ state_in, flowrate, GHI, DNI , DHI, solar_apparent_zenith, solar_azimuth, Tamb, Tmains ] ]):
                raise TypeError("SolarField.compute_outputs: Not all arguments needed for manual mode were provided. Arguments needed: state_in, flowrate, GHI, DNI , DHI, solar_apparent_zenith, solar_azimuth,  Tamb, Tmains.")
            
            self._input_convergence = False
                
            irradiance_first_row, IAM_first_row, irradiance_shadeable_rows, IAM_shadeable_rows = self.compute_poa_irradiance( GHI, DNI, DHI, solar_apparent_zenith, solar_azimuth, doy = doy,  )
            
            operating_conditions = {
                
                'irradiance_first_row': irradiance_first_row,
                'irradiance_shadeable_rows': irradiance_shadeable_rows,
                'IAM_first_row': IAM_first_row,
                'IAM_shadeable_rows': IAM_shadeable_rows,
                'Tamb': Tamb,
                'Tmains': Tmains,
                
                }
            
        elif operating_conditions is None or iteration_number is None:
            raise TypeError("SolarField.compute_outputs: Both 'operating_conditions' and 'operating_conditions' must be provided in simulation mode. None of them must be provided in manual mode.")
        
        else:
            
            if type( operating_conditions ) is not dict:
                raise TypeError("SolarField.compute_outputs: Argument 'operating_conditions' must be a dictionary.")
            if not ( type( iteration_number ) is int and iteration_number >= 0 ):
                raise TypeError("SolarField.compute_outputs: Argument 'iteration_number' must be an 'int'. Its value msut be >= 0.")
            
            try:
                flowrate = self._inlet.flowrate
                state_in = self._inlet.state
            except AttributeError:
                self._input_convergence = False
                return
            
            if iteration_number == 0:
                self._set_last_inputs(flowrate, state_in)
                self._input_convergence = False
            else:
                self._compute_convergence(flowrate, state_in)
                if self._input_convergence:
                    return
                else:
                    self._set_last_inputs(flowrate, state_in)
        
        if flowrate == 0:
            self._outlet.flowrate = 0
            self._outlet.state = state_in
            self._useful_power = 0
            self._wasted_power = 0
            self._vapor_flowrate = 0
            self._efficiency = np.nan
            self._iterations = 0
            self._vapor_release_convergence = True
            return
        
        try:
            irradiance_first_row = operating_conditions[ 'irradiance_first_row' ]
            irradiance_shadeable_rows = operating_conditions[ 'irradiance_shadeable_rows' ]
            IAM_first_row = operating_conditions[ 'IAM_first_row' ]
            IAM_shadeable_rows = operating_conditions[ 'IAM_shadeable_rows' ]
        except:
            raise KeyError("SolarField.compute_outputs: Irradiance data could not be retrieved from 'operating_conditions'. Maybe you forgot to call the method 'MeteoProfile.compute_poa_irradiance'. After this, redefine the instance of `OperatingConditions` for the change to be applied.")
        
        try:
            Tamb = operating_conditions[ 'Tamb' ]
            Tmains = operating_conditions[ 'Tmains' ]
        except:
            raise KeyError("Ambient temperature and mains water temperature could not be extracted from 'operating_conditions'.")
        
        flowrate_each_row = flowrate / self._coll_rows
        fluid = state_in.fluid
        
        if self._row_mode == 'PARALLEL':
            flowrate_each_collector = flowrate_each_row / self._colls_per_row
        else:
            flowrate_each_collector = flowrate_each_row
            
        flowrate_correction_factor = self._collector.compute_flowrate_correction_factor( fluid, flowrate_each_collector )
        
        # Suffix "NS" for NON-shadeable rows
        if irradiance_first_row > 0:
            state_out_NS, Q_waste_NS, vap_flow_NS, iterations_NS, convergence_NS = self._compute_row( flowrate_each_row, state_in, Tmains, irradiance_first_row, IAM_first_row, Tamb, flowrate_correction_factor )
        else:
            state_out_NS = state_in.h
            Q_waste_NS = 0
            vap_flow_NS = 0
            iterations_NS = 1
            convergence_NS = True
        
        # Suffix "Sh" for shadeable rows
        if irradiance_shadeable_rows > 0:
            state_out_Sh, Q_waste_Sh, vap_flow_Sh, iterations_Sh, convergence_Sh = self._compute_row(flowrate_each_row, state_in, Tmains, irradiance_shadeable_rows, IAM_shadeable_rows, Tamb, flowrate_correction_factor)
        else:
            state_out_Sh = state_in.h
            Q_waste_Sh = 0
            vap_flow_Sh = 0
            iterations_Sh = 1
            convergence_Sh = True
        
        h_out = ( state_out_NS.h*self._non_shadeable_rows + state_out_Sh.h*self._shadeable_rows ) / self._coll_rows
        
        if fluid.can_boil:
            state_out = fluid.state( h = min ( [ h_out, fluid.h_sat_liq ] ) )
        else:
            state_out = fluid.state( h = h_out )
        
        Q_useful = max( [ flowrate*( h_out - state_in.h ) , 0 ] )
        Q_waste  = max( [ Q_waste_NS*self._non_shadeable_rows + Q_waste_Sh*self._shadeable_rows , 0 ] )
        vapor_flowrate = vap_flow_NS*self._non_shadeable_rows + vap_flow_Sh*self._shadeable_rows
        
        if irradiance_first_row <= 0:
            efficiency = np.nan
        else:
            efficiency = Q_useful/( irradiance_first_row*self._collector.area*self._coll_rows*self._colls_per_row )
        
        total_iterations = iterations_NS + iterations_Sh
        vapor_release_convergence = convergence_NS and convergence_Sh
        
        self._outlet.state = state_out
        self._outlet.flowrate = flowrate
        
        self._useful_power = Q_useful
        self._wasted_power = Q_waste
        self._vapor_flowrate = vapor_flowrate
        self._efficiency = efficiency
        self._iterations = total_iterations
        self._vapor_release_convergence = vapor_release_convergence
    
def example_solar_field( field_gross_area, latitude = None, ):
    """
    Function that takes one of two arguments and returns a generic instance of the class `SolarField`.
    
    Parameters
    ----------
    field_gross_area : float
        Desired area for the solar field. Minimum value: 10.
    latitude : float, optional
        If provided, the orientation of the solar collector (tilt and azimuth) is set based on this value. The default is None.

    Returns
    -------
    solar_field : SolarField
        Generic instance of the class SolarField.

    """
    
    coll_area = 2
    n0 = 0.75
    a1 = 3.6
    a2 = 0.01
    coll_IAM = 0.05
    
    if field_gross_area < 10:
        raise ValueError( "example_solar_field: field_gross_area cannot be less than 10." )
    
    if latitude is not None:
        coll_tilt = abs( latitude )
        if latitude >= 0:
            coll_azimuth = 180
        else:
            coll_azimuth = 0
    
    else:
        coll_tilt = None
        coll_azimuth = None
        
    collector = SolarCollector(
        
        area = coll_area,
        n0 = n0,
        a1 = a1,
        a2 = a2,
        IAM = coll_IAM,
        
        )
    
    n_colls = field_gross_area // coll_area
    
    solar_field = SolarField(
        
        collector = collector,
        coll_tilt = coll_tilt,
        coll_azimuth = coll_azimuth,
        total_colls = n_colls,
        
        )
    
    return solar_field
    