# -*- coding: utf-8 -*-
"""
Created on Mon Aug 17 22:08:31 2026

@author: adria
"""


import requests
import json
import pandas as pd
from datetime import datetime
import numpy as np
from .core import SHIPcalError
from pvlib.solarposition import get_solarposition

class LocationError(Exception):
    pass
    

def download_TMY(latitude, longitude, API_KEY):
    """
    Function to contact 'API Energias Renovables' (url: https://api.minenergia.cl/) from the Ministry of Energy of Chile.
    
    It downloads a TMY (typical meteorological year) data file produced by that site and produces a pandas.DataFrame object with the the components: GHI, DNI, DHI, and ambient temperature.

    Parameters
    ----------
    latitude : int or float
        Latitude of the location.
    longitude : int or float
        Longitude of the location.
    API_KEY : str
        API key for the 'API Energias Renovables' website.

    Raises
    ------
    SHIPcalError
        Errors such as connection error, timeout error, incorrect API key, etc. Also raised when the latitude or longitude provided cannot be interpreted as floating point values.
    LocationError
        If the site 'API Energias Renovables' is not able to produce the data requested because the location porvided is out of the allowed range.

    Returns
    -------
    df : pandas.DataFrame
        DataFrame containing the the data of a typical meteorological year (TMY) with the components: GHI, DNI, DHI, and ambient temperature. It has 8760 rows, one for each hour of a year.
    elevation : float
        Elevation (in meters) of the specified location.

    """
    
    try:
        latitude = float(latitude)
        longitude = float(longitude)
    except:
        raise SHIPcalError("Function download_TMY: Parameters 'latitude' and 'longitude' must be convertible to type 'float'.")
    
    # API's url
    url = "https://api.exploradorenergia.cl/api/proxy"
    
    # Request header
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Token {API_KEY}"
    }
    
    # Request body data
    payload = {
        "action": {
            "action": "series",
            "interval": "hour",
            "stat": "mean",
            "tmy": True
        },
        "period": {
            "start": "1980-01-01",
            "end": "2017-12-31"
        },
        "export": {
            "label": "datos",
            "format": "csv"
        },
        "variables": [
            {
                "id": "ghi",
                "options": {
                    "label": "GHI",
                    "stat": "default",
                    "band": "full",
                    "clearsky": False,
                    "fill_missing": True
                }
            },
            {
                "id": "dni",
                "options": {
                    "label": "DNI",
                    "stat": "default",
                    "band": "full",
                    "clearsky": False,
                    "fill_missing": True
                }
            },
            {
                "id": "dif",
                "options": {
                    "label": "DHI",
                    "stat": "default",
                    "band": "full",
                    "clearsky": False,
                    "fill_missing": True,
                    "receptor": {
                        "type": "hori",
                        "azimuth": 0,
                        "elev1": 0,
                        "elev2": 0,
                        "hsatmax": 45,
                        "optimize": False,
                        "optimize_on_rglb": False
                    }
                }
            },
            {
                "id": "tempc",
                "options": {
                    "label": "T_amb",
                    "stat": "default",
                    "recon": "on"
                }
            }
        ],
        "position": [
            {
                "label": "S1",
                "type": "point",
                "lon": longitude,
                "lat": latitude
            }
        ]
    }
    
    try:
        # Carry out POST request
        response = requests.post(url, headers=headers, json=payload, timeout = (10, 40))
        
        # Verify response status code
        if response.status_code == 200:
            # Convert response to python dictionary
            response_data = json.loads(response.text)
            
            csv_url = response_data.get('url')
            
            if not csv_url:
                print(f"response_data: {response_data}")
                raise LocationError("Function download_TMY: No url was received from 'API Energias Renovables' (url: https://api.minenergia.cl/). Probably, the location provided is outside the accepted range.")
                
            # Download CSV content
            csv_response = requests.get(csv_url)
            if csv_response.status_code == 200:
                # Process CSV content
                
                file_content = csv_response.text
                lines = file_content.split('\n')
                variable_list = ['Date'] + [ payload['variables'][i]['options']['label'] for i in range(len(payload['variables'])) ]
                data = { variable_list[i]: [] for i in range(len(variable_list)) } 
                data_start = False
                extract_elevation = False
                for line in lines:
                    if extract_elevation:
                        line_list = line.split(',')
                        elevation = float(line_list[-1])
                        extract_elevation = False
                    if line.startswith('Nombre,Longitud,Latitud,Altura Terreno (m)'):
                        extract_elevation = True
                    if line.startswith('FECHA'):
                        data_start = True
                    elif data_start and line.strip():
                        line_list = line.split(',')
                        assert len(line_list) == len(variable_list)
                        for i in range(len(variable_list)):
                            if i == 0:
                                data[variable_list[i]].append(line_list[i])
                            else:
                                data[variable_list[i]].append(float(line_list[i]))
                
                df = pd.DataFrame.from_dict(data)
                
                return df, elevation
            
    # Manage errors
            
            else:
                raise SHIPcalError("Function download_TMY: The data could not be downloaded from the url provided by 'API Energias Renovables' (url: https://api.minenergia.cl/). Check your internet connection and try again later.")
                
        else:
            if response.status_code == 403:
                raise SHIPcalError("Function download_TMY: The data could not be downloaded from 'API Energias Renovables' (url: https://api.minenergia.cl/). Response status code: 403 (non-valid API Key)")
            else:
                raise SHIPcalError(f"Function download_TMY: The data could not be downloaded from 'API Energias Renovables' (url: https://api.minenergia.cl/). Response status code: {response.status_code}")
        
    except requests.exceptions.ConnectionError:
        raise SHIPcalError("Function download_TMY: Could not connect to the server. Check your internet connection and try again later.")
        
    except requests.exceptions.Timeout:
        raise SHIPcalError("Function download_TMY: The server took too long to respond.")
        
    except requests.exceptions.RequestException as e:
        raise SHIPcalError("Function download_TMY: A requests/network error occurred:", e)
        
    except:
        raise SHIPcalError("Function download_TMY: An unknown exception occurred when contacting 'API Energias Renovables' (url: https://api.minenergia.cl/).")

