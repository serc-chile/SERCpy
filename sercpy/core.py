# -*- coding: utf-8 -*-
"""
Created on Mon Aug 17 12:33:21 2026

@author: adria
"""

class SHIPcalError(Exception):
    def __init__(self, message):
        super().__init__(message)
        
class UnitConversionError(Exception):
    pass


weekday_names = [ "Monday", "Tuesday", "Wednesday", "Thursay", "Friday", "Saturday", "Sunday" ]
month_days = [ 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31 ]
monthly_cummulated_days = [ 0 ] + [ sum([ month_days[i] for i in range(m + 1)  ]) for m in range(len(month_days)) ]
month_names = {
    
    0: 'January',
    1: 'February',
    2: 'March',
    3: 'April',
    4: 'May',
    5: 'June',
    6: 'July',
    7: 'August',
    8: 'September',
    9: 'October',
    10: 'November',
    11: 'December',
    
    }

# PARA TODOS LOS COMBUSTIBLES EL EF SE EXPRESA EN KG_CO2/KG_FUEL
# PARA LA ELECTRICIDAD SE EXPRESA EN KG_CO2/KWH
Energy_Sources_Database = { 'LIQUEFIED PETROLEUM GAS': {'density': 2.15, 'LHV': 45.5e6, 'HHV': 49.3e6, 'EF': 2.98463 },
                            'NATURAL GAS': {'density': 0.777, 'LHV': 47.1e6, 'HHV': 52.2e6, 'EF': 2.6928 },
                            'METHANE': {'density': 0.716, 'LHV': 50.0e6, 'HHV': 55.5e6, 'EF': 2.75 },
                            'PROPANE': {'density': 1.875, 'LHV': 46.4e6, 'HHV': 50.4e6, 'EF': 3 },
                            'BUTANE': {'density': 2.51, 'LHV': 45.3e6, 'HHV': 49.1e6, 'EF': 3.035 },
                            'DIESEL': {'density': 846, 'LHV': 42.6e6, 'HHV': 45.6e6, 'EF': 3.1863 },
                            'COAL': {'density': 1300, 'LHV': 29.0e6, 'HHV': 30.2e6, 'EF': 2.44068 },
                            'BIOMASS': {'density': 760*0.9, 'LHV': 14.4e6, 'HHV': 17.6e6, 'EF': 1.7472 },
                            'ELECTRICITY': { 'EF': 0.4 } }

Energy_Sources_Database['LIQUEFIED_PETROLEUM_GAS'] = Energy_Sources_Database['LIQUEFIED PETROLEUM GAS']
Energy_Sources_Database['NATURAL_GAS'] = Energy_Sources_Database['NATURAL GAS']
Energy_Sources_Database['LPG'] = Energy_Sources_Database['LIQUEFIED PETROLEUM GAS']
Energy_Sources_Database['NG'] = Energy_Sources_Database['NATURAL GAS']
Energy_Sources_Database['CH4'] = Energy_Sources_Database['METHANE']
Energy_Sources_Database['C3H8'] = Energy_Sources_Database['PROPANE']
Energy_Sources_Database['C4H10'] = Energy_Sources_Database['BUTANE']


