# -*- coding: utf-8 -*-
"""
Created on Thu Sep 24 09:42:44 2026

@author: Adrian Riebel Brummer
"""

from typing import Optional
import numpy as np
from .fluids import Fluid
from .devices import Outlet
import warnings
from math import log, exp

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

class SolarCollector:
    """
    Class that stores the features (area, parameters of the efficiency curve, etc.) of a solar thermal collector.
    
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
        First order (linear) loss coefficient (W/m2 K).
    
    a2 : float, optional
        Second order (quadratic) loss coefficient (W/m2 K2). If not provided, it is assumed to be null.
    
    IAM : float, list, or dict
        Object specifying the shape of the IAM (Incidence Angle Modifier) curve. See :doc:`IAM </solar/IAM>` to learn the possible formats of this parameter.
    
    test_flowrate_per_m2 : float, optional
        Flowrate per area unit with wich the collector has been tested (kg/m2 s). It is used to correct the efficiency of the collector considering the operation flowrate. If not provided, its value is assumed to be 0.02.
    
    test_fluid : sercpy.fluids.Fluid or str, optional
        Instance of :doc:`Fluid </fluids/fluid_class>`, or a valid name to initialize an instance of this class. If not provided, 'water' is assumed.
    
    Attributes
    ----------
    model_name : str
        String identifying the collector model.
    
    area : float
        Area of the collector. If not provided by the user as initialization argument, it is computed from `length` and `width`.
    
    length : float
        Long side of the collector (m). Only available if enough data is provided at initialization.
    
    width : float
        Short side of the collector (m). Only available if enough data is provided at initialization.
    
    n0 : float
        Adimensional value in the range 0.1 - 0.99 identifying the intercept efficiency, sometimes referred to as 'optical efficiency'. 
    
    a1 : float
        First order (linear) loss coefficient (W/m2 K).
    
    a2 : float
        Second order (quadratic) loss coefficient (W/m2 K2).
    
    IAM : float, list, or dict
        Object specifying the shape of the IAM (Incidence Angle Modifier) curve. See :doc:`IAM </solar/IAM>` to learn the possible formats of this parameter.
    
    test_flowrate_per_m2 : float
        Flowrate per area unit with wich the collector has been tested (kg/m2 s).
    
    test_fluid : sercpy.fluids.Fluid
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
                 IAM: float | list | dict,
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
            raise ValueError("SolarCollector: Length and width must be provided if area is not provided.")
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
            
    @property
    def model_name(self):
        return self._model_name
            
    @property
    def area(self):
        return self._area
    
    @property
    def length(self):
        return self._length
    
    @property
    def width(self):
        return self._width
    
    @property
    def n0(self):
        return self._n0
    
    @property
    def a1(self):
        return self._a1
    
    @property
    def a2(self):
        return self._a2
    
    @property
    def IAM(self):
        return self._IAM
    
    @property
    def test_flowrate_per_m2(self):
        return self._test_flowrate_per_m2
    
    @property
    def test_fluid(self):
        return self._test_fluid
    
    def _validate_argument( self, argument_name, value ):
        
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
            if not ( value >= 0.01 and value <= 100 ):
                raise ValueError("SolarCollector: Argument 'a1' is out of the allowed range: 0.01 <= a1 <= 100.")
                
        if argument_name == 'a2':
            try:
                value = float( value )
            except:
                raise TypeError("SolarCollector: Argument 'a2' must be convertible to type 'float'.")
            if not value >= 0:
                raise ValueError("SolarCollector: Argument 'a2' must be >= 0.")
                
        if argument_name == 'IAM':
            
            if type( value ) in [ list, np.ndarray ]:
                
                try:
                    assert len( value ) == 10
                    value = [ float(v) for v in value ]
                    assert all( [ v >= 0 and v <= 1 for v in value ] )
                    assert value[0] == 1 and value[9] == 0
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
                            assert len( IAM_list ) == 10
                            IAM_list = [ float(v) for v in IAM_list ]
                            assert all( [ v >= 0 and v <= 1 for v in IAM_list ] )
                            assert IAM_list[0] == 1 and IAM_list[9] == 0
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

field_allowed_arguments = [
    
    "collector",
    "coll_tilt",
    "coll_azmiuth",
    "total_colls",
    "coll_rows",
    "colls_per_row",
    "coll_disposition",
    "tube_direction",
    "non_shadeable_rows",
    "non_shadeable_colls",
    "ground_fraction_covered",
    "row_spacing",
    "row_mode",
    "release_vapor",
    "tolerance",
    "max_iterations",
    
    ]

class SolarField:
    """
    Class that models a solar collector field.
    
    Parameters
    ----------
    collector : SolarCollector
        `sercpy.solar.SolarCollector` instance defining the features of each individual collector of the field.
    
    coll_tilt : float, optional
        Tilt angle of each collector with respect to the ground. If not provided, it will be set automatically by a `MeteoProfile` instance when the method `compute_poa_irradiance` gets called using the `SolarField` instance.
    
    coll_azmiuth : float, optional
        Azimuthal angle of the collectors with respect to the ground. If not provided, it will be set automatically by a `MeteoProfile` instance when the method `compute_poa_irradiance` gets called using the `SolarField` instance.
    
    total_colls : int, optional
        Number of collectors that make up the solar field. If not provided, it can be computed as `coll_rows*colls_per_row`.
    
    coll_rows : int, optional
        Number of collector groups that make up the solar field. This parameter only matters for the model's results if the argument `row_mode` is set to `"series"`, or if the argument `non_shadeable_rows` is provided. If not provided, its value can be determined as `total_cols/colls_per_row` (this result must be an integer).
    
    colls_per_row : int, optional
        Number of collectors making up each collector row. This parameter only matters for the model's results if the argument `row_mode` is set to `"series"`, or if the argument `non_shadeable_rows` is provided. If not provided, its value can be determined as `total_cols/coll_rows` (this result must be an integer).
        
    row_mode : str, optional
        Parameter defining whether the collectors in a row are arranged in series or in parallel. Possible values for this argument: `"series"`, `"parallel"`.
        If arranged in series (common for heat pipe evacuated tube collectors), the heat transfer fluid passes from one collector to another one, entering each one of them with the temperature it left the previous one with.
        If arranged in parallel (common for flat plate collectors), the heat transfer fluid flow gets equally distributed among all the collectors, entering all of them with the same temperature. In the latter case, it is actually not mandatory to specify `coll_rows` or `colls_per_row`, since the number of collectors per row only makes a difference when they are arranged in series.
        The default value for this parameter is `"parallel"`.
    
    coll_disposition : str, optional
        String identifying whether the tilted side of the collector is the short side or the long side. The former case can be identified with the strings 'horizontal' and 'landscape'. The latter case can be identified with the strings 'vertical' and 'portrait'.
    
    tube_direction : str, optional
        This parameter only makes a difference for collectors that have biaxial IAM (Incidence Angle Modifier) functions, which in most cases are evacuated tube collectors.
        This parameter can have the values 'vertical' and 'horizontal'. In the former case, the tubes point towards the ground (not perpendicularly; the angle depends on the tilt of the collector), whereas in the latter case, the tubes are parallel to the ground. 
    
    non_shadeable_rows : int, optional
        Number of collector rows that are not subject to self-shading. Note that more than one collector row may be in the front o the collector field, since a collector row may be defined as a group of collectors connected in series (see the argument `row_mode`).
    
    non_shadeable_colls : int, optional
        Number of collectors that are not subject to self-shading. If the number of collectors per row has been specified, this argument must be equivalent to an entire number of rows (i.e. `non_shadeable_colls/colls_per_row` must be a whole number). This argument is useful when the number of rows is not being taken into account.
    
    ground_fraction_covered : float, optional
        Ratio between the tilted side of the solar collectors and the row spacing between them. This parameter is relevant for modeling of self-shading. This value can be computed internally if the attributes `length` and `width` of the object `collector` have been correctly defined, and if the arguments `coll_disposition` and `row_spacing` are provided for this class.
    
    row_spacing : float, optional
        Distance between collector rows (m). 
    
    release_vapor : bool, optional
        If this parameter is set to `True`, the vapor produced when the saturation temperature of the heat transfer fluid is achieved will be released and replaced with water from the distribution network. This mode is only available when water is used as heat transfer fluid. This parameter defaults to `True`.
    
    tolerance : float, optional
        Only relevant of `release_vapor` is set to `True`. This argument defines the relative difference allowed between the vapor flowrate being released and the water flowrate being introduced from the distribution network to replace it. Allowed range: 1e-8 - 1e-1. If not provided, it defaults to 1e-3.
    
    max_iterations : int, optional
        Maximum number of iterations allowed when computing the vapor being released due to boiling of the heat transfer fluid.
    
    Attributes
    ----------
    model_name : str
        String identifying the collector model.
    
    area : float
        Area of the collector. If not provided by the user as initialization argument, it is computed from `length` and `width`.
    
    length : float
        Long side of the collector (m). Only available if enough data is provided at initialization.
    
    width : float
        Short side of the collector (m). Only available if enough data is provided at initialization.
    
    n0 : float
        Adimensional value in the range 0.1 - 0.99 identifying the intercept efficiency, sometimes referred to as 'optical efficiency'. 
    
    a1 : float
        First order (linear) loss coefficient (W/m2 K).
    
    a2 : float
        Second order (quadratic) loss coefficient (W/m2 K2).
    
    IAM : float, list, or dict
        Object specifying the shape of the IAM (Incidence Angle Modifier) curve. See :doc:`IAM </solar/IAM>` to learn the possible formats of this parameter.
    
    test_flowrate_per_m2 : float
        Flowrate per area unit with wich the collector has been tested (kg/m2 s).
    
    test_fluid : sercpy.fluids.Fluid
        :doc:`Fluid </fluids/fluid_class>` instance that models the fluid used to test the collector.
    """
    
    def __init__( self, *,
            
            collector: SolarCollector,
            coll_tilt: Optional[ float ] = None,
            coll_azmiuth: Optional[ float ] = None,
            total_colls: Optional[ int ] = None,
            coll_rows: Optional[ int ] = None,
            colls_per_row: Optional[ int ] = None,
            row_mode: Optional[ str ] = None,
            coll_disposition: Optional[ str ] = None,
            tube_direction: Optional[ str ] = None,
            non_shadeable_rows: Optional[ int ] = None,
            non_shadeable_colls: Optional[ int ] = None,
            ground_fraction_covered: Optional[ float ] = None,
            row_spacing: Optional[ float ] = None,
            release_vapor: Optional[ bool ] = None,
            tolerance: Optional[ float ] = None,
            max_iterations: Optional[ int ] = None, ):
        
        self._collector = self._validate_argument("collector", collector)
        self._coll_tilt = self._validate_argument("coll_tilt", coll_tilt)
        self._coll_azmiuth = self._validate_argument("coll_azmiuth", coll_azmiuth)
        
        if self._coll_tilt is None:
            self._tilt_mode = 'auto'
        else:
            self._tilt_mode = 'manual'
        
        if self._coll_azmiuth is None:
            self._azimuth_mode = 'auto'
        else:
            self._azimuth_mode = 'manual'
        
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
            raise ValueError( "SolarField: Only one of the arguments 'non_shadeable_rows' and 'non_shadeable_colls' must be provided." )
        elif non_shadeable_rows is not None:
            self._non_shadeable_rows = self._validate_argument("non_shadeable_rows", non_shadeable_rows)
        elif non_shadeable_colls is not None:
            if not non_shadeable_colls%self._colls_per_row == 0:
                raise ValueError(f"SolarField: 'non_shadeable_colls' must correspond to an entire number of rows (i.e. it must be a multiple of 'colls_per_row' which is { self._colls_per_row }).")
            self._non_shadeable_rows = non_shadeable_colls // self._colls_per_row
        else:
            self._non_shadeable_rows = max( [ int( self._coll_rows*0.2 ), 1 ] )
            
        self._shadeable_rows = self._coll_rows - self._non_shadeable_rows
            
        if ground_fraction_covered is not None:
            self._ground_fraction_covered = self._validate_argument("ground_fraction_covered", ground_fraction_covered)
        elif row_spacing is not None or coll_disposition is not None:
            row_spacing = self._validate_argument("row_spacing", row_spacing)
            coll_disposition = self._validate_argument("coll_disposition", coll_disposition)
            
            if any( [ row_spacing is None,
                      coll_disposition is None,
                      coll_disposition == 'HORIZONTAL' and self._collector.width is None,
                      coll_disposition == 'VERTICAL' and self._collector.length is None ] ):
                
                warnings.warn("SolarField: Not enough data was provided to determine parameters for self-shading modeling. Default values are assumed.")
                self._ground_fraction_covered = 0.7
            
            else:
                
                if coll_disposition == 'HORIZONTAL':
                    self._ground_fraction_covered = self._collector.width / row_spacing
                else:
                    self._ground_fraction_covered = self._collector.length / row_spacing
                    
        else:
            self._ground_fraction_covered = 0.7
            
        self._coll_disposition = self._validate_argument("coll_disposition", coll_disposition)
            
        if release_vapor is not None:
            self._release_vapor = self._validate_argument("release_vapor", release_vapor)
        else:
            self._release_vapor = True
            
        if tolerance is not None:
            self._tolerance = self._validate_argument("tolerance", tolerance)
        else:
            self._tolerance = 1e-3
        
        if max_iterations is not None:
            self._max_iterations = self._validate_argument("max_iterations", max_iterations)
        else:
            self._max_iterations = 100
        
        self._coll_area = self._collector.area
        self._coll_n0 = self._collector.n0
        self._coll_a1 = self._collector.a1
        self._coll_a2 = self._collector.a2
        
        if type( self._collector.IAM ) is list:
            self._coll_IAM = { [ 0, 10, 20, 30, 40, 50, 60, 70, 80, 90 ][i] : self._collector.IAM[i] for i in range( len( self._collector.IAM ) ) }
        elif type( self._collector.IAM ) is dict and 'Kl' in self._collector.IAM:
            self._coll_IAM = {  }
            for component_name in [ 'Kl', 'Kt' ]:
                IAM_list = self._collector.IAM[ component_name ]
                self._coll_IAM[ component_name ] = { [ 0, 10, 20, 30, 40, 50, 60, 70, 80, 90 ][i] : IAM_list[i] for i in range(len(IAM_list)) }
        else:
            try:
                self._coll_IAM = self._collector.IAM.copy()
            except AttributeError:
                self._coll_IAM = self._collector.IAM
        
        test_flow = self._collector.test_flowrate_per_m2*self._coll_area
        test_fluid_cp = self._collector.fluid.cp_ref
        self._FpUL = -( test_flow * test_fluid_cp / self._coll_area )*log( 1 - self._coll_a1*self._coll_area / ( test_flow*test_fluid_cp ) )
        self._test_conditions = ( test_flow*test_fluid_cp / ( self._coll_area * self.FpUL ) ) *( 1 - exp( - self._coll_area * self.FpUL / ( test_flow * test_fluid_cp ) ) )
        
        self._outlet = Outlet()
    
    @property
    def outlet(self):
        return self._outlet
    
    @property
    def collector(self):
        return self._collector
    
    @property
    def convergence(self):
        if not hasattr( self, "_convergence" ):
            raise AttributeError("SolarField: Attribute 'convergence' has not been computed yet. This attribute gets computed after calling the method SolarField.compute_outputs.")
        return self._convergence
    
    @property
    def useful_power(self):
        if not hasattr( self, "_useful_power" ):
            raise AttributeError("SolarField: Attribute 'useful_power' has not been computed yet. This attribute gets computed after calling the method SolarField.compute_outputs.")
        return self._useful_power
    
    @property
    def wasted_power(self):
        if not hasattr( self, "_wasted_power" ):
            raise AttributeError("SolarField: Attribute 'wasted_power' has not been computed yet. This attribute gets computed after calling the method SolarField.compute_outputs.")
        return self._wasted_power
    
    @property
    def vapor_flowrate(self):
        if not hasattr( self, "_vapor_flowrate" ):
            raise AttributeError("SolarField: Attribute 'vapor_flowrate' has not been computed yet. This attribute gets computed after calling the method SolarField.compute_outputs.")
        return self._vapor_flowrate
    
    @property
    def efficiency(self):
        if not hasattr( self, "_efficiency" ):
            raise AttributeError("SolarField: Attribute 'efficiency' has not been computed yet. This attribute gets computed after calling the method SolarField.compute_outputs.")
        return self._efficiency
    
    @property
    def iterations(self):
        if not hasattr( self, "_iterations" ):
            raise AttributeError("SolarField: Attribute 'iterations' has not been computed yet. This attribute gets computed after calling the method SolarField.compute_outputs.")
        return self._iterations
    
    @property
    def vapor_release_convergence(self):
        if not hasattr( self, "_vapor_release_convergence" ):
            raise AttributeError("SolarField: Attribute 'vapor_release_convergence' has not been computed yet. This attribute gets computed after calling the method SolarField.compute_outputs.")
        return self._vapor_release_convergence
    
    @property
    def coll_tilt(self):
        if self._coll_tilt is None:
            raise AttributeError("SolarField: Attribute 'coll_tilt' has not been defined yet. This attribute can be defined automatically with the method 'MeteoProfile.compute_poa_irradiance' using this SolarField instance.")
        return self._coll_tilt
    
    @property
    def coll_azimuth(self):
        if self._coll_azimuth is None:
            raise AttributeError("SolarField: Attribute 'coll_azimuth' has not been defined yet. This attribute can be defined automatically with the method 'MeteoProfile.compute_poa_irradiance' using this SolarField instance.")
        return self._coll_azimuth
    
    @property
    def coll_IAM(self):
        return self._coll_IAM
    
    @property
    def coll_disposition(self):
        if self._coll_disposition is None:
            raise AttributeError("SolarField: 'coll_disposition' has not been specified.")
        return self._coll_disposition
    
    @property
    def tube_direction(self):
        return self._tube_direction
    
    @property
    def ground_fraction_covered(self):
        return self._ground_fraction_covered
    
    @property
    def row_width_to_coll_length_ratio(self):
        return 100
        
    def set_auto_orientation( self, *, coll_tilt, coll_azimuth ):
        
        if self._tilt_mode == 'auto':
            self._coll_tilt = self._validate_argument( "coll_tilt", coll_tilt )
        if self._azimuth_mode == 'auto':
            self._coll_azimuth = self._validate_argument( "coll_azimuth", coll_azimuth )
        
    def _validate_argument(self, argument_name, value ):
        
        if type(argument_name) is not str:
            raise TypeError("SolarField._validate_argument: Argument 'argument_name' must be a string.")
            
        if not argument_name in field_allowed_arguments:
            raise ValueError( f"MeteoProfile: '{argument_name}' is not a valid argument." )
            
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
                
        if argument_name == 'coll_azmiuth':
            try:
                value = float( value )
            except:
                raise TypeError("SolarField: Argument 'coll_azmiuth' must be converible to type 'float'.")
            if not ( value >= 0 and value < 360 ):
                raise ValueError("SolarField: Argument 'coll_azmiuth' must be in the range 0 <= coll_azmiuth < 360.")
        
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
            
            if not value in [ 'HORIZONTAL', 'VERTICAL' ]:
                raise ValueError("SolarField: Argument 'tube_direction' must be one of the strings: 'horizontal', or 'vertical'.")
        
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
                
        if argument_name == 'release_vapor':
            try:
                value = bool( value )
            except:
                raise TypeError("SolarField: Argument 'release_vapor' must be convertible to a boolean value.")
        
        if argument_name == 'tolerance':
            try:
                value = float( value )
            except:
                raise TypeError("SolarField: Argument 'tolerance' must be converible to type 'float'.")
            if not ( value >= 1e-8 and value <= 1e-1 ):
                raise ValueError("SolarField: Argument 'tolerance' must be in the range 1e-8 <= tolerance <= 1e-1.")
                
        if argument_name == 'max_iterations':
            try:
                assert value.is_integer()
                value = int( value )
            except:
                raise TypeError("SolarField: Argument 'max_iterations' must be an integer value.")
                
            if not ( value >= 3 and value <= 300 ):
                raise ValueError("SolarField: Argument 'max_iterations' must be in the range 3 <= max_iterations <= 300.")
        
        return value
    
    def _compute_collector(self, flowrate, state_in, irradiance, IAM_factor, Tamb, flow_correction_factor):
        """
        Function that computes the power of an individual solar collector and returns the state of the fluid leaving it.
        
        Parameters
        ----------
        flowrate : float
            Mass flowrate entering the collector (kg/s).
        
        state_in : sercpy.fluids.FluidState
            State of the fluid as it enters the collector.
        
        irradiance : float
            Solar irradiance on the collector's plane (W/m2).
        
        IAM_factor : float
            Dimensionless quantity defining the correction factor associated to IAM (Incidence Angle Modifier).
        
        Tamb : float
            Ambient temperature (°C).
        
        flow_correction_factor : float
            Dimensionless quantity defining the correction factor associated to the flowrate.
        
        Returns
        -------
        state_out : sercpy.fluids.FluidState
            State of the fluid leaving the collector.
        """
        
        T_in = state_in.T
        h_in = state_in.h
        efficiency = flow_correction_factor*max( [ self._coll_n0*IAM_factor - self._coll_a1*( T_in - Tamb )/irradiance - self._coll_a2*(T_in - Tamb)*abs( T_in - Tamb )/irradiance , 0 ] )
        power = efficiency*irradiance*self.coll_area
        h_out = h_in + power/flowrate
        return state_in.fluid.state( h = h_out )

    def _compute_row( self, flowrate_in, state_in, T_mains, irradiance, IAM_factor, Tamb, flow_correction_factor ):
        """
        Function that computes the power of a collector row and returns the state of the fluid leaving it.
        
        Parameters
        ----------
        flowrate_in : float
            Mass flowrate entering the collector row (kg/s).
        
        state_in : sercpy.fluids.FluidState
            State of the fluid as it enters the collector row.
        
        T_mains : float
            Mains water temperature (°C). This parameter is only used is water boiling and replacement from the distribution network is simulated by the solar field model.
        
        irradiance : float
            Solar irradiance on the collectors' plane (W/m2).
        
        IAM_factor : float
            Dimensionless quantity defining the correction factor associated to IAM (Incidence Angle Modifier).
            
        Tamb : float
            Ambient temperature (°C).
            
        flow_correction_factor : float
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
            
            h_in = state_in.h
            h_mains = fluid.state( T = T_mains ).h
            
            flowrate_mains = 0
            it = 0
            while True:
                flowrate_mix = flowrate_in + flowrate_mains
                h_mix_init = ( flowrate_in*h_in + flowrate_mains*h_mains )/flowrate_mix
                
                mixture_state = fluid.state( h = h_mix_init )
                
                if self._row_mode == 'SERIES':
                    for i in range( self._colls_per_row ):
                        mixture_state = self._compute_collector(flowrate_mix, mixture_state, irradiance, IAM_factor, Tamb, flow_correction_factor)
                else:
                    mixture_state = self._compute_collector( flowrate_mix / self._colls_per_row , mixture_state, irradiance, IAM_factor, Tamb, flow_correction_factor)
                
                vapor_flowrate = mixture_state.Q*flowrate_mix
                
                it = it + 1
                if flowrate_mains == vapor_flowrate or abs(flowrate_mains - vapor_flowrate)/max([ flowrate_mains, vapor_flowrate ]) < self._tolerance:
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
                    fluid_state = self._compute_collector( flowrate_in, fluid_state, irradiance, IAM_factor, Tamb, flow_correction_factor )
            else:
                fluid_state = self._compute_collector( flowrate_in / self._colls_per_row , fluid_state, irradiance, IAM_factor, Tamb, flow_correction_factor )
            return fluid_state, 0, 0, 0, True
        
    def set_connections( self, *, inlet ):
        
        if not isinstance( inlet, Outlet ):
            raise ValueError("SolarField.set_inputs: 'outlet' must be an instance of sercpy.devices.outlet.")
        
        self._inlet = inlet
    
    def set_convergence_criteria( self, *,
                                  relative_tolerance: float,
                                  temp_tolerance: Optional[ float ] = None,
                                  h_tolerance: Optional[ float ] = None,
                                  temp_normalization_range: Optional[ float ] = None,
                                  h_normalization_range: Optional[ float ] = None, ):
        
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
        
        
        if temp_tolerance is not None:
            try:
                temp_tolerance = float( temp_tolerance )
            except:
                raise TypeError("SolarField.set_convergence_criteria: 'temp_tolerance' must be convertible to type 'float'.")
            self._temp_tolerance = temp_tolerance
            self._h_tolerance = None
        elif temp_normalization_range is not None:
            try:
                temp_normalization_range = float( temp_normalization_range )
            except:
                raise TypeError("SolarField.set_convergence_criteria: 'temp_normalization_range' must be convertible to type 'float'.")
            self._temp_tolerance = relative_tolerance*temp_normalization_range
            self._h_tolerance = None
        elif h_tolerance is not None:
            try:
                h_tolerance = float( h_tolerance )
            except:
                raise TypeError("SolarField.set_convergence_criteria: 'h_tolerance' must be convertible to type 'float'.")
            self._h_tolerance = h_tolerance
            self._temp_tolerance = None
        elif h_normalization_range is not None:
            try:
                h_normalization_range = float( h_normalization_range )
            except:
                raise TypeError("SolarField.set_convergence_criteria: 'h_normalization_range' must be convertible to type 'float'.")
            self._h_tolerance = relative_tolerance*h_normalization_range
            self._temp_tolerance = None
        else:
            raise Exception("SolarField.set_convergence_criteria: Unexpected error.")
            
    def _set_last_inputs( self, flowrate, state_in ):
        
        self._flowrate_last = flowrate
        self._state_in_last = state_in
        
    def _compute_convergence(self, flowrate, state_in ):
        
        convergence = True
        if flowrate == 0 or self._flowrate_last == 0:
            convergence = convergence and flowrate == self._flowrate_last
        elif flowrate != self._flowrate_last:
            convergence = convergence and abs( flowrate - self._flowrate_last ) / min( [ flowrate  , self._flowrate_last ] ) < self._relative_tolerance
        
        if self._h_tolerance is not None:
            convergence = convergence and abs( state_in.h - self._state_in_last.h ) < self._h_tolerance
        elif self._temp_tolerance is not None:
            convergence = convergence and abs( state_in.T - self._state_in_last.T ) < self._temp_tolerance
        else:
            raise Exception("SolarField._compute_convergence: Unexpected error.")
        
        return convergence

    def compute_outputs( self, operating_conditions, iteration_number ):
        """
        Method to compute the outputs of the solar field.

        Parameters
        ----------
        operating_conditions : dict
            Dictionary returned by an instance of `sercpy.operating_conditions.OperatingConditions` when its method `get_conditions` is called.
        iteration_number : int
            Number of the iteration

        Returns
        -------
        None
        """
        
        if type( operating_conditions ) is not dict:
            raise TypeError("SolarField.compute_outputs: Argument 'operating_conditions' must be a dictionary.")
        if not ( type( iteration_number ) is int and iteration_number >= 0 ):
            raise TypeError("SolarField.compute_outputs: Argument 'iteration_number' must be an 'int'. Its value msut be >= 0.")
        
        try:
            flowrate = self.inlet.flowrate
            state_in = self.inlet.state
        except AttributeError:
            return
        
        if iteration_number == 0:
            self._set_last_inputs(flowrate, state_in)
            self._convergence = False
        else:
            self._convergence = self._compute_convergence(flowrate, state_in)
            if self._convergence:
                return
            else:
                self._set_last_inputs(flowrate, state_in)
        
        if flowrate == 0:
            self._outlet.flowrate = 0
            self._outlet.state = state_in
            self._useful_power = 0
            self._wasted_power = 0
            self._vapor_flowrate = 0
            self._efficiency = None
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
        
        flowrate_each_row = flowrate/self._coll_rows
        fluid = state_in.fluid
        
        use_conditions = ( flowrate_each_row*fluid.cp_ref/(self._coll_area*self._FpUL) )*( 1 - exp( - self._coll_area*self._FpUL/( flowrate_each_row*fluid.cp_ref ) ) )
        flow_correction_factor = use_conditions/self._test_conditions
        
        # Suffix "NS" for NON-shadeable rows
        if irradiance_first_row > 0:
            state_out_NS, Q_waste_NS, vap_flow_NS, iterations_NS, convergence_NS = self._compute_row(flowrate_each_row, state_in, Tmains, irradiance_first_row, IAM_first_row, Tamb, flow_correction_factor)
        else:
            state_out_NS = state_in.h
            Q_waste_NS = 0
            vap_flow_NS = 0
            iterations_NS = 1
            convergence_NS = True
        
        # Suffix "Sh" for shadeable rows
        if irradiance_shadeable_rows > 0:
            state_out_Sh, Q_waste_Sh, vap_flow_Sh, iterations_Sh, convergence_Sh = self._compute_row(flowrate_each_row, state_in, Tmains, irradiance_shadeable_rows, IAM_shadeable_rows, Tamb, flow_correction_factor)
        else:
            state_out_Sh = state_in.h
            Q_waste_Sh = 0
            vap_flow_Sh = 0
            iterations_Sh = 1
            convergence_Sh = True
            
        h_out = min([ ( state_out_NS.h*self._non_shadeable_rows + state_out_Sh.h*self._shadeable_rows ) / self.coll_rows , fluid.h_sat_liq ])
        state_out = fluid.state( h = h_out )
        
        Q_useful = max ( [ flowrate*( h_out - state_in.h ) , 0 ] )
        Q_waste = max( [ Q_waste_NS*self._non_shadeable_rows + Q_waste_Sh*self._shadeable_rows , 0 ] )
        vapor_flowrate = vap_flow_NS*self._non_shadeable_rows + vap_flow_Sh*self._shadeable_rows
        
        if irradiance_first_row <= 0:
            efficiency = None
        else:
            efficiency = Q_useful/( irradiance_first_row*self.coll_area*self.coll_rows*self.colls_per_row )
        
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
    
