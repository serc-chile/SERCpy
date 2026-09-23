# -*- coding: utf-8 -*-
"""
Created on Fri Jul 14 15:08:06 2023

@author: adria
"""

class UnitsError(Exception):
    pass

unit_database = {

    'time': {
        
        's': 1,
        'second': 1,
        'seconds': 1,
        'min': 60,
        'minute': 60,
        'minutes': 60,
        'h': 3600,
        'hour': 3600,
        'hours': 3600,
        'hr': 3600,
        'day': 3600*24,
        'year': 3600*24*365,
        
        },
    
    'energy': {
        
        'J': 1,
        'kJ': 1e3,
        'MJ': 1e6,
        'GJ': 1e9,
        'TJ': 1e12,
        'j': 1,
        'kj': 1e3,
        'KJ': 1e3,
        'cal': 4.184,
        'kcal': 4184,
        'Mcal': 4.184e6,
        'BTU': 1055.056,
        'btu': 1055.056,
        'Btu': 1055.056,
        'kBTU': 1e3*1055.056,
        'kbtu': 1e3*1055.056,
        'kBtu': 1e3*1055.056,
        'MBTU': 1e6*1055.056,
        'Mbtu': 1e6*1055.056,
        'MBtu': 1e6*1055.056,
        'Wh': 3.6e3,
        'kWh': 3.6e6,
        'MWh': 3.6e9,
        'GWh': 3.6e12,
        
        },
    
    'pressure': {
        
        'Pa': 1,
        'pa': 1,
        'kPa': 1e3,
        'kpa': 1e3,
        'MPa': 1e6,
        'Mpa': 1e6,
        'bar': 100000,
        'mbar': 100,
        'atm': 101325,
        'ATM': 101325,
        'mmHg': 133.322,
        'mmhg': 133.322,
        'psi': 6894.76,
        'PSI': 6894.76,
        
        },
    
    'distance': {
        
        'm': 1,
        'meter': 1,
        'metre': 1,
        'meters': 1,
        'metres': 1,
        'KM': 1e3,
        'Km': 1e3,
        'km': 1e3,
        'kilometer': 1e3,
        'kilometre': 1e3,
        'kilometers': 1e3,
        'kilometres': 1e3,
        'mm': 1e-3,
        'milimeter': 1e-3,
        'milimetre': 1e-3,
        'milimeters': 1e-3,
        'milimetres': 1e-3,
        'cm': 1e-2,
        'centimeter': 1e-2,
        'centimetre': 1e-2,
        'centimeters': 1e-2,
        'centimetres': 1e-2,
        'dm': 1e-1,
        'decimeter': 1e-1,
        'decimetre': 1e-1,
        'decimeters': 1e-1,
        'decimetres': 1e-1,
        'hm': 1e2,
        'mile': 1609.34,
        
        },
    
    'area': {
        
        'm2': 1,
        'cm2': 1e-4,
        'hm2': 1e4,
        'in2': 0.00064516,
        'ha': 1e4,
        'HA': 1e4,
        'Ha': 1e4,
        'ft2': 0.092903,
        
        },
    
    'volume': {
        
        'm3': 1,
        'L': 1e-3,
        'ft3': 0.0283168,
        'in3': 1.6387e-5,
        'gal': 0.003785411784,
        'gallon': 0.003785411784,
        'barrel': 0.15899,
        'bbl': 0.15899,
        'dm3': 1e-3,
        'cm3': 1e-6,
        'mm3': 1e-9,
        
        },
    
    'mass': {
        
        'kg': 1,
        'KG': 1,
        'g': 1e-3,
        'Mg': 1e3,
        'mg': 1e-6,
        'lb': 0.453592,
        'short_ton': 0.453592*2000,
        'Short_Ton': 0.453592*2000,
        'short_Ton': 0.453592*2000,
        'Short_ton': 0.453592*2000,
        'st': 0.453592*2000,
        'metric_ton': 1000,
        'Metric_Ton': 1000,
        'metric_Ton': 1000,
        'Metric_ton': 1000,
        'tonne': 1000,
        'Tonne': 1000,
        'tonnes': 1000,
        'Tonnes': 1000,
        
        },
    
    'temperature': {
        
        'C': 1,
        '°C': 1,
        'K': 1,
        '°K': 1,
        'F': 5/9,
        '°F': 5/9,
        'R': 5/9,
        '°R': 5/9,
        'Ra': 5/9,
        '°Ra': 5/9,
        
        },
    
    'power': {
        
        'W': 1,
        'w': 1,
        'kW': 1e3,
        'kw': 1e3,
        'MW': 1e6,
        'Mw': 1e6,
        'hp': 745.7,
        'HP': 745.7,
        'Hp': 745.7,
        
        }

}

