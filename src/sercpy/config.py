# -*- coding: utf-8 -*-
"""
Created on Mon Aug 17 09:46:38 2026

@author: Adrian Riebel Brummer
"""

from pathlib import Path

default_year = 2025

kwargs_list = [
    
    'solar_field',
    'storage_tank',
    'heat_exchanger_1',
    'heat_exchanger_2',
    'boiler',
    'op_conditions',
    
    'demand_profile',
    
    'latitude',
    'longitude',
    
    'TMY_file_path',
    'GHI_column_name',
    'DNI_column_name',
    'DHI_column_name',
    'Tamb_column_name',
    'zenith_column_name',
    'azimuth_column_name',
    
    'fuel_name',
    'fuel_consumption',
    'fuel_consumption_units',
    
    'hot_water_demand',
    'hot_water_demand_units',
    
    'energy_demand',
    'energy_demand_units',
    
    'coll_n0',
    'coll_a1',
    'coll_a2',
    'coll_test_flowrate',
    'coll_IAM_K',
    'coll_IAM_Kl',
    'coll_IAM_Kt',
    'coll_b',
    'coll_b0',
    'coll_b1',
    'coll_b2',
    
    'coll_rows',
    'colls_per_row',
    'coll_tilt',
    'coll_azimuth',
    'row_spacing',
    'non_shadeable_rows',
    'non_shadeable_rows_fraction',
    
    'solar_field_fluid',
    'solar_field_pressure',
    'solar_field_op_flowrate',
    
    'tank_volume',
    'tank_aspect_ratio',
    'tank_height',
    'tank_diameter',
    'tank_loss_coeff',
    'tank_top_loss_coeff',
    'tank_edge_loss_coeff',
    'tank_bottom_loss_coeff',
    'tank_inlet_flow_model',
    'tank_flow_alloc_coeff',
    
    ]

_API_Key_folder = Path.home() / ".sercpy"

def set_api_key( api_key ):
    """
    Function that allows the user to permanently store their API key for `Renewable Energies API by Chilean Ministriy of Energy <https://api.minenergia.cl/>`_

    Parameters
    ----------
    api_key : str
        User's API key.

    Returns
    -------
    None.

    """
    if not type(api_key) is str:
        raise ValueError("sercpy.config.set_api_key: api_key must be a string.")
    _API_Key_folder.mkdir( exist_ok = True )
    with open( _API_Key_folder / 'API_Key.txt', 'w' ) as api_key_file:
        api_key_file.write(api_key)
        
def get_api_key():
    """
    Function to retrieve the API key for `Renewable Energies API by Chilean Ministriy of Energy <https://api.minenergia.cl/>`_ previously stored by the user.
    
    Returns
    -------
    api_key : str or NoneType
        User's API key. The function returns None if no API key can be found.
    
    """
    
    if Path.is_file( _API_Key_folder / 'API_Key.txt' ):
        with open( _API_Key_folder / 'API_Key.txt' ) as api_key_file:
            api_key = api_key_file.read()
    else:
        api_key = None
    
    return api_key

demand_Tset_limits = [ 25, 150 ]
demand_Tin_limits = [ 2, 130 ]