## Función para convertir unidades del sistema internacional a otra especificada
def convert_SI_units(input_value, goal_units):
    if goal_units == 'K':
        return input_value
    if goal_units == 'J':
        return input_value
    if goal_units == 'J/kg':
        return input_value
    if goal_units == 'Pa':
        return input_value
    if goal_units == 'W':
        return input_value
    if goal_units == 'm2':
        return input_value
    if goal_units == 'm3':
        return input_value
    if goal_units == 'kg':
        return input_value
    if goal_units == 'm3/s':
        return input_value
    if goal_units == 'kg/s':
        return input_value
    if goal_units == 'C':
        return input_value - 273.15
    if goal_units == 'F':
        return (input_value - 273.15)*9/5 + 32
    if goal_units == 'ton':
        return input_value/1e3
    if goal_units == 'lb':
        return input_value*2.20462
    if goal_units == 'ha':
        return input_value/1e4
    if goal_units == 'L':
        return input_value*1e3
    if goal_units == 'gal':
        return input_value*1e3/3.785411784
    if goal_units == 'ft3':
        return input_value/0.02831684
    if goal_units == 'kWh':
        return input_value/3.6e6
    if goal_units == 'MWh':
        return input_value/3.6e9
    if goal_units == 'BTU':
        return input_value/1055.056
    if goal_units == 'kBTU':
        return input_value/1.055056e6
    if goal_units == 'MBTU':
        return input_value/1.055056e9
    if goal_units == 'kJ':
        return input_value/1e3
    if goal_units == 'MJ':
        return input_value/1e6
    if goal_units == 'TJ':
        return input_value/1e9
    if goal_units == 'kJ/kg':
        return input_value/1e3
    if goal_units == 'atm':
        return input_value/101325
    if goal_units == 'mmHg':
        return input_value/133.322
    if goal_units == 'psi':
        return input_value*1.45038e-4
    if goal_units == 'kpsi':
        return input_value*1.45038e-7
    if goal_units == 'kPa':
        return input_value/1e3
    if goal_units == 'bar':
        return input_value/1e5
    if goal_units == 'MPa':
        return input_value/1e6
    if goal_units == 'kW':
        return input_value/1e3
    if goal_units == 'MW':
        return input_value/1e6
    if goal_units == 'BTU/h':
        return input_value*3.41
    if goal_units == 'kBTU/h':
        return input_value*3.41e-3
    if goal_units == 'MBTU/h':
        return input_value*3.41e-6
    if goal_units == 'kJ/h':
        return input_value*3.6
    if goal_units == 'MJ/h':
        return input_value*3.6e-3
    if goal_units == 'kg/h':
        return input_value*3.6e3
    if goal_units == 'kg/min':
        return input_value*60
    if goal_units == 'ton/h':
        return input_value*3.6
    if goal_units == 'ton/min':
        return input_value*6e-2
    if goal_units == 'ton/s':
        return input_value/1e3
    if goal_units == 'lb/h':
        return input_value*7936.6414387
    if goal_units == 'lb/min':
        return input_value*132.27735731
    if goal_units == 'lb/s':
        return input_value*2.2046226218
    if goal_units == 'L/h':
        return input_value*3.6e6
    if goal_units == 'L/min':
        return input_value*6e4
    if goal_units == 'L/s':
        return input_value*1e3
    if goal_units == 'm3/h':
        return input_value*3.6e3
    if goal_units == 'm3/min':
        return input_value*6e1
    if goal_units == 'gal/h':
        return input_value*3.6e6/3.785411784
    if goal_units == 'gal/min':
        return input_value*6e4/3.785411784
    if goal_units == 'gal/s':
        return input_value/3.785411784e-3
    if goal_units == 'ft3/s':
        return input_value*2.83168e-2
    if goal_units == 'ft3/min':
        return input_value*6e3/2.83168
    if goal_units == 'ft3/h':
        return input_value*3.6e5/2.83168
    raise UnitConversionError("convert_SI_units: Units provided are not available.")