# volumetric flowrate
# mass flowrate
# specific heat
# power
# density

unit_type_dict = {}
for unit_type in unit_database:
    for _unit in unit_database[ unit_type ]:
        if _unit in unit_type_dict:
            raise UnitsError(f"Repeated unit: {_unit}")
        unit_type_dict[ _unit ] = unit_type
        
def _convert_to_C( input_value, original_units ):
    
    if original_units in [ 'C', '°C' ]:
        return input_value
    if original_units in [ 'K', '°K' ]:
        return input_value - 273.15
    if original_units in [ 'F', '°F' ]:
        return (input_value - 32)*5/9
    if original_units in [ 'R', '°R', 'Ra', '°Ra' ]:
        return input_value*5/9 - 273.15
    raise UnitsError(f"Temperature units not valid: {original_units}")
    
def _convert_C( input_value, goal_units ):
    
    if goal_units in [ 'C', '°C' ]:
        return input_value
    if goal_units in [ 'K', '°K' ]:
        return input_value + 273.15
    if goal_units in [ 'F', '°F' ]:
        return input_value*9/5 + 32
    if goal_units in [ 'R', '°R', 'Ra', '°Ra' ]:
        return (input_value + 273.15)*9/5
    raise UnitsError(f"Temperature units not valid: {goal_units}")
    
def _convert_temperature( input_value, original_units, goal_units ):
    
    temp_C = _convert_to_C( input_value, original_units )
    return _convert_C( temp_C, goal_units )

def _isolate_units( unit_string ):
    
    unit_string = unit_string.replace( '*', ' ' )
    unit_string = unit_string.replace( '.', ' ' )
    unit_list = unit_string.split( ' ' )
    while '' in unit_list:
        unit_list.remove( '' )
    return set( unit_list )

def get_unit_type( units: str ) -> str:
    """
    Function that takes the units of a physical quantity and identifies the type of quantity involved.
    
    When the type of the units provided cannot be identified, the function returns None.
    
    The possible unit types that can be identified are:
        
        - time
        - energy
        - pressure
        - distance
        - area
        - volume
        - mass
        - temperature
        - power
        - density
        - volumetric_flowrate
        - mass_flowrate
        - power
        - specific_energy_mass
        - specific_energy_volume
        - specific_heat_capacity

    Parameters
    ----------
    units : str
        Unit to identify.

    Returns
    -------
    str or NoneType
        If the unit type can be identified, it is returned as a string. Else, None is returned.

    """
    
    if not '/' in units:
        try:
            basic_unit_set = _isolate_units( units )
            assert len( basic_unit_set ) == 1
            basic_unit = basic_unit_set.pop()
            assert basic_unit in unit_type_dict
        except:
            return None
        return unit_type_dict[ basic_unit ]
    
    units_numerator, units_denominator = _isolate_units( units.split('/')[0] ), _isolate_units( units.split('/')[1] )
    
    try:
        unit_types_numerator = { unit_type_dict[ unit ] for unit in units_numerator }
        unit_types_denominator = { unit_type_dict[ unit ] for unit in units_denominator }
    except KeyError:
        return None
    
    if unit_types_numerator == {'mass'} and unit_types_denominator == {'volume'}:
        return 'density'
    
    if unit_types_numerator == {'volume'} and  unit_types_denominator == {'time'}:
        return 'volumetric_flowrate'
    
    if unit_types_numerator == {'mass'} and  unit_types_denominator == {'time'}:
        return 'mass_flowrate'
    
    if unit_types_numerator == {'energy'} and unit_types_denominator == {'time'}:
        return 'power'
    
    if unit_types_numerator == {'energy'} and unit_types_denominator == {'mass'}:
        return 'specific_energy_mass'

    if unit_types_numerator == {'energy'} and unit_types_denominator == {'volume'}:
        return 'specific_energy_volume'
    
    if unit_types_numerator == {'energy'} and unit_types_denominator == {'mass', 'temperature'}:
        return 'specific_heat_capacity'
    
    return None
    