def average_azimuth(azimuth_list):
    """
    Function that averages a list of azimuthal solar position values. 
    
    The function corrects potential bugs that could be produced at solar midday in the southern hemisphere, due to the fact that the sun 

    Parameters
    ----------
    azimuth_list : TYPE
        DESCRIPTION.

    Raises
    ------
    SHIPcalError
        DESCRIPTION.

    Returns
    -------
    result : TYPE
        DESCRIPTION.

    """
    midday_found = False
    correction_type = None
    corrected_list = []
    for i in range(len(azimuth_list)):
        if i == 0:
            corrected_list.append( azimuth_list[i] )
            continue
        if abs( azimuth_list[i] - azimuth_list[i - 1] ) > 180:
            if midday_found:
                raise SHIPcalError("Function average_azimuth: midday found two times in a list.")
            if azimuth_list[i - 1] > azimuth_list[i]:
                correction_type = 'above_360'
            else:
                correction_type = 'below_0'
            midday_found = True
        if correction_type is None:
            corrected_list.append( azimuth_list[i] )
            continue
        if correction_type == 'below_0':
            corrected_list.append( azimuth_list[i] - 360 )
            continue
        corrected_list.append( 360 + azimuth_list[i] )
    
    result = float(np.mean(corrected_list))
    if result < 0:
        result = 360 + result
    elif result > 360:
        result = result - 360
    
    return result
    