## Función para convertir unidades al sistema internacional
def convert_to_SI_units(input_value, original_units):
    if original_units == 'K':
        return input_value
    if original_units == 'J':
        return input_value
    if original_units == 'J/kg':
        return input_value
    if original_units == 'Pa':
        return input_value
    if original_units == 'W':
        return input_value
    if original_units == 'm2':
        return input_value
    if original_units == 'm3':
        return input_value
    if original_units == 'kg':
        return input_value
    if original_units == 'm3/s':
        return input_value
    if original_units == 'kg/s':
        return input_value
    if original_units == 'C':
        return input_value + 273.15
    if original_units == 'F':
        return (input_value - 32)*5/9 + 273.15
    if original_units == 'ton':
        return input_value*1e3
    if original_units == 'lb':
        return input_value/2.20462
    if original_units == 'ha':
        return input_value*1e4
    if original_units == 'L':
        return input_value/1e3
    if original_units == 'gal':
        return input_value*3.785411784e-3
    if original_units == 'ft3':
        return input_value*2.831684e-2
    if original_units == 'kWh':
        return input_value*3.6e6
    if original_units == 'MWh':
        return input_value*3.6e9
    if original_units == 'BTU':
        return input_value*1055.056
    if original_units == 'kBTU':
        return input_value*1.055056e6
    if original_units == 'MBTU':
        return input_value*1.055056e9
    if original_units == 'kJ':
        return input_value*1e3
    if original_units == 'MJ':
        return input_value*1e6
    if original_units == 'TJ':
        return input_value*1e9
    if original_units == 'kJ/kg':
        return input_value*1e3
    if original_units == 'atm':
        return input_value*101325
    if original_units == 'mmHg':
        return input_value*133.322
    if original_units == 'psi':
        return input_value/1.45038e-4
    if original_units == 'kpsi':
        return input_value/1.45038e-7
    if original_units == 'kPa':
        return input_value*1e3
    if original_units == 'bar':
        return input_value*1e5
    if original_units == 'MPa':
        return input_value*1e6
    if original_units == 'kW':
        return input_value*1e3
    if original_units == 'MW':
        return input_value*1e6
    if original_units == 'BTU/h':
        return input_value/3.41
    if original_units == 'kBTU/h':
        return input_value/3.41e-3
    if original_units == 'MBTU/h':
        return input_value/3.41e-6
    if original_units == 'kJ/h':
        return input_value/3.6
    if original_units == 'MJ/h':
        return input_value/3.6e-3
    if original_units == 'kg/h':
        return input_value/3.6e3
    if original_units == 'kg/min':
        return input_value/6e1
    if original_units == 'ton/h':
        return input_value/3.6
    if original_units == 'ton/min':
        return input_value*1e2/6
    if original_units == 'ton/s':
        return input_value*1e3
    if original_units == 'lb/h':
        return input_value/7936.6414387
    if original_units == 'lb/min':
        return input_value/132.27735731
    if original_units == 'lb/s':
        return input_value/2.2046226218
    if original_units == 'L/h':
        return input_value/3.6e6
    if original_units == 'L/min':
        return input_value/6e4
    if original_units == 'L/s':
        return input_value/1e3
    if original_units == 'm3/h':
        return input_value/3.6e3
    if original_units == 'm3/min':
        return input_value/6e1
    if original_units == 'gal/h':
        return input_value*3.785411784/3.6e6
    if original_units == 'gal/min':
        return input_value*3.785411784/6e4
    if original_units == 'gal/s':
        return input_value*3.785411784/1e3
    if original_units == 'ft3/s':
        return input_value*2.83168e-2
    if original_units == 'ft3/min':
        return input_value*2.83168e-3/6
    if original_units == 'ft3/h':
        return input_value*2.83168e-5/3.6
    raise UnitConversionError("convert_to_SI_units: Units provided are not available.")