def _conversion_factor_to_basic_units( units ):
    
    if not '/' in units:
        try:
            basic_unit_set = _isolate_units( units )
            assert len( basic_unit_set ) == 1
            basic_unit = basic_unit_set.pop()
            assert basic_unit in unit_type_dict
        except:
            raise UnitsError(f"Variable type could not be identified from units: {units}")
        return unit_database[ unit_type_dict[ basic_unit ] ][ basic_unit ]
    
    units_numerator, units_denominator = _isolate_units( units.split('/')[0] ), _isolate_units( units.split('/')[1] )
    
    factor = 1
    
    try:
        for unit in units_numerator:
            unit_type = unit_type_dict[ unit ]
            factor = factor*unit_database[ unit_type ][ unit ]
        for unit in units_denominator:
            unit_type = unit_type_dict[ unit ]
            factor = factor/unit_database[ unit_type ][ unit ]
    except KeyError:
        raise UnitsError(f"Unit not identified: {unit}")
        
    return factor

def _pre_process_units( units ):
    units = units.replace( 'short ton', 'short_ton' )
    units = units.replace( 'Short Ton', 'Short_Ton' )
    units = units.replace( 'short Ton', 'short_Ton' )
    units = units.replace( 'Short ton', 'Short_ton' )
    units = units.replace( 'metric ton', 'metric_ton' )
    units = units.replace( 'Metric Ton', 'Metric_Ton' )
    units = units.replace( 'metric Ton', 'metric_Ton' )
    units = units.replace( 'Metric ton', 'Metric_ton' )
    units = units.replace( 'per', '/' )
    units = units.replace( '(', '' )
    units = units.replace( ')', '' )
    return units