def example_solar_field(
        *,
        
        location = None,
        latitude = None,
        longitude = None,
        field_gross_area = None,
        
        ):
    
    if not ( location is not None or ( latitude is not None and longitude is not None ) ):
        raise ValueError("example_solar_field: Either 'location' or 'latitude' and 'longitude' must be provided.")
        
    if location is not None:
        try:
            assert type(location) is tuple and len( location ) == 2
            latitude, longitude = float( location[0] ), float( location[1] )
        except:
            raise ValueError("example_solar_field: 'location' must be a tuple of two values convertible to float.")
    else:
        try:
            latitude = float( latitude )
            longitude = float( longitude )
        except:
            raise ValueError("example_solar_field: latitude and longitude must be convertible to float.")
    
    coll_tilt = abs( latitude )
    if latitude < 0:
        coll_azimuth = 0
    else:
        coll_azimuth = 180
    coll_IAM = { 0: 1, 10: 1, 20: 0.98, 30: 0.95, 40: 0.92, 50: 0.88, 60: 0.85, 70: 0.8, 80: 0.30, 90: 0 }
    ground_fraction_covered = 0.65
    row_width_to_coll_length_ratio = 40
    
    return SolarField(
        
        coll_tilt = coll_tilt,
        coll_azimuth = coll_azimuth,
        coll_IAM = coll_IAM,
        ground_fraction_covered = ground_fraction_covered,
        row_width_to_coll_length_ratio = row_width_to_coll_length_ratio,
        
        )