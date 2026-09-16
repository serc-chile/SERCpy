# -*- coding: utf-8 -*-
"""
Created on Mon Aug 17 12:33:21 2026

@author: adria
"""

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