def convert_units( input_value, original_units, goal_units, density = None, density_units = 'kg/m3' ):
    """
    Function to obtain the numeric value of a quantity as expressed in another unit system.
    
    It also allows the conversion of mass to volume (and viceversa) and of mass flowrate to volumetric flowrate (and viceversa).
    
    If several values need be converted from the same original units to the same goal units, it is recommendable to provide all the values in a list, so that the conversion factor is computed only once. This is much faster than applying this function separately to every value of a list.

    Parameters
    ----------
    input_value : float or list of float
        Value or list of values to be converted.
    original_units : str
        Original units in which the quantities are expressed.
    goal_units : str
        Units in which the quantities need to be expressed.
    density : float, optional
        Only needed if a conversion between mass and volumes (or flowrates involving volumes and masses) is being carried out. The default is None.
    density_units : str, optional
        Units in which the density of the fluid is being expressed. The default is `"kg/m3"`.

    Raises
    ------
    UnitsError
        If the conversion is not possible.

    Returns
    -------
    float or list of float
        Quantity specified as `input_value`, in the new unit system. If the input is a list, so is the returned value.

    """
    
    try:
        input_value = float( input_value )
    except TypeError:
        try:
            input_value = [ float( value ) for value in input_value ]
        except:
            raise UnitsError("Unit conversion error: input_value must be either a floating point value or a list of floating point values.")
    try:
        original_units = str( original_units )
    except:
        raise UnitsError("convert_units: Argument 'original_units' must be convertible to type str.")
    try:
        goal_units = str( goal_units )
    except:
        raise UnitsError("convert_units: Argument 'goal_units' must be convertible to type str.")
    if density is not None:
        try:
            density = float( density )
        except:
            raise UnitsError("convert_units: Argument 'density' must be None or convertible to type float.")
    try:
        density_units = str( density_units )
    except:
        raise UnitsError("convert_units: Argument 'density_units' must be convertible to type str.")
    
    original_units = _pre_process_units( original_units )
    goal_units = _pre_process_units( goal_units )
    
    if original_units in unit_type_dict and unit_type_dict[ original_units ] == 'temperature':
        if not ( goal_units in unit_type_dict and unit_type_dict[ goal_units ] == 'temperature' ):
            raise UnitsError("convert_units: original_units are temperature units and goal_units are not.")
        conversion_function = lambda value: _convert_temperature( value, original_units, goal_units )
        
    else:
        
        if original_units in unit_type_dict and goal_units in unit_type_dict and unit_type_dict[ original_units ] == unit_type_dict[ goal_units ]:
            
            original_to_basic_factor = unit_database[ unit_type_dict[ original_units ] ][ original_units ]
            goal_to_basic_factor = unit_database[ unit_type_dict[ goal_units ] ][ goal_units ]
            conversion_factor = original_to_basic_factor/goal_to_basic_factor
        
        elif ( original_units in unit_type_dict and goal_units in unit_type_dict and
               ( ( unit_type_dict[ original_units ] == 'mass' and unit_type_dict[ goal_units ] == 'volume' ) or
                 ( unit_type_dict[ original_units ] == 'volume' and unit_type_dict[ goal_units ] == 'mass' ) ) ):
            
            if density is None:
                raise UnitsError("convert_units: Cannot convert mass to volume (and viceversa) without a known density.")
                
            if density_units == 'kg/m3':
                density_kg_m3 = density
            else:
                density_kg_m3 = convert_units(density, density_units, 'kg/m3')
            
            if unit_type_dict[ original_units ] == 'mass' and unit_type_dict[ goal_units ] == 'volume':
                conversion_factor_to_kg = convert_units( 1, original_units, 'kg' )
                conversion_factor_kg_to_m3 = 1/density_kg_m3
                conversion_factor_m3_to_goal_units = convert_units( 1, 'm3', goal_units )
                conversion_factor = conversion_factor_to_kg*conversion_factor_kg_to_m3*conversion_factor_m3_to_goal_units
                
            elif unit_type_dict[ original_units ] == 'volume' and unit_type_dict[ goal_units ] == 'mass':
                conversion_factor_to_m3 = convert_units( 1, original_units, 'm3' )
                conversion_factor_m3_to_kg = density_kg_m3
                conversion_factor_kg_to_goal_units = convert_units(1, 'kg', goal_units)
                conversion_factor = conversion_factor_to_m3*conversion_factor_m3_to_kg*conversion_factor_kg_to_goal_units
                
        elif '/' in original_units and not '/' in goal_units:
            
            if not ( get_unit_type( original_units ) == 'power' and get_unit_type( goal_units ) == 'power' ):
                raise UnitsError(f"Unit conversion error: no conversion feasible from original units {original_units} to goal units {goal_units}.")
            
            original_units_to_W_factor = _conversion_factor_to_basic_units( original_units )
            goal_units_to_W_factor = unit_database[ unit_type_dict[ goal_units ] ][ goal_units ]
            
            conversion_factor = original_units_to_W_factor/goal_units_to_W_factor
        
        elif not '/' in original_units and '/' in goal_units:
            
            if not ( get_unit_type( original_units ) == 'power' and get_unit_type( goal_units ) == 'power' ):
                raise UnitsError(f"Unit conversion error: no conversion feasible from original units {original_units} to goal units {goal_units}.")
                
            original_units_to_W_factor = unit_database[ unit_type_dict[ original_units ] ][ original_units ]
            goal_units_to_W_factor = _conversion_factor_to_basic_units( goal_units )
            
            conversion_factor = original_units_to_W_factor/goal_units_to_W_factor
            
        elif '/' in original_units and '/' in goal_units:
            
            var_type_1 = get_unit_type( original_units )
            var_type_2 = get_unit_type( goal_units )
            
            if var_type_1 is None:
                raise UnitsError(f"convert_units: Unit type of original_units '{original_units}' could not be identified.")
            if var_type_2 is None:
                raise UnitsError(f"convert_units: Unit type of goal_units '{goal_units}' could not be identified.")
            
            if not ( var_type_1 == var_type_2 or ( var_type_1.endswith( 'flowrate' ) and var_type_2.endswith( 'flowrate' ) ) ):
                raise UnitsError("Unit conversion error: original units and goal units do not belong to the same variable type.")
            
            if var_type_1 == var_type_2:
                
                original_units_to_W_factor = _conversion_factor_to_basic_units( original_units )
                goal_units_to_W_factor = _conversion_factor_to_basic_units( goal_units )
                
                conversion_factor = original_units_to_W_factor/goal_units_to_W_factor
                
            elif var_type_1 == 'volumetric_flowrate' and var_type_2 == 'mass_flowrate':
                
                if density is None:
                    raise UnitsError("convert_units: Cannot convert mass to volume (and viceversa) without a known density.")
                    
                if density_units == 'kg/m3':
                    density_kg_m3 = density
                else:
                    density_kg_m3 = convert_units(density, density_units, 'kg/m3')
                
                original_units_to_m3_per_s_factor = _conversion_factor_to_basic_units( original_units )
                m3_per_s_to_kg_per_s_factor = density_kg_m3
                goal_units_to_kg_per_s_factor =  _conversion_factor_to_basic_units( goal_units )
                
                conversion_factor = original_units_to_m3_per_s_factor*m3_per_s_to_kg_per_s_factor/goal_units_to_kg_per_s_factor
                
            elif var_type_1 == 'mass_flowrate' and var_type_2 == 'volumetric_flowrate':
                
                if density is None:
                    raise UnitsError("convert_units: Cannot convert mass to volume (and viceversa) without a known density.")
                    
                if density_units == 'kg/m3':
                    density_kg_m3 = density
                else:
                    density_kg_m3 = convert_units(density, density_units, 'kg/m3')
                
                original_units_to_kg_per_s_factor = _conversion_factor_to_basic_units( original_units )
                kg_per_s_to_m3_per_s_factor = 1/density_kg_m3
                goal_units_to_m3_per_s_factor =  _conversion_factor_to_basic_units( goal_units )
                
                conversion_factor = original_units_to_kg_per_s_factor*kg_per_s_to_m3_per_s_factor/goal_units_to_m3_per_s_factor
            
            else:
                raise UnitsError(f"Unit conversion error: no conversion feasible from original units {original_units} to goal units {goal_units}.")
            
        else:
            raise UnitsError(f"Unit conversion error: no conversion feasible from original units {original_units} to goal units {goal_units}.")
            
        conversion_function = lambda value: conversion_factor*value
    
    if type( input_value ) is float:
        return conversion_function( input_value )
    return [ conversion_function( value ) for value in input_value ]