## Función para convertir cualquier par de unidades
def convert_units(input_value, original_units, goal_units, density = None):
    if density == None:
        SI_value = convert_to_SI_units(input_value, original_units)
        return convert_SI_units(SI_value, goal_units)
    elif original_units == goal_units:
        return input_value
    elif ( original_units in [ 'L/h', 'L/min', 'L/s', 'm3/h', 'm3/min', 'm3/s', 'gal/h', 'gal/min', 'gal/s', 'ft3/h', 'ft3/min', 'ft3/s' ] and 
           goal_units in [ 'L/h', 'L/min', 'L/s', 'm3/h', 'm3/min', 'm3/s', 'gal/h', 'gal/min', 'gal/s', 'ft3/h', 'ft3/min', 'ft3/s' ] ):
        SI_value = convert_to_SI_units(input_value, original_units)
        return convert_SI_units(SI_value, goal_units)
    elif ( original_units in [ 'kg/h', 'kg/min', 'kg/s', 'ton/h', 'ton/min', 'ton/s', 'lb/h', 'lb/min', 'lb/s' ] and
           goal_units in [ 'kg/h', 'kg/min', 'kg/s', 'ton/h', 'ton/min', 'ton/s', 'lb/h', 'lb/min', 'lb/s' ] ):
        SI_value = convert_to_SI_units(input_value, original_units)
        return convert_SI_units(SI_value, goal_units)
    elif ( original_units in [ 'kg/h', 'kg/min', 'kg/s', 'ton/h', 'ton/min', 'ton/s', 'lb/h', 'lb/min', 'lb/s' ] and
           goal_units in [ 'L/h', 'L/min', 'L/s', 'm3/h', 'm3/min', 'm3/s', 'gal/h', 'gal/min', 'gal/s', 'ft3/h', 'ft3/min', 'ft3/s' ] ):
        flow_kg_s = convert_to_SI_units(input_value, original_units)
        flow_m3_s = flow_kg_s/density
        return convert_SI_units(flow_m3_s, goal_units)
    elif ( original_units in [ 'L/h', 'L/min', 'L/s', 'm3/h', 'm3/min', 'm3/s', 'gal/h', 'gal/min', 'gal/s', 'ft3/h', 'ft3/min', 'ft3/s' ] and
           goal_units in [ 'kg/h', 'kg/min', 'kg/s', 'ton/h', 'ton/min', 'ton/s', 'lb/h', 'lb/min', 'lb/s' ] ):
        flow_m3_s = convert_to_SI_units(input_value, original_units)
        flow_kg_s = flow_m3_s*density
        return convert_SI_units(flow_kg_s, goal_units)
    elif ( original_units in [ 'L', 'm3', 'ft3', 'gal' ] and 
           goal_units in [ 'L', 'm3', 'ft3', 'gal' ] ):
        SI_value = convert_to_SI_units(input_value, original_units)
        return convert_SI_units(SI_value, goal_units)
    elif ( original_units in [ 'kg', 'ton', 'lb' ] and
           goal_units in [ 'kg', 'ton', 'lb' ] ):
        SI_value = convert_to_SI_units(input_value, original_units)
        return convert_SI_units(SI_value, goal_units)
    elif ( original_units in [ 'kg', 'ton', 'lb' ] and
           goal_units in [ 'L', 'm3', 'ft3', 'gal' ] ):
        q_kg = convert_to_SI_units(input_value, original_units)
        q_m3 = q_kg/density
        return convert_SI_units(q_m3, goal_units)
    elif ( original_units in [ 'L', 'm3', 'ft3', 'gal' ] and
           goal_units in [ 'kg', 'ton', 'lb' ] ):
        q_m3 = convert_to_SI_units(input_value, original_units)
        q_kg = q_m3*density
        return convert_SI_units(q_kg, goal_units)
    raise UnitConversionError("convert_units: Units provided are not available.")

def mean_squared_error(list_1, list_2):
    """
    Function that computes the mean squared error between two lists of the same length.

    Parameters
    ----------
    list_1 : list
        First list.
    list_2 : list
        Second list.

    Raises
    ------
    SHIPcalError
        When the arguments are not two lists of the same length.

    Returns
    -------
    float
        Error result.

    """
    if not (type(list_1) is list and type(list_2) is list and len(list_1) == len(list_2)):
        raise SHIPcalError("Arguments of the funcion must be two lists of the same length.")
    if len(list_1) == 0:
        return 0.0
    return sum([ ( list_1[i] - list_2[i] )**2 for i in range(len(list_1)) ])/len(list_1)