class MeteoProfile:
    
    def __init__(self, **kwargs):
        
        if "location" in kwargs:
            try:
                assert type(kwargs["location"]) is tuple and len(kwargs["location"]) == 2
                self._latitude = float(kwargs["location"][0])
                self._longitude = float(kwargs["location"][1])
            except:
                raise ValueError("Class MeteoProfile: Argument 'location' must be a tuple and both values must be convertible to type 'float'. The values correspond to (latitude, longitude).")
                
        elif "latitude" in kwargs or "longitude" in kwargs:
            
            try:
                assert "latitude" in kwargs and "longitude" in kwargs
            except:
                raise SHIPcalError("Class MeteoProfile: Arguments 'latitude' and 'longitude' must be specified together.")
            try:
                self._latitude = kwargs["latitude"]
                self._longitude = kwargs["longitude"]
            except:
                raise ValueError("Class MeteoProfile: Arguments 'latitude' and 'longitude' must be convertible to type 'float'.")
        
        if "solar_field" in kwargs:
            
            self._solar_field = kwargs["solar_field"]
            
        if "date_format" in kwargs:
            
            pass
            
        if "utc_offset_jan" in kwargs:
            
            pass
            
        elif "tz" in kwargs or "timezone" in kwargs:
            
            if "tz" in kwargs:
                
                pass
                #self._timezone = 
            
            "timezone" in kwargs
    
    def set_time_step(self, time_step):
        if hasattr(self, "_time_step") and self._time_step == time_step:
            return
        try:
            assert type(time_step) is int and time_step in [ 1, 2, 3, 4, 5, 6, 10, 12, 15, 20, 30, 60 ]
        except:
            raise SHIPcalError("DemandProfile.set_time_step: time_step (in minutes) must be an integer within the possible values: 1, 2, 3, 4, 5, 6, 10, 12, 15, 20, 30, and 60")
        self._time_step = time_step
        self._time_steps_per_year = 8760*60//time_step
        self.update_effective_profiles()
        
    def update_effective_profiles(self):
        
        self.update_effective_solar_position_profiles()
    
    def update_effective_solar_position_profiles(self):
        
        for attribute_name in [
                
                "_zenith_profile_minutal",
                "_azimuth_profile_minutal",
                "_time_step",
                "_time_steps_per_year",
                
                ]:
            
            if not hasattr(self, attribute_name):
                return
        
        self._zenith_profile = [ float(np.mean( self._zenith_profile_minutal[ initial_minute : initial_minute + self._time_step ] ) ) for initial_minute in range(0, self._time_steps_per_year, self._time_step ) ]
        self._azimuth_profile = [ average_azimuth( self._azimuth_profile_minutal[ initial_minute : initial_minute + self._time_step ] ) for initial_minute in range(0, self._time_steps_per_year, self._time_step ) ]
    
    def update_minutal_solar_position_profiles(self):
        
        for attribute_name in [
                
                "_latitude",
                "_longitude",
                "_UTC" ]:
            
            if not hasattr(self, attribute_name):
                return
            
        if self._UTC == 0:
            tz_string = 'Etc/GMT'
        elif self._UTC < 0:
            tz_string = f'Etc/GMT+{abs(self._UTC)}'
        else:
            tz_string = f'Etc/GMT-{self._UTC}'
        
        times = pd.date_range(start = '2022-01-01 00:00:00', end = '2023-01-01 00:00:00', freq = 'min', inclusive = 'left', tz = tz_string)
        solPos = get_solarposition(times, self.latitude, self.longitude)
        self._zenith_profile_minutal = solPos[ 'apparent_zenith' ].astype(float).tolist()
        self._azimuth_profile_minutal = solPos[ 'azimuth' ].astype(float).tolist()
        self.update_effective_solar_position_profiles()
        
    def set_UTC(self, UTC):
        
        try:
            assert type(UTC) is int and UTC >= -12 and UTC <= 14
        except AssertionError:
            raise SHIPcalError("MeteoProfile.set_UTC: UTC value must be an integer greater than or queal to -12, and smaller than or equal to 14.")
        
        self._UTC = UTC
        self.update_minutal_solar_position_profiles()
    
    def set_location(self, latitude, longitude):
        
        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except:
            raise ValueError("MeteoProfile.set_location: Parameters 'latitude' and 'longitude' must be convertible to type 'float'.")
        
        try:
            assert latitude >= -90 and latitude <= 90 and longitude >=-180 and longitude <= 180
        except:
            raise ValueError("MeteoProfile.set_location: 'latitude' value must be between -90 and 90. 'longitude' value must be between -180 and 180.")
        
        self._latitude = latitude
        self._longitude = longitude
        self.update_minutal_solar_position_profiles()
        
    def load_TMY(self, **kwargs):
        
        if 'TMY_file_name' in kwargs:
            if 'GHI_column_name' in kwargs or 'DNI_column_name' in kwargs or  'DHI_column_name' in kwargs:
                try:
                    assert 'UTC' in kwargs and 'Tamb_column_name' in kwargs and (
                        
                        ('GHI_column_name' in kwargs and 'DNI_column_name' in kwargs) or 
                        ('DNI_column_name' in kwargs and 'DHI_column_name' in kwargs) or 
                        ('GHI_column_name' in kwargs and 'DHI_column_name' in kwargs)
                        
                        )
                
                except:
                    raise SHIPcalError("MeteoProfile.load_TMY: Custom TMY files must have an ambient temperature column and at least two of three irradiance components (GHI, DNI, DHI)")
        