if __name__ == "__main__":
    # Test
    
    # Temperature conversions
    
    # Convert F to C
    print( f"78 F to C: {convert_units( 78, 'F', 'C' )}" )
    
    # Convert C to F
    print( f"90 C to F: {convert_units( 90, 'C', 'F' )}" )
    
    # Convert C to R
    print( f"90 C to R: {convert_units( 90, 'C', 'R' )}" )
    
    # Convert R to C
    print( f"90 R to C: {convert_units( 90, 'R', 'C' )}" )
    
    # Convert F to R
    print( f"0 F to R: {convert_units( 0, 'F', 'R' )}" )
    
    # Convert R to F
    print( f"0 R to F: {convert_units( 0, 'R', 'F' )}" )
    
    # Specific heat capacity conversions
    
    # Convert 6000 BTU/lb F to J/kg C
    print( f"6000 BTU/lb F to J/kg C: {convert_units( 6000, 'BTU/lb F', 'J/kg C' )}" )
    
    # Convert 6000 BTU/lb F to MJ/kg C
    print( f"6000 BTU/lb F to MJ/kg C: {convert_units( 6000, 'BTU/lb F', 'MJ/kg C' )}" )
    
    # Convert 5 kWh/lb F to MJ/kg C
    print( f"5 kWh/lb F to MJ/kg C: {convert_units( 5, 'kWh/lb F', 'MJ/kg C' )}" )
    
    # Power conversions
    
    # Convert 500 BTU/hr to W
    print( f"500 BTU/hr to W: {convert_units( 500, 'BTU/hr', 'W' )}" )
    
    # Convert 50 HP to kW
    print( f"50 HP to kW: {convert_units( 50, 'HP', 'kW' )}" )
    
    # Convert 500 BTU/hr to kW
    print( f"500 BTU/hr to kW: {convert_units( 500, 'BTU/hr', 'kW' )}" )
    
    # Convert 78 BTU/hr to kJ/min
    print( f"78 BTU/hr to kJ/min: {convert_units( 78, 'BTU/hr', 'kJ/min' )}" )
    
    # Convert 48 kW to kWh/day
    print( f"48 kW to kWh/day: {convert_units( 48, 'kW', 'kWh/day' )}" )
    
    # Mass conversions
    
    # Convert 2 metric tons to lb
    print( f"2 metric tonnes to lb: { convert_units( 2, 'tonne', 'lb' ) }" )
    
    # Convert 2 short tons to lb
    print( f"2 short tons to lb: { convert_units( 2, 'short ton', 'lb' ) }" )
    
    # Volume conversions
    
    # Convert 15 ft3 to gal
    print( f"15 ft3 to gal: { convert_units( 15, 'ft3', 'gal' ) }" )
    
    # Convert 50 bbl to L
    print( f"50 bbl to L: { convert_units( 50, 'bbl', 'L' ) }" )
    
    # Volumetric flowrate conversions
    
    # Convert 50 bbl/hr to L/s
    print( f"50 bbl/hr to L/s: { convert_units( 50, 'bbl/hr', 'L/s' ) }" )
    
    # Mass flowrate conversions
    
    # Convert 15 kg/s to tonnes/day
    print( f"15 kg/s to tonnes/day: { convert_units( 15, 'kg/s', 'tonnes/day' ) }" )
    
    # Mass <-> Volume conversions
    
    density_1 = 1000
    
    # Convert 15 m3/h to kg/hr
    print( f"15 m3/h to kg/hr: { convert_units( 15, 'm3/h', 'kg/hr', density = density_1 ) }" )
    
    # Convert 15 m3/h to kg/s
    print( f"15 m3/h to kg/s: { convert_units( 15, 'm3/h', 'kg/s', density = density_1 ) }" )
    
    # Convert 15 m3/day to kg/min
    print( f"15 m3/day to kg/min: { convert_units( 15, 'm3/day', 'kg/min', density = density_1 ) }" )
    
    # Change density units
    
    density_units = 'g/cm3'
    print( f"15 m3/day to kg/min (new density units): { convert_units( 15, 'm3/day', 'kg/min', density = density_1, density_units = density_units ) }" )
    
    
    # Convert 15 kg/hr to m3/day
    print( f"15 kg/hr to m3/day: { convert_units( 15, 'kg/hr', 'm3/day', density = density_1 ) }" )
    
    # Convert 3 short ton/min to m3/day
    print( f"3 short ton/min to m3/day: { convert_units( 3, 'short ton/min', 'm3/day', density = density_1 ) }" )
    
    # # Change density and density units
    
    density_1 = 1
    density_units = 'tonne/bbl'
    print( f"15 m3/day to kg/min (new density): { convert_units( 15, 'm3/day', 'kg/min', density = density_1, density_units = density_units ) }" )
    
    
    # Convert heating value of a fuel
    # Convert 4000 kJ/kg to kcal/lb
    print( f"4000 kJ/kg to kcal/lb: { convert_units( 4000, 'kJ/kg', 'kcal/lb' ) }" )
    
    
    
    