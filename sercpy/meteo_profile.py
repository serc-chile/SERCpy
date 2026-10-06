# -*- coding: utf-8 -*-
"""
Created on Mon Aug 17 22:08:31 2026

@author: Adrian Riebel Brummer
"""

from .core import month_days
from math import pi
from numpy import arctan, tan, sin, cos
from typing import Optional
from pathlib import Path
import requests
import json
import pandas as pd
from datetime import datetime
import numpy as np
from pvlib.solarposition import get_solarposition
from pvlib.atmosphere import get_relative_airmass
from pvlib.irradiance import get_extra_radiation, perez
from scipy.integrate import quad, nquad
from scipy.interpolate import interp1d
from .config import get_api_key
from .config import coordinates_tolerance
from .units import convert_units
from timezonefinder import timezone_at
from .solar_field import SolarField
import warnings
from zoneinfo import ZoneInfo

class TMY_Error(Exception):
    pass

class TimeZoneError(Exception):
    pass

class OutOfChileError(Exception):
    pass

class FileFormatError(Exception):
    pass

class LocationNeeded(Exception):
    pass



MeteoProfile_valid_args = [
    
    "location",
    "latitude",
    "longitude",
    
    "ground_albedo",
    
    "api_key",
    
    "tmy_file_path",
    "ghi_col_name",
    "dni_col_name",
    "dhi_col_name",
    "Tamb_col_name",
    "tmy_utc_offset",
    "sep",
    "delimiter",
    "skiprows",
    
    "irradiance_units",
    "temp_units",
    "T_units",
    
    "elevation",
    "elevation_units",
    
    "solar_field",
    
    "tz",
    "time_zone",
    
    ]


    
class MeteoProfile:
    """
    Class that imports, computes and stores the meteorological conditions during an entire year, on a certain location.
    
    The class is meant to work with TMY (typical meteorological year) data. Time resolutions accepted for user-provided data range from 1 minute (maximal resolution) to 1 hour (minimal resolution).
    
    For simulations within the Chilean territory, the class is able to automatically download TMY data, provided that the user owns an API key for `Ministry of Energy's "Renewable Energies API" <https://api.minenergia.cl/>`__.
    
    The class works for any location on the planet; however, for places outside Chile, the user must provide the meteorological data. The time zone is automatically inferred from the location, unless manually provided by the user; this includes eventual time changes due to daylight saving time.
    
    Parameters
    ----------
    
    location : tuple of two float, optional
        Tuple with the form `(latitude, longitude)` defining the place where the simualtion will be performed. Only needed when: (1) the user provides a custom-format file, or (2) the TMY is downloaded internally by the class instance from `Ministry of Energy's "Renewable Energies API" <https://api.minenergia.cl/>`__.
    latitude : float, optional
        If provided along with `longitude`, it is a substitute for the argument `location`.
    longitude : float, optional
        If provided along with `latitude`, it is a substitute for the argument `location`.
    ground_albedo : float, optional
        Irradiance fraction refelcted by the ground. If not provided, it defaults to 0.2.
    api_key : str, optional
        User's API key for `Ministry of Energy's "Renewable Energies API" <https://api.minenergia.cl/>`__. Only needed when no data file is provided by the user. An alternative to providing this argument is using the function `config.set_api_key` to store the key permanently.
    tmy_file_path : str, optional
        Path of the user-provided csv data file. If the file does not align with one of the standard formats known to the platform (see the :doc:`tutorial about the class <examples/MeteoProfile_tutorial>`, Section 1, for more information), then the next arguments, up to `elevation_units`, might be useful to the user.
        In the next arguments, the terms 'custom format' and 'custom file' refers to any csv file that does not have the `SAM <https://sam.nlr.gov/>`__ nor the `Solar Explorer <https://solar.minenergia.cl/inicio>`__ form.
    ghi_col_name : str, optional
        Name of the GHI (global horizontal irradiance) column of the csv file. Only needed for custom files, in which the name of this column is different from 'GHI'.
    dni_col_name : str, optional
        Name of the DNI (direct normal irradiance) column of the csv file. Only needed for custom files, in which the name of this column is different from 'DNI'.
    dhi_col_name : str, optional
        Name of the DHI (diffuse horizontal irradiance) column of the csv file. Only needed for custom files, in which the name of this column is different from 'DHI'.
    Tamb_col_name : str, optional
        Name of the ambient temperature column of the csv file. Only needed for custom files, in which the name of this column is different from 'Tamb'.
    tmy_utc_offset : str, optional
        UTC offset of the data in the csv file provided by the user. Only needed for custom files. If not provided, this parameter will be inferred from the location; however, this can lead to large errors.
    sep : str, optional
        Same effect as in the function `pandas.read_csv <https://pandas.pydata.org/docs/reference/api/pandas.read_csv.html>`__. Only considered when a custom csv file is provided by the user.
    delimiter : str, optional
        Alias for `sep`.
    skiprows : int, optional
        Same effect as in the function `pandas.read_csv <https://pandas.pydata.org/docs/reference/api/pandas.read_csv.html>`__. Only considered when a custom csv file is provided by the user.
    irradiance_units : str, optional
        Units in which irradiance is expressed in the csv file. Only considered when a custom csv file is provided by the user. If not provided, 'W/m2' is assumed.
    temp_units : str, optional
        Units in which ambient temperature is expressed in the csv file. Only considered when a custom csv file is provided by the user. If not provided, '°C' is assumed.
    T_units : str, optional
        Alias for temp_units.
    elevation : float, optional
        Terrain elevation of the place where the TMY is taken from. It is used to compute the atmospheric pressure in that location. If not provided, the value 0 is assumed.
    elevation_units : str, optional
        Units in which elevation is being provided. If not provided, 'm' is assumed.
    tz : 
        
    time_zone : 
        
    solar_field : 
        
        
    """
    
    def __init__(
            
            self, 
            *,
            
            location: Optional[ tuple ] = None,
            latitude: Optional[ float ] = None,
            longitude: Optional[ float ] = None,
            
            ground_albedo: Optional[ float ] = None,
            
            api_key: Optional[ str ] = None,
            
            tmy_file_path: Optional[ str | Path ] = None,
            ghi_col_name: Optional[ str ] = None,
            dni_col_name: Optional[ str ] = None,
            dhi_col_name: Optional[ str ] = None,
            Tamb_col_name: Optional[ str ] = None,
            tmy_utc_offset: Optional[ str ] = None,
            sep: Optional[ str ] = None,
            delimiter: Optional[ str ] = None,
            skiprows: Optional[ int ] = None,
            
            irradiance_units: Optional[ str ] = None,
            temp_units: Optional[ str ] = None,
            T_units: Optional[ str ] = None,
            
            elevation: Optional[ float ] = None,
            elevation_units: Optional[ str ] = None,
            
            solar_field: Optional[ SolarField ] = None,
            
            tz: Optional[ str ] = 'auto',
            time_zone: Optional[ str ] = 'auto',
            
            **kwargs):
        
        self.irradiance_columns = [ 
            
            'GHI', 'DNI', 'DHI',
            'irradiance_first_row', 'irradiance_shadeable_rows' ]
        
        self.temp_columns = [ 'Tamb', 'Tmains' ]
        
        self.angle_columns = [ 'azimuth', 'zenith', 'apparent_zenith',
                               'aoi', 'aoi_l', 'aoi_t' ]
        
        # If location is provided
        if location is not None:
            
            self._latitude, self._longitude = self.validate_argument("location", location)
        
        # If latitude and longitude are provided
        elif latitude is not None or longitude is not None:
            
            if latitude is None or longitude is None:
                raise ValueError("Class MeteoProfile: latitude and longitude must be provided together.")
            
            self._latitude = self.validate_argument( "latitude", latitude )
            self._longitude = self.validate_argument( "longitude", longitude )
        
        # Else, it is expected that tmy_file_path is provided and that the file specifies the location.
        # Hence, it is necessary that the file has a format known to the platform ("solar_explorer" or "SAM")
        else:
            
            if tmy_file_path is None:
                raise ValueError("Class MeteoProfile: A meteorological data file must be provided if no location is provided.")
            
            self._latitude = None
            self._longitude = None
            
        self._ground_albedo = self.validate_argument("ground_albedo", ground_albedo)
        if self._ground_albedo is None:
            self._ground_albedo = 0.2
        
        self._api_key = self.validate_argument("api_key", api_key)
        
        self._tmy_file_path = self.validate_argument("tmy_file_path", tmy_file_path)
        
        self._ghi_col_name = self.validate_argument("ghi_col_name", ghi_col_name)
        self._dni_col_name = self.validate_argument("dni_col_name", dni_col_name)
        self._dhi_col_name = self.validate_argument("dhi_col_name", dhi_col_name)
        self._Tamb_col_name = self.validate_argument("Tamb_col_name", Tamb_col_name)
        
        self._tmy_utc_offset = self.validate_argument("tmy_utc_offset", tmy_utc_offset)
        
        if sep is None and delimiter is not None:
            self._sep = self.validate_argument("delimiter", delimiter)
        else:
            self._sep = self.validate_argument( "sep", sep )
        
        self._skiprows = self.validate_argument( "skiprows", skiprows )
        
        self._irradiance_units = self.validate_argument( "irradiance_units", irradiance_units )
        if temp_units is None and T_units is not None:
            self._temp_units = self.validate_argument( "T_units", T_units )
        else:
            self._temp_units = self.validate_argument( "temp_units", temp_units )
        
        elevation = self.validate_argument( "elevation", elevation )
        elevation_units = self.validate_argument( "elevation_units", elevation_units )
        
        if elevation is not None and elevation_units is not None:
            self._elevation = convert_units( elevation, elevation_units, 'm' )
        elif elevation is not None:
            self._elevation = elevation
        else:
            self._elevation = 0
        
        self._solar_field = self.validate_argument( "solar_field", solar_field )
        
        if tz != "auto" and time_zone != "auto":
            raise ValueError("MeteoProfile: Argument 'time_zone' is an alternative name for 'tz'. Both arguments cannot be provided together.")
        elif tz != "auto":
            self._tz = self.validate_argument( "tz", tz )
        elif time_zone != "auto":
            self._tz = self.validate_argument( "time_zone", time_zone )
        else:
            self._tz = "auto"
        
        self._import_meteo_data()
        
        self.compute_T_mains_Profile()
        
        if self._solar_field is not None:
            self.compute_poa_irradiance( solar_field )
    
    @staticmethod
    def import_solar_explorer_file( tmy_file_path ):
        
        with open( tmy_file_path ) as file:
            
            line_counter = 0
            while (line := file.readline()):
                line_counter += 1
                if line_counter < 12:
                    continue
                line_list = line.rstrip("\n").split(',')
                if line_counter == 12:
                    if not line_list[0] == 'LATITUD':
                        raise FileFormatError("MeteoProfile.import_solar_explorer_file: 'LATITUD' not encountered in line 12 of the file.")
                    try:
                        latitude = float( line_list[1] )
                    except:
                        raise FileFormatError("MeteoProfile.import_solar_explorer_file: latitude could not be read in line 12 of the file.")
                if line_counter == 13:
                    if not line_list[0] == 'LONGITUD':
                        raise FileFormatError("MeteoProfile.import_solar_explorer_file: 'LONGITUD' not encountered in line 13 of the file.")
                    try:
                        longitude = float( line_list[1] )
                    except:
                        raise FileFormatError("MeteoProfile.import_solar_explorer_file: latitude could not be read in line 13 of the file.")
                if line_counter == 14:
                    if not line_list[0] == 'ALTURA':
                        raise FileFormatError("MeteoProfile.import_solar_explorer_file: 'ALTURA' not encountered in line 14 of the file.")
                    try:
                        elevation = float( line_list[1] )
                    except:
                        raise FileFormatError("MeteoProfile.import_solar_explorer_file: elevation could not be read in line 14 of the file.")
                    break
            
        df = pd.read_csv( tmy_file_path, skiprows = 41 )
        
        try:
            df = df.filter( [ 'ghi','dni','difh','temp' ] )
            df = df.rename( columns = {
                
                'ghi': 'GHI',
                'dni': 'DNI',
                'difh': 'DHI',
                'temp': 'Tamb',
                
                } )
        except:
            raise FileFormatError("MeteoProfile.import_solar_explorer_file: Solar Explorer file could not be processed.")
            
        if len( df ) != 8760:
            raise FileFormatError("MeteoProfile.import_solar_explorer_file: TMY data file is expected to have 8760 rows.")
            
        utc_offset = -4
        
        return latitude, longitude, elevation, utc_offset, df
        
    @staticmethod
    def import_SAM_file( tmy_file_path ):
        
        with open( tmy_file_path ) as file:
            
            line_counter = 0
            while (line := file.readline()):
                line_counter += 1
                if line_counter == 1:
                    continue
                line_list = line.rstrip("\n").split(',')
                try:
                    latitude, longitude, utc_offset, elevation = float( line_list[ 5 ] ), float( line_list[ 6 ] ), float( line_list[ 7 ] ), float( line_list[ 8 ] )
                except:
                    raise FileFormatError("MeteoProfile.import_SAM_file: Metadata could not be extracted from file (latitude, longitude, utc_offset, elevation).")
                break
            
        df = pd.read_csv( tmy_file_path, skiprows = 2 )
        
        try:
            df = df.filter( [ 'GHI','DNI','DHI','Tdry' ] )
            df = df.rename( columns = { 'Tdry': 'Tamb', } )
        except:
            raise FileFormatError("MeteoProfile.import_SAM_file: SAM-formatted file could not be processed.")
            
        return latitude, longitude, elevation, utc_offset, df
    
    @staticmethod
    def data_length_to_datetimes(
            
            data_length: int,
            tz: Optional[ str ] = None ):
        
        # Allowed df lengths:
            # 8760 -> 1 hr per value -> first value after 30 min
            # 8760*2 -> 1/2 hr per value -> first value after 15 min
            # 8760*3 -> 1/3 hr per value -> first value after 10 min
            # 8760*4 -> 1/4 hr per value -> first value after 7 min   30 sec
            # 8760*5 -> 1/5 hr per value -> first value after 6 min
            # 8760*6 -> 1/6 hr per value -> first value after 5 min
            # 8760*10 -> 1/10 hr per value -> first value after 3 min
            # 8760*12 -> 1/12 hr per value -> first value after 2 min 30 sec
            # 8760*15 -> 1/15 hr per value -> first value after 2 min
            # 8760*20 -> 1/20 hr per value -> first value after 1 min 30 sec
            # 8760*30 -> 1/30 hr per value -> first value after 1 min
            # 8760*60 -> 1/60 hr per value -> first value after       30 sec
        
        if data_length in [ 8760*factor for factor in [ 1, 2, 3, 5, 6, 10, 15, 30 ] ]:
            
            factor = data_length//8760
            assert 30%factor == 0
            first_minute = 30//factor
            last_minute = 60 - first_minute
            
            dt_start = datetime( year = 2025, month = 1, day = 1, hour = 0, minute = first_minute, second = 0 )
            dt_end = datetime( year = 2025, month = 12, day = 31, hour = 23, minute = last_minute, second = 0 )
            
        elif data_length == 8760*4:
            
            dt_start = datetime( year = 2025, month = 1, day = 1, hour = 0, minute = 7, second = 30 )
            dt_end = datetime( year = 2025, month = 12, day = 31, hour = 23, minute = 52, second = 30 )
        
        elif data_length == 8760*12:
            
            dt_start = datetime( year = 2025, month = 1, day = 1, hour = 0, minute = 2, second = 30 )
            dt_end = datetime( year = 2025, month = 12, day = 31, hour = 23, minute = 57, second = 30 )
        
        elif data_length == 8760*20:
            
            dt_start = datetime( year = 2025, month = 1, day = 1, hour = 0, minute = 1, second = 30 )
            dt_end = datetime( year = 2025, month = 12, day = 31, hour = 23, minute = 58, second = 30 )
        
        elif data_length == 8760*60:
            
            dt_start = datetime( year = 2025, month = 1, day = 1, hour = 0, minute = 0, second = 30 )
            dt_end = datetime( year = 2025, month = 12, day = 31, hour = 23, minute = 59, second = 30 )
        
        else:
            
            raise ValueError("MeteoProfile.data_length_to_datetimes: Length of DataFrame must be consistent with one year of data with one of the following time resolutions in minutes: 1, 2, 3, 4, 5, 6, 10, 12, 15, 20, 30, 60.")
        
        date_times = pd.date_range( dt_start, dt_end, periods = data_length, inclusive = 'both', tz = tz )
        
        return date_times
    
    @staticmethod
    def utc_offset_num_to_str( offset_num: float ) -> str:
        
        try:
            offset_num = float( offset_num )
        except TypeError:
            try:
                offset_num = str( offset_num )
            except:
                raise ValueError("MeteoProfile.utc_offset_num_to_str: offset_num must be convertible to type 'float', or any time zone name as string.")
            return offset_num
        
        if offset_num == 0:
            return 'UTC'
        
        elif offset_num > 0:
            utc_sign = '+'
        
        elif offset_num < 0:
            utc_sign = '-'
            offset_num = abs( offset_num )
            
        h = int( offset_num )
        m = int( np.round( (offset_num - h)*60 ) )
        
        return 'UTC' + utc_sign + '0'*( h < 10 ) + str( h ) + ':' + '0'*( m < 10 ) + str( m )
    
    @staticmethod
    def get_utc_offset( timezone = None, latitude = None, longitude = None, month = None ):
        
        if timezone is None:
            if latitude is None or longitude is None:
                raise ValueError("MeteoProfile.get_utc_offset: Latitude and longitude must be provided if no timezone is provided.")
            timezone = timezone_at(lng = longitude, lat = latitude)
        
        if month is None:
            if latitude >= 0:
                month = 1
            else:
                month = 7
        
        dt = datetime( year = 2025, month = month, day = 1, hour = 0, minute = 0, second = 0, tzinfo = ZoneInfo(timezone) )
        
        offset_seconds = int( dt.utcoffset().total_seconds() )
        
        if offset_seconds%3600 == 0:
            offset_hours = offset_seconds//3600
        else:
            offset_hours = offset_seconds/3600
        
        return offset_hours
    
    def _complete_irradiance_data( self ):
        
        df = self.get_attribute( "df_tmy" )
        latitude = self.get_attribute( "latitude" )
        longitude = self.get_attribute( "longitude" )
        utc_offset  = self.get_attribute( "tmy_utc_offset" )
        
        columns = df.columns.tolist()
        
        if 'GHI' in columns and 'DNI' in columns and 'DHI' in columns:
            
            return df
        
        if latitude is None or longitude is None:
            raise LocationNeeded("MeteoProfile._complete_irradiance_data: Latitude and longitude are needed when one of the irradiance columns is missing (GHI, DNI, DHI).")
        
        if not any( [
                
                'GHI' in columns and 'DNI' in columns,
                'DNI' in columns and 'DHI' in columns,
                'GHI' in columns and 'DHI' in columns,
                
                ] ):
            
            raise ValueError("MeteoProfile._complete_irradiance_data: At least two irradiance columns have to be present in the DataFrame from the three: GHI, DNI, DHI.")
        
        tz = MeteoProfile.utc_offset_num_to_str( utc_offset )
        
        date_times = MeteoProfile.data_length_to_datetimes( len( df ), tz = tz )
        
        zenith_list = get_solarposition(date_times, latitude, longitude)[ 'apparent_zenith' ].astype(float).tolist()
        zenith_list_rad = ( (pi/180)*np.array(zenith_list) ).astype( float ).tolist()
        
        assert len( zenith_list ) == len( df )
        
        # GHI = DNI cos(z) + DHI
        if 'GHI' in columns and 'DNI' in columns:
            GHI_list = df[ 'GHI' ].values.astype(float).tolist()
            DNI_list = df[ 'DNI' ].values.astype(float).tolist()
            DHI_list = []
            
            for i in range( len( GHI_list ) ):
                if zenith_list[i] > 90:
                    DHI_list.append( GHI_list[i] )
                else:
                    DHI_list.append( max( [ GHI_list[i] - DNI_list[i]*cos( zenith_list_rad[i] ) , 0 ] ) )
                    
            df[ 'DHI' ] = DHI_list
            
        elif 'DNI' in columns and 'DHI' in columns:
            DNI_list = df[ 'DNI' ].values.astype(float).tolist()
            DHI_list = df[ 'DHI' ].values.astype(float).tolist()
            GHI_list = []
            
            for i in range( len( DNI_list ) ):
                if zenith_list[i] > 90:
                    GHI_list.append( DHI_list[i] )
                else:
                    GHI_list.append( DNI_list[i]*cos( zenith_list_rad[i] ) + DHI_list[i] )
                    
            df[ 'GHI' ] = GHI_list
                    
        elif 'GHI' in columns and 'DHI' in columns:
            GHI_list = df[ 'GHI' ].values.astype(float).tolist()
            DHI_list = df[ 'DHI' ].values.astype(float).tolist()
            DNI_list = []
            
            for i in range( len( GHI_list ) ):
                if zenith_list[i] > 85:
                    DNI_list.append( 0 )
                else:
                    DNI_list.append( max( [ GHI_list[i] - DHI_list[i] , 0 ] )/cos( zenith_list_rad[i]) )
                    
            df[ 'DNI' ] = DNI_list
            
        else:
            
            raise Exception("MeteoProfile._complete_irradiance_data: Unable to complete missing irradiance columns.")
        
        return df
    
    @staticmethod
    def _import_custom_file(
            
            tmy_file_path: str | Path,
            latitude: Optional[ float ] = None,
            longitude: Optional[ float ] = None,
            *,
            ghi_col_name: Optional[ str ] = None,
            dni_col_name: Optional[ str ] = None,
            dhi_col_name: Optional[ str ] = None,
            Tamb_col_name: Optional[ str ] = None,
            sep: Optional[ str ] = None,
            skiprows: Optional[ int ] = None,
            
            ):
        
        try:
            
            df = pd.read_csv( 
                
                tmy_file_path,
                sep = sep,
                skiprows = skiprows
                
                )
            
            columns = df.columns.tolist()
            
            columns_to_rename = {}
            columns_to_keep = []
            
            if Tamb_col_name is not None:
                columns_to_rename[ Tamb_col_name ] = 'Tamb'
            elif not 'Tamb' in columns:
                raise FileFormatError("MeteoProfile._import_custom_file: Ambient temperature column must be present in the csv file. If the name of the column is not 'Tamb', it must be provided through the argument 'Tamb_col_name'.")
            columns_to_keep.append( 'Tamb' )
            
            irradiance_custom_names = [ ghi_col_name, dni_col_name, dhi_col_name ]
            irradiance_standard_names = [ 'GHI', 'DNI', 'DHI' ]
            
            for i in range( 3 ):
                if irradiance_custom_names[ i ] is not None:
                    columns_to_rename[ irradiance_custom_names[ i ] ] = irradiance_standard_names[ i ]
                    columns_to_keep.append( irradiance_standard_names[ i ] )
                elif irradiance_standard_names[ i ] in columns:
                    columns_to_keep.append( irradiance_standard_names[ i ] )
                    
            if len( columns_to_keep ) < 3:
                raise FileFormatError("MeteoProfile._import_custom_file: At least two of three irradiance components must be present in the csv file (GHI, DNI, DHI). If the name of the data columns in file are not as mentioned, they must be provided through the arguments 'ghi_col_name','dni_col_name','dhi_col_name'.")
            
            df = df.rename( columns = columns_to_rename )
            df = df.filter( columns_to_keep )
        
        except:
            raise FileFormatError("MeteoProfile._import_custom_file: File could not be imported.")
        
        return df
    
    def _import_meteo_data( self ):
        
        latitude = self.get_attribute( "latitude" )
        longitude = self.get_attribute( "longitude" )
        
        api_key = self.get_attribute( "api_key" )
        
        tmy_file_path = self.get_attribute( "tmy_file_path" )
        ghi_col_name = self.get_attribute( "ghi_col_name" )
        dni_col_name = self.get_attribute( "dni_col_name" )
        dhi_col_name = self.get_attribute( "dhi_col_name" )
        Tamb_col_name = self.get_attribute( "Tamb_col_name" )
        irradiance_units = self.get_attribute( "irradiance_units" )
        temp_units = self.get_attribute( "temp_units" )
        sep = self.get_attribute( "sep" )
        skiprows = self.get_attribute( "skiprows" )
        
        if tmy_file_path is None:
            
            if latitude is None or longitude is None:
                raise ValueError("MeteoProfile.import_meteo_data: latitude and longitude must be provided if no data file is provided.")
            
            try:
                self._df_tmy, self._elevation = MeteoProfile.download_TMY(latitude, longitude, api_key)
            except OutOfChileError:
                raise ValueError("MeteoProfile.import_meteo_data: The location provided is not within the Chilean territory. A meteorological data file must be provided.")
            self._tmy_utc_offset = -4
            
            self._df_tmy = self._df_tmy.filter( [ 'GHI', 'DNI', 'DHI', 'Tamb' ] )
            
        else:
            
            file_format = MeteoProfile._get_file_format( tmy_file_path )
                    
            if file_format in [ "Solar_Explorer", "SAM" ]:
                
                if file_format == "Solar_Explorer":
                    self._latitude, self._longitude, self._elevation, self._tmy_utc_offset, self._df_tmy = MeteoProfile.import_solar_explorer_file( tmy_file_path )
                    
                elif file_format == "SAM":
                    self._latitude, self._longitude, self._elevation, self._tmy_utc_offset, self._df_tmy = MeteoProfile.import_SAM_file( tmy_file_path )
                    
            else:
                
                assert file_format is None
                
                if latitude is None or longitude is None:
                    raise ValueError("MeteoProfile.import_meteo_data: Custom-format data file detected. Latitude and longitude must be provided along with custom-format data files.")
                
                utc_offset = self.get_attribute( "tmy_utc_offset" )
                
                if utc_offset is None:
                    utc_offset = self.get_utc_offset(latitude = latitude, longitude = longitude)
                    self._tmy_utc_offset = utc_offset
                    warnings.warn(f"MeteoProfile: UTC offset of the data was not provided. The value {utc_offset} was inferred from the location. This can be a cause for errors. It is recommended to specify this parameter through the argument 'tmy_utc_offset'.")
                
                self._df_tmy = self._import_custom_file(
                    
                    tmy_file_path,
                    latitude,
                    longitude,
                    ghi_col_name = ghi_col_name,
                    dni_col_name = dni_col_name,
                    dhi_col_name = dhi_col_name,
                    Tamb_col_name = Tamb_col_name,
                    sep = sep,
                    skiprows = skiprows )
                
                self._df_tmy = self.to_minutal( self._df_tmy )
                
                self._df_tmy = self._complete_irradiance_data()
                
                if irradiance_units is not None:
                    self._df_tmy[ 'GHI' ] = convert_units( self._df_tmy[ 'GHI' ].values.astype(float).tolist(), self.get_attribute( "irradiance_units" ), "W/m2" )
                    self._df_tmy[ 'DNI' ] = convert_units( self._df_tmy[ 'DNI' ].values.astype(float).tolist(), self.get_attribute( "irradiance_units" ), "W/m2" )
                    self._df_tmy[ 'DHI' ] = convert_units( self._df_tmy[ 'DHI' ].values.astype(float).tolist(), self.get_attribute( "irradiance_units" ), "W/m2" )
                    
                if temp_units is not None:
                    self._df_tmy[ 'Tamb' ] = convert_units( self._df_tmy[ 'Tamb' ].values.astype(float).tolist(), self.get_attribute( "temp_units" ), "°C" )
        
        self._atmospheric_pressure = self.altitude_to_pressure( self._elevation )
        
        for column in self._df_tmy.columns.tolist():
            self._df_tmy[ column ] = pd.to_numeric( self._df_tmy[ column ] )
                
        self._df_tmy = self.to_minutal( self._df_tmy )
        
        self._df_tmy = self._match_january_first()
        
        assert len( self._df_tmy ) == 8760*60
        
        date_times = pd.date_range(
            
            datetime( year = 2025, month = 1, day = 1, hour = 0, minute = 0, second = 0 ),
            datetime( year = 2025, month = 12, day = 31, hour = 23, minute = 59, second = 0 ),
            freq = 'min', inclusive = 'both', tz = self._tz )
        
        self._df_tmy[ 'timestamp' ] = date_times
        
        solar_position = get_solarposition(date_times, self._latitude, self._longitude)
        
        self._df_tmy[ 'azimuth' ] = solar_position[ 'azimuth' ].values
        self._df_tmy[ 'apparent_zenith' ] = solar_position[ 'apparent_zenith' ].values
        self._df_tmy[ 'zenith' ] = solar_position[ 'zenith' ].values
        
        self._df_tmy = self._df_tmy[ [ 'timestamp', 'GHI', 'DNI', 'DHI', 'Tamb', 'azimuth', 'zenith', 'apparent_zenith' ] ]
        
    def _match_january_first( self ):
        
        df_tmy = self.get_attribute( "df_tmy" )
        latitude = self.get_attribute( "latitude" )
        longitude = self.get_attribute( "longitude" )
        tz = self.get_attribute("tz")
        utc_offset = self.get_attribute( "tmy_utc_offset" )
        
        if tz == "auto":
            self._tz = self.get_timezone(latitude, longitude)
        elif tz is None:
            raise ValueError("MeteoProfile: Time zone cannot be None.")
            
        utc_offset_1st_January = self.get_utc_offset( timezone = self._tz , month = 1 ) #-3
            
        assert len( df_tmy ) == 8760*60
        
        mismatch_minutes = int( np.round( (utc_offset_1st_January - utc_offset)*60 ) ) # In Chile: -3 - (-4) = 1 -> *60 = 60
        
        if mismatch_minutes == 0:
            return df_tmy.copy()
        
        columns = df_tmy.columns.tolist()
        new_df = pd.DataFrame()
        
        if mismatch_minutes > 0:
            for column in columns:
                values_list = df_tmy[ column ].values.astype( float ).tolist()
                last_section = values_list[ -mismatch_minutes: ]
                values_list = last_section + values_list
                values_list = values_list[ : 8760*60 ]
                new_df[ column ] = values_list
        
        else:
            for column in columns:
                values_list = df_tmy[ column ].values.astype( float ).tolist()
                first_section = values_list[ : mismatch_minutes ]
                values_list = values_list + first_section
                values_list = values_list[ - 8760*60: ]
                new_df[ column ] = values_list
                
        return new_df
    
    @staticmethod
    def to_minutal( data ):
        
        if type( data ) is not pd.DataFrame:
            
            try:
                data = [ float( value ) for value in data ]
            except TypeError:
                raise TypeError("MeteoProfile.to_minutal: data must be either pd.DataFrame or list of float.")
            
        if len( data ) == 8760*60:
            return data.copy()
            
        minutes_per_sample = 8760*60/len( data )
        first_sample_time = minutes_per_sample/2
        
        original_time_axis = [ first_sample_time + minutes_per_sample*i for i in range( len( data ) ) ]
        
        goal_time_axis = list( range( 8760*60 ) )
        
        if type( data ) is list:
            return ( np.interp( goal_time_axis, original_time_axis, data ) ).astype( float ).tolist()
        
        else:
            assert type( data ) is pd.DataFrame
            new_df = pd.DataFrame()
            columns = data.columns.tolist()
            for column in columns:
                try:
                    new_df[ column ] = np.interp( goal_time_axis, original_time_axis, data[ column ].values )
                except:
                    raise Exception(f"MeteoProfile.to_minutal: column '{column}' could not be interpolated.")
            return new_df
    
    @staticmethod
    def _get_file_format( file_path ):
        
        with open( file_path ) as file:
            first_line = file.readline().rstrip("\n")
            if first_line == "DATOS HORARIOS GENERADOS CON EL EXPLORADOR DE ENERGIA SOLAR PARA UN ANIO METEOROLOGICO TIPICO":
                return "Solar_Explorer"
            if first_line == "Source,Location ID,City,State,Country,Latitude,Longitude,Time Zone,Elevation":
                return "SAM"
            return None
        
    def get_attribute( self, attribute_name ):
        
        if type( attribute_name ) is not str:
            raise ValueError( "MeteoProfile.get_attribute: attribute_name must be a string." )
        
        return getattr(self, '_' + attribute_name, None)
        
    @staticmethod
    def validate_argument( argument_name, value ):
        
        if not argument_name in MeteoProfile_valid_args:
            raise ValueError( f"Class MeteoProfile: '{argument_name}' is not a valid argument." )
            
        if value is None:
            return value
        
        if argument_name == "location":
            try:
                value = tuple( value )
                assert len( value ) == 2
                value = ( float( value[0] ), float( value[1] ) )
            except:
                raise ValueError( "Class MeteoProfile: Argument 'location' must be convertible to a tuple with length 2." )
                
        if argument_name in [ "latitude", "longitude" ]:
            try:
                value = float( value )
            except:
                raise ValueError( f"Class MeteoProfile: Argument '{argument_name}' must be convertible to type float." )
                
        if argument_name == "ground_albedo":
            try:
                value = float( value )
            except:
                raise ValueError( f"Class MeteoProfile: Argument '{argument_name}' must be convertible to type float." )
                
            if not value >= 0 and value < 1:
                raise ValueError( "Class MeteoProfile: Argument 'ground_albedo' must be >= 0 and < 1." )
            
                
        if argument_name == "api_key":
            try:
                value = str( value )
            except: 
                ValueError( "Class MeteoProfile: Argument 'api_key' must be convertible type 'str'." )
                
        if argument_name == "tmy_file_path":
            try:
                value = Path( value )
            except:
                raise ValueError( "Class MeteoProfile: Argument 'tmy_file_path' must be convertible to type pathlib.Path." )
                
        if argument_name in [
                
                "ghi_col_name",
                "dni_col_name",
                "dhi_col_name",
                "Tamb_col_name",
                
                ]:
            
            try:
                value = str( value )
            except: 
                raise ValueError( f"Class MeteoProfile: Argument '{argument_name}' must be convertible type 'str'." )
                
        if argument_name == "tmy_utc_offset":
            
            try:
                value = float( value )
            except:
                raise ValueError( "Class MeteoProfile: Argument 'tmy_utc_offset' must be convertible type 'float'." )
                
        if argument_name in [
                
                "sep",
                "delimiter",
                
                ]:
            
            try:
                value = str( value )
            except: 
                raise ValueError( f"Class MeteoProfile: Argument '{argument_name}' must be convertible type 'str'." )
                
        if argument_name in [
                
                "irradiance_units",
                "temp_units",
                "T_units",
                "elevation_units",
                
                ]:
            
            try:
                value = str( value )
            except: 
                raise ValueError( f"Class MeteoProfile: Argument '{argument_name}' must be convertible type 'str'." )
                
        if argument_name == "elevation":
            
            try:
                value = float( value )
            except:
                raise ValueError( "Class MeteoProfile: Argument 'elevation' must be convertible type 'float'." )
                
        if argument_name == "solar_field":
            
            if not isinstance( value, SolarField ):
                raise ValueError( "Class MeteoProfile: Argument 'solar_field' must be a SolarField instance." )
                
        if argument_name in [
                
                "tz",
                "time_zone",
                
                ]:
            
            try:
                value_2 = float( value )
                value_2 = MeteoProfile.utc_offset_num_to_str( value_2 )
                value = value_2
            except:
                try:
                    value = str( value )
                except:
                    raise ValueError( f"Class MeteoProfile: Argument '{argument_name}' must be either str (time zone name) or int/float (utc offset)." )
        
        return value
    
    @staticmethod
    def is_Chile( latitude = None, longitude = None, timezone = None ):
        
        if latitude is None and longitude is None:
            try:
                timezone = str( timezone )
            except:
                raise ValueError( "MeteoProfile.is_Chile: Either latitude and longitude must be provided, or timezone must be a string." )
        else:
            if latitude is None or longitude is None:
                raise ValueError( "MeteoProfile.is_Chile: Either both latitude and longitude must be provided, or none of them." )
            try:
                latitude = float( latitude )
                longitude = float( longitude )
            except:
                raise ValueError( "MeteoProfile.is_Chile: latitude and longitude must be convertible to float." )
            
            try:
                timezone = timezone_at(lng = longitude, lat = latitude)
            except:
                raise TimeZoneError( "MeteoProfile.is_Chile: Time zone could not be provided." )
        
        return timezone in [ "America/Santiago", "Pacific/Easter", "America/Coyhaique", "America/Punta_Arenas" ]
    
    @staticmethod
    def get_timezone( latitude, longitude ):
        
        try:
            latitude = float( latitude )
            longitude = float( longitude )
        except:
            raise ValueError( "MeteoProfile.get_timezone: latitude and longitude must be convertible to float." )
            
        try:
            timezone = timezone_at(lng = longitude, lat = latitude)
        except:
            raise TimeZoneError( "MeteoProfile.get_timezone: Time zone could not be provided." )
        
        return timezone
    
    @staticmethod
    def download_TMY(latitude, longitude, api_key = None):
        """
        Function to contact 'API Energias Renovables' (url: https://api.minenergia.cl/) from the Ministry of Energy of Chile.
        
        It downloads a TMY (typical meteorological year) data file produced by that site and generates a pandas.DataFrame object with the the components: GHI, DNI, DHI, and ambient temperature.
        
        The location provided must be within the Chilean territory.
        
        Parameters
        ----------
        latitude : float
            Latitude of the location (degree).
        longitude : float
            Longitude of the location (degree).
        api_key : str, optional
            API key for the 'API Energias Renovables' website. If no value is provided to this function, it is expected that this key was previously saved by the user with the function 'config.set_api_key'.
    
        Raises
        ------
        TMY_Error
        
            - Errors such as connection error, timeout error, incorrect API key, etc. Also raised when the latitude or longitude provided cannot be interpreted as floating point values.
            
            - If the site 'API Energias Renovables' is not able to produce the data requested because the location provided is out of the allowed range.
    
        Returns
        -------
        df : pandas.DataFrame
            DataFrame containing the the data of a typical meteorological year (TMY) with the components: GHI, DNI, DHI, and ambient temperature. It has 8760 rows, one for each hour of a year. Irradiances are expressed in W/m2. Temperature is expressed in °C.
        elevation : float
            Elevation of the specified location (in meters).
    
        """
        
        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except:
            raise TMY_Error("Function download_TMY: Parameters 'latitude' and 'longitude' must be convertible to type 'float'.")
        
        if api_key is None:
            api_key = get_api_key()
            if api_key is None:
                raise TMY_Error("MeteoProfile.download_TMY: No API key available. This key must either be provided as a parameter to the function (argument 'api_key') or be saved with the function config.set_api_key.")
            
        if type( api_key ) is not str:
            raise TMY_Error( "MeteoProfile.download_TMY: api_key must be a string." )
            
        if api_key == "":
            raise TMY_Error("MeteoProfile.download_TMY: Empty API key.")
            
        if not MeteoProfile.is_Chile( latitude, longitude ):
            raise OutOfChileError("MeteoProfile.download_TMY: Location provided is not located within the Chilean territory.")
        
        # API's url
        url = "https://api.exploradorenergia.cl/api/proxy"
        
        # Request header
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Token {api_key}"
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
                        "label": "Tamb",
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
                    raise TMY_Error("Function download_TMY: No url was received from 'API Energias Renovables' (url: https://api.minenergia.cl/). Probably, the location provided is outside the accepted range.")
                    
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
                    raise TMY_Error("Function download_TMY: The data could not be downloaded from the url provided by 'API Energias Renovables' (url: https://api.minenergia.cl/). Check your internet connection and try again later.")
                    
            else:
                if response.status_code == 403:
                    raise TMY_Error("Function download_TMY: The data could not be downloaded from 'API Energias Renovables' (url: https://api.minenergia.cl/). Response status code: 403 (non-valid API Key)")
                else:
                    raise TMY_Error(f"Function download_TMY: The data could not be downloaded from 'API Energias Renovables' (url: https://api.minenergia.cl/). Response status code: {response.status_code}")
            
        except requests.exceptions.ConnectionError:
            raise TMY_Error("Function download_TMY: Could not connect to the server. Check your internet connection and try again later.")
            
        except requests.exceptions.Timeout:
            raise TMY_Error("Function download_TMY: The server took too long to respond.")
            
        except requests.exceptions.RequestException as e:
            raise TMY_Error("Function download_TMY: A requests/network error occurred:", e)
    
    @staticmethod
    def altitude_to_pressure(
            
            altitude: float,
            altitude_units: Optional[ str ] = None,
            pressure_units: Optional[ str ] = None ):
        """
        Static method to compute the atmospheric pressure at a certain altitude.

        Parameters
        ----------
        altitude : float
            Altitude where the pressure needs to be computed. Available range in meters: -500 to 10,000.
        altitude_units : str, optional
            Units with which the altitude is being provided. If not provided, it defaults to 'm'.
        pressure_units : str, optional
            Units with which the pressure is meant to be returned. If not provided, it defaults to 'Pa'.

        Returns
        -------
        pressure : float
            Pressure computed at the altitude introduced.

        """
        
        try:
            altitude = float( altitude )
        except:
            raise ValueError( "MeteoProfile.altitude_to_pressure: altitude must be convertible to type 'float'." )
        
        if altitude_units is not None:
            altitude = convert_units(altitude, altitude_units, 'm')
            
        if not altitude >= -500 and altitude <= 10000:
            raise ValueError( f"MeteoProfile.altitude_to_pressure: altitude must lie within the range: -500 m <= altitude <= 10,000 m. Altitude introduced: {altitude} m." )
        
        Pb = 101325 # Reference pressure, Pa
        Tref = 273.15 + 15 # Reference temperature, K
        R = 8.31432 # Gas constant, J/(mol·K)
        M = 0.0289644 # Air molar mas, kg/mol
        g = 9.80665 # Gravity acceleration, m/s2
        temp_gradient = -6.5e-3 # Temperature gradient, K/m
        
        base = Tref/( Tref + temp_gradient*altitude )
        exponent = g*M/( R * temp_gradient )
        
        pressure = Pb*base**exponent
        
        if pressure_units is not None:
            pressure = convert_units( pressure, 'Pa', pressure_units )
        
        return pressure
    
    def compute_poa_irradiance( self, solar_field ):
        
        coll_tilt_deg = solar_field.get_attribute( "coll_tilt" )
        coll_azimuth_deg = solar_field.get_attribute( "coll_azimuth" )
        coll_IAM = solar_field.get_attribute( "coll_IAM" )
        ground_fraction_covered = solar_field.get_attribute( "ground_fraction_covered" )
        row_width_to_coll_length_ratio = solar_field.get_attribute( "row_width_to_coll_length_ratio" )
        
        coll_tilt_rad = coll_tilt_deg*pi/180
        coll_azimuth_rad = coll_azimuth_deg*pi/180
        
        ground_albedo = self.get_attribute( "ground_albedo" )
        
        
        # assert coll_tilt_deg >= 0 and coll_tilt_deg <= 90
        # assert coll_azimuth_deg >= 0 and coll_azimuth_deg < 360
        
        # assert ground_fraction_covered > 0
        # assert ground_fraction_covered*cos( coll_tilt_rad ) < 1
            
            
            
        
        def dblquad(func, a, b, gfun, hfun, args=()):
            def temp_ranges(*args):
                return [gfun(args[0]) if callable(gfun) else gfun,
                        hfun(args[0]) if callable(hfun) else hfun]
            return nquad(func, [temp_ranges, [a, b]], args=args,
                          opts={"epsabs": 1e-3, "limit": 200, "epsrel": 1e-3})[0]
        
        def diffuse_iam(IAM, coll_tilt, ground_fraction_covered):
            assert type(IAM) in [ dict, int, float ]
            if type(IAM) == dict:
                if 'b0' in IAM:
                    IAM_dict = IAM
                    def IAM_func(theta, phi):
                        aoi = theta
                        if aoi <= 85*pi/180:
                            result = 1 - sum([ IAM_dict['b' + str(i)]*(1/cos(aoi) - 1)**(i + 1) for i in range(len(IAM_dict)) ])
                            return  max([result, 0]) 
                        else:
                            return 0
                elif 'Kl' in IAM:
                    IAM['Kt'][0] = 1
                    IAM['Kt'][90] = 0
                    IAM['Kl'][0] = 1
                    IAM['Kl'][90] = 0
                    angles_Kt = sorted([ angle for angle in IAM['Kt'] ])
                    IAMs_Kt = [ IAM['Kt'][angle] for angle in angles_Kt ]
                    angles_Kl = sorted([ angle for angle in IAM['Kl']  ])
                    IAMs_Kl = [ IAM['Kl'][angle] for angle in angles_Kl ]
                    angles_Kt = [ angle*pi/180 for angle in angles_Kt ]
                    angles_Kl = [ angle*pi/180 for angle in angles_Kl ]
                    Kt_interp = interp1d(angles_Kt, IAMs_Kt)
                    Kl_interp = interp1d(angles_Kl, IAMs_Kl)
                    def IAM_func(theta, phi):
                        transverse_angle = arctan(tan(theta)*sin(phi))
                        longitudinal_angle = arctan(tan(theta)*cos(phi))
                        return Kt_interp(transverse_angle)*Kl_interp(longitudinal_angle)
                else:
                    IAM[0] = 1
                    IAM[90] = 0
                    angles = sorted([ angle for angle in IAM ])
                    IAMs = [ IAM[angle] for angle in angles ]
                    angles = [ angle*pi/180 for angle in angles ]
                    IAM_interp = interp1d(angles, IAMs)
                    def IAM_func(theta, phi):
                        return IAM_interp(theta)
            if type(IAM) == float or type(IAM) == int:
                b0 = IAM
                def IAM_func(theta, phi):
                    if theta <= 85*pi/180:
                        result = 1 - b0*(1/cos(theta) - 1)
                        return max([result, 0])
                    else:
                        return 0
            def function_to_integrate(theta, phi, mode):
                if mode == 'numerator':
                    return IAM_func(theta, phi)*cos(theta)*sin(theta)
                if mode == 'denominator':
                    return cos(theta)*sin(theta)
            assert coll_tilt >= 0 and coll_tilt <= 90
            coll_tilt_rad = coll_tilt*pi/180
            def integration_limit_first_row( phi ):
                return arctan( tan( pi/2 - coll_tilt_rad )/cos( phi ) )
            Results_Dict = {}
            if coll_tilt == 0 or coll_tilt == 90:
                numerator = dblquad( function_to_integrate, 0, pi/2, 0, pi/2, args = ('numerator',) )
                denominator = dblquad( function_to_integrate, 0, pi/2, 0, pi/2, args = ('denominator',) )
                Results_Dict[ 'isotropic_first_row' ] = numerator/denominator
                Results_Dict[ 'ground' ] = (coll_tilt == 90)*numerator/denominator
            else:
                numerator_sky_1 = dblquad( function_to_integrate, 0, pi/2, 0, pi/2, args = ('numerator',) )
                denominator_sky_1 = dblquad( function_to_integrate, 0, pi/2, 0, pi/2, args = ('denominator',) )
                numerator_sky_2 = dblquad( function_to_integrate, 0, pi/2, 0, integration_limit_first_row, args = ('numerator',) )
                denominator_sky_2 = dblquad( function_to_integrate, 0, pi/2, 0, integration_limit_first_row, args = ('denominator',) )
                numerator_ground = dblquad( function_to_integrate, 0, pi/2, integration_limit_first_row, pi/2, args = ('numerator',) )
                denominator_ground = dblquad( function_to_integrate, 0, pi/2, integration_limit_first_row, pi/2, args = ('denominator',) )
                Results_Dict[ 'isotropic_first_row' ] = (numerator_sky_1 + numerator_sky_2)/(denominator_sky_1 + denominator_sky_2)
                Results_Dict[ 'ground' ] = numerator_ground/denominator_ground
            delta_rad = arctan( ground_fraction_covered*sin( coll_tilt_rad )/( 2 - ground_fraction_covered*cos( coll_tilt_rad ) ) )
            if coll_tilt_rad + delta_rad >= pi/2:
                def integration_limit_shadeable_rows( phi ):
                    return arctan( tan( coll_tilt_rad + delta_rad - pi/2 )/cos( phi ) )
                numerator_sky = dblquad( function_to_integrate, 0, pi/2, integration_limit_shadeable_rows, pi/2, args = ('numerator',) )
                denominator_sky = dblquad( function_to_integrate, 0, pi/2, integration_limit_shadeable_rows, pi/2, args = ('denominator',) )
                Results_Dict[ 'isotropic_shadeable_rows' ] = numerator_sky/denominator_sky
            else:
                def integration_limit_shadeable_rows( phi ):
                    return arctan( tan( pi/2 - coll_tilt_rad - delta_rad )/cos( phi ) )
                numerator_sky_1 = dblquad( function_to_integrate, 0, pi/2, 0, pi/2, args = ('numerator',) )
                denominator_sky_1 = dblquad( function_to_integrate, 0, pi/2, 0, pi/2, args = ('denominator',) )
                numerator_sky_2 = dblquad( function_to_integrate, 0, pi/2, 0, integration_limit_shadeable_rows, args = ('numerator',) )
                denominator_sky_2 = dblquad( function_to_integrate, 0, pi/2, 0, integration_limit_shadeable_rows, args = ('denominator',) )
                Results_Dict[ 'isotropic_shadeable_rows' ] = (numerator_sky_1 + numerator_sky_2)/(denominator_sky_1 + denominator_sky_2)
            if coll_tilt == 90:
                def function_to_integrate(theta, mode):
                    phi = pi/2
                    if mode == 'numerator':
                        return IAM_func(theta, phi)*cos(theta)*sin(theta)
                    if mode == 'denominator':
                        return cos(theta)*sin(theta)
                numerator = quad( function_to_integrate, 0, pi/2, args = ('numerator',) )[0]
                denominator = quad( function_to_integrate, 0, pi/2, args = ('denominator',) )[0]
                Results_Dict[ 'horizon' ] = numerator/denominator
            elif coll_tilt == 0:
                Results_Dict[ 'horizon' ] = 0
            else:
                def function_to_integrate(phi, mode):
                    theta = arctan( tan( pi/2 - coll_tilt_rad )/cos( phi ) )
                    if mode == 'numerator':
                        return IAM_func(theta, phi)*cos(theta)*sin(theta)
                    if mode == 'denominator':
                        return cos(theta)*sin(theta)
                numerator = quad( function_to_integrate, 0, pi/2, args = ('numerator',) )[0]
                denominator = quad( function_to_integrate, 0, pi/2, args = ('denominator',) )[0]
                Results_Dict[ 'horizon' ] = numerator/denominator
            return Results_Dict
        
        rotation_matrix = np.linalg.inv(np.array([[  cos( coll_azimuth_rad )*cos( coll_tilt_rad ), -sin( coll_azimuth_rad ), cos( coll_azimuth_rad )*sin( coll_tilt_rad ) ],
                                                  [  sin( coll_azimuth_rad )*cos( coll_tilt_rad ),  cos( coll_azimuth_rad ), sin( coll_azimuth_rad )*sin( coll_tilt_rad ) ],
                                                  [ -sin( coll_tilt_rad ),                          0,                       cos( coll_tilt_rad )         ] ] ) )
        
        def incidence_angles(solar_zenith, solar_azimuth):
            solar_N = cos(solar_azimuth*pi/180)*sin(solar_zenith*pi/180)
            solar_E = sin(solar_azimuth*pi/180)*sin(solar_zenith*pi/180)
            solar_Z = cos(solar_zenith*pi/180)
            coll_coordinates = np.dot(rotation_matrix, np.array([[solar_N],
                                                                 [solar_E],
                                                                 [solar_Z]]))
            coll_N = coll_coordinates[0][0]
            coll_E = coll_coordinates[1][0]
            coll_Z = coll_coordinates[2][0]
            if coll_Z <= 0:
                return None, None, None
            trans = arctan(abs(coll_E)/coll_Z)
            longi = arctan(abs(coll_N)/coll_Z)
            tg2_aoi = (tan(trans))**2 + (tan(longi))**2
            aoi = arctan(tg2_aoi**(1/2))
            if longi > pi/2 - coll_tilt_rad and coll_N > 0:
                longi = pi/2 - coll_tilt_rad
                tg2_aoi = (tan(trans))**2 + (tan(longi))**2
                aoi = arctan(tg2_aoi**(1/2))
            if coll_N > 0:
                longi = -longi
            return float(aoi), float(longi), float(trans)
        
        def incidence_angles_series(solar_zenith_series, solar_azimuth_series):
            
            solar_N = cos( (pi/180)*solar_azimuth_series )*sin( (pi/180)*solar_zenith_series )
            
            solar_E = sin( (pi/180)*solar_azimuth_series )*sin( (pi/180)*solar_zenith_series )
            
            solar_Z = cos( (pi/180)*solar_zenith_series )
            
            vectors = np.stack([solar_N, solar_E, solar_Z], axis = 1)[:, :, np.newaxis]
            
            coll_coordinates = np.matmul(rotation_matrix, vectors)
            
            aoi_array = []
            longi_array = []
            trans_array = []
            
            for vector in coll_coordinates:
                coll_N = vector[0][0]
                coll_E = vector[1][0]
                coll_Z = vector[2][0]
                if coll_Z <= 0:
                    aoi_array.append( np.nan )
                    longi_array.append( np.nan )
                    trans_array.append( np.nan )
                    continue
                trans = arctan(abs(coll_E)/coll_Z)
                longi = arctan(abs(coll_N)/coll_Z)
                tg2_aoi = (tan(trans))**2 + (tan(longi))**2
                aoi = arctan(tg2_aoi**(1/2))
                if longi > pi/2 - coll_tilt_rad and coll_N > 0:
                    longi = pi/2 - coll_tilt_rad
                    tg2_aoi = (tan(trans))**2 + (tan(longi))**2
                    aoi = arctan(tg2_aoi**(1/2))
                if coll_N > 0:
                    longi = -longi
                aoi_array.append( aoi )
                longi_array.append( longi )
                trans_array.append( trans )
            return np.array( aoi_array ), np.array( longi_array ), np.array( trans_array )
        
        if type(coll_IAM) == dict:
            assert 'b0' in coll_IAM or 'Kl' in coll_IAM or all([ (type(key) == int or type(key) == float) for key in coll_IAM])
            if 'b0' in coll_IAM:
                assert all(['b' + str(i) in coll_IAM for i in range(len(coll_IAM)) ])
                coll_type = 'monoaxial_b'
                IAM_dict = coll_IAM
            elif 'Kl' in coll_IAM:
                assert 'Kt' in coll_IAM and len(coll_IAM) == 2
                coll_type = 'biaxial'
                coll_IAM['Kt'][0] = 1
                coll_IAM['Kt'][90] = 0
                coll_IAM['Kl'][0] = 1
                coll_IAM['Kl'][90] = 0
                angles_Kt = sorted([ angle for angle in coll_IAM['Kt'] ])
                IAMs_Kt = [ coll_IAM['Kt'][angle] for angle in angles_Kt ]
                angles_Kl = sorted([ angle for angle in coll_IAM['Kl']  ])
                IAMs_Kl = [ coll_IAM['Kl'][angle] for angle in angles_Kl ]
                assert all([ angles_Kt[i]>= 0 and angles_Kt[i]<= 90 for i in range(len(angles_Kt)) ])
                assert all([ angles_Kl[i]>= 0 and angles_Kl[i]<= 90 for i in range(len(angles_Kl)) ])
                angles_Kt = [ angle*pi/180 for angle in angles_Kt ]
                angles_Kl = [ angle*pi/180 for angle in angles_Kl ]
                Kt_func = interp1d(angles_Kt, IAMs_Kt)
                Kl_func = interp1d(angles_Kl, IAMs_Kl)
            else:
                assert all( [ key >= 0 and key <= 90 for key in coll_IAM ] )
                coll_type = 'monoaxial_angle_list'
                coll_IAM[0] = 1
                coll_IAM[90] = 0
                angles = sorted([ angle for angle in coll_IAM ])
                IAMs = [ coll_IAM[angle] for angle in angles ]
                angles = [ angle*pi/180 for angle in angles ]
                IAM_func = interp1d(angles, IAMs)
        elif type(coll_IAM) == float or type(coll_IAM) == int:
            coll_type = 'monoaxial_b'
            IAM_dict = {'b0': coll_IAM}
        else:
            assert coll_IAM is None
            coll_type = 'no_IAM'
        if coll_type == 'no_IAM':
            isotropic_iam_first_row = 1
            isotropic_iam_shadeable_rows = 1
            horizon_iam = 1
            ground_iam = 1
        else:
            diff_IAM = diffuse_iam(coll_IAM, coll_tilt_deg, ground_fraction_covered)
            isotropic_iam_first_row = diff_IAM['isotropic_first_row']
            isotropic_iam_shadeable_rows = diff_IAM['isotropic_shadeable_rows']
            horizon_iam = diff_IAM['horizon']
            ground_iam = diff_IAM['ground']
        
        def compute_beam_IAM(aoi, longi, trans):
            if coll_type == 'no_IAM':
                return 1
            if coll_type == 'monoaxial_b':
                if aoi <= 85*pi/180:
                    result = 1 - sum([ IAM_dict['b' + str(i)]*(1/cos(aoi) - 1)**(i + 1) for i in range(len(IAM_dict)) ])
                    return max([result, 0])
                else:
                    return 0
            if coll_type == 'monoaxial_angle_list':
                return IAM_func(aoi)
            if coll_type == 'biaxial':
                return Kt_func(trans)*Kl_func(longi)
            
        def visible_sky_fraction( x ):
            delta = arctan( x*ground_fraction_covered*sin( coll_tilt_rad )/( 1 - x*ground_fraction_covered*cos( coll_tilt_rad ) ) )
            rho = coll_tilt_rad + delta
            if rho >= pi/2:
                return ( 1 - cos( pi - rho ) )/2
            else:
                return ( 1 + cos( rho ) )/2
        
        diffuse_irradiance_fraction_non_shadeable_rows = 0.5*(1 + cos(coll_tilt_rad))
        diffuse_irradiance_fraction_shadeable_rows = quad( visible_sky_fraction, 0, 1 )[0]
        reflected_irradiance_fraction = 0.5*( 1 - cos(coll_tilt_rad) )
        
        First_Row_Irradiance_Profile = []
        Shadeable_Rows_Irradiance_Profile = []
        First_Row_IAM_Profile = []
        Shadeable_Rows_IAM_Profile = []
        
        
        date_times = pd.DatetimeIndex( self._df_tmy[ 'timestamp' ] )
        GHI_array = np.max( [ self._df_tmy[ 'GHI' ].values, [ 0 ]*len( self._df_tmy ) ], axis = 0 )
        DNI_array = np.max( [ self._df_tmy[ 'DNI' ].values, [ 0 ]*len( self._df_tmy ) ], axis = 0 )
        DHI_array = np.max( [ self._df_tmy[ 'DHI' ].values, [ 0 ]*len( self._df_tmy ) ], axis = 0 )
        
        zenith_array = self._df_tmy[ 'apparent_zenith' ].values
        azimuth_array = self._df_tmy[ 'azimuth' ].values
        
        relative_airmass_array = get_relative_airmass( zenith_array  )
        dni_extra_array = get_extra_radiation( date_times )
        
        diff_irradiance = perez( coll_tilt_deg,
                                 coll_azimuth_deg,
                                 DHI_array,
                                 DNI_array,
                                 dni_extra_array,
                                 zenith_array,
                                 azimuth_array,
                                 relative_airmass_array,
                                 return_components = True )
        
        isotropic_irradiance_array = diff_irradiance[ 'isotropic' ].values
        circumsolar_irradiance_array = diff_irradiance['circumsolar'].values
        horizon_irradiance_array = diff_irradiance[ 'horizon' ].values
        
        aoi_array, longi_array, trans_array = incidence_angles_series(zenith_array, azimuth_array)
        
        for time_step in range( len( self._df_tmy ) ):
            
            GHI = GHI_array[time_step]
            DNI = DNI_array[time_step]
            DHI = DHI_array[time_step]
            
            if DHI <= 0 and DNI <= 0:
                
                First_Row_Irradiance_Profile.append( 0 )
                Shadeable_Rows_Irradiance_Profile.append( 0 )
                First_Row_IAM_Profile.append( 0 )
                Shadeable_Rows_IAM_Profile.append( 0 )
                continue
            
            aoi = aoi_array[ time_step ]
            longi = longi_array[ time_step ]
            trans = trans_array[ time_step ]
            
            isotropic_irradiance_first_row = float( isotropic_irradiance_array[ time_step ] )
            isotropic_irradiance_shadeable_rows = isotropic_irradiance_first_row*diffuse_irradiance_fraction_shadeable_rows/diffuse_irradiance_fraction_non_shadeable_rows
            circumsolar_irradiance = float( circumsolar_irradiance_array[ time_step ] )
            horizon_irradiance = float( horizon_irradiance_array[ time_step ] )
            ref_irradiance = reflected_irradiance_fraction*ground_albedo*max([GHI, 0] )
            
            if np.isnan(aoi):
                
                beam_irradiance = 0
                beam_IAM = 0
                shading_factor = 0
                
            else:
                
                beam_irradiance = max( [ DNI*cos(aoi), 0 ] ) + max( [ circumsolar_irradiance, 0 ] )
                beam_IAM = compute_beam_IAM(aoi, abs(longi), trans)
                
                if longi < 0 and abs(longi) >= pi/2 - coll_tilt_rad:
                    shading_factor = 0
                
                elif ( cos( coll_tilt_rad ) + sin( coll_tilt_rad )*tan( longi ) )/ground_fraction_covered >= 1 or sin( coll_tilt_rad )*tan( trans )/( row_width_to_coll_length_ratio*ground_fraction_covered ) >= 1:
                    shading_factor = 1
                    
                else:
                    F1 = ( cos( coll_tilt_rad ) + sin( coll_tilt_rad )*tan( longi ) )/ground_fraction_covered
                    F2 = sin( coll_tilt_rad )*tan( trans )*( 1 - F1 )/( row_width_to_coll_length_ratio*ground_fraction_covered )
                    shading_factor =  F1 + F2
            
            first_row_irradiance = beam_irradiance + isotropic_irradiance_first_row + horizon_irradiance + ref_irradiance
            shadeable_rows_irradiance = shading_factor*beam_irradiance + isotropic_irradiance_shadeable_rows
            
            if first_row_irradiance > 0:
                first_row_IAM = ( beam_irradiance*beam_IAM + isotropic_irradiance_first_row*isotropic_iam_first_row + horizon_irradiance*horizon_iam + ref_irradiance*ground_iam )/first_row_irradiance
            else:
                first_row_IAM = 0
            if shadeable_rows_irradiance > 0:
                shadeable_rows_IAM = ( shading_factor*beam_irradiance*beam_IAM + isotropic_irradiance_shadeable_rows*isotropic_iam_shadeable_rows )/shadeable_rows_irradiance
            else:
                shadeable_rows_IAM = 0
            
            First_Row_Irradiance_Profile.append( first_row_irradiance )
            Shadeable_Rows_Irradiance_Profile.append( shadeable_rows_irradiance )
            First_Row_IAM_Profile.append( first_row_IAM )
            Shadeable_Rows_IAM_Profile.append( shadeable_rows_IAM )
            
        aoi_array = (180/pi)*aoi_array
        longi_array = (180/pi)*longi_array
        trans_array = (180/pi)*trans_array
        
        self._df_tmy[ 'aoi' ] = aoi_array
        self._df_tmy[ 'aoi_l' ] = longi_array
        self._df_tmy[ 'aoi_t' ] = trans_array
        
        self._df_tmy[ 'irradiance_first_row' ] = First_Row_Irradiance_Profile
        self._df_tmy[ 'irradiance_shadeable_rows' ] = Shadeable_Rows_Irradiance_Profile
        self._df_tmy[ 'IAM_first_row' ] = First_Row_IAM_Profile
        self._df_tmy[ 'IAM_shadeable_rows' ] = Shadeable_Rows_IAM_Profile
        
    def instant_to_index( self, month, day, hour, minute ):
        
        if month == 2 and day == 29:
            day = 28
            raise ValueError("Class MeteoProfile.instant_to_index: Data for February 29 was requested. Leap years are not supported.")
            
        if month < 1 or month > 12:
            raise ValueError("Class MeteoProfile.instant_to_index: Month number not valid.")
            
        if day < 1 or day > month_days[ month - 1 ]:
            raise ValueError("Class MeteoProfile.instant_to_index: Day number not valid.")
            
        if hour < 0 or hour > 23:
            raise ValueError("Class MeteoProfile.instant_to_index: Hour number not valid.")
            
        if minute < 0 or minute > 59:
            raise ValueError("Class MeteoProfile.instant_to_index: Minute number not valid.")
        
        mask = (
            
            ( self._df_tmy[ "timestamp" ].dt.month == month ) &
            ( self._df_tmy[ "timestamp" ].dt.day == day     ) &
            ( self._df_tmy[ "timestamp" ].dt.hour == hour   ) &
            ( self._df_tmy[ "timestamp" ].dt.minute == minute )
            
            )
        
        idx = self._df_tmy.index[ mask ].tolist()
        
        return idx
        
    def get_conditions(
            self,
            *args,
            include_right = True,
            month = None,
            day = None,
            hour = None,
            minute = None,
            irradiance_units = None,
            temp_units = None,
            T_units = None,
            angle_units = None ):
        
        """
        
        Get the meteorological conditions.
        
        Parameters
        ----------
        
        include_right : bool, optional
            sdflsdfsdfasdf
            
        returns
        -------
        
        
        
        
        """
        
        if not len( args ) in [ 0, 1, 2 ]:
            raise ValueError("MeteoProfile.get_conditions: Number of positional arguments must be either 0, 1, or 2.")
            
        result = self._df_tmy.copy()
        
        if len( args ) == 2:
            
            try:
                
                dt1 = args[0]
                dt2 = args[1]
                
                
                month_1 = int( dt1.month )
                day_1 = int( dt1.day )
                hour_1 = int( dt1.hour )
                minute_1 = int( dt1.minute )
                
                month_2 = int( dt2.month )
                day_2 = int( dt2.day )
                hour_2 = int( dt2.hour )
                minute_2 = int( dt2.minute )
                
            except:
                
                raise ValueError("MeteoProfile.get_conditions: Both positional arguments must have attributes named 'year', 'month', 'day', 'hour' and 'minute', convertible to type 'int'.")
            
            if month_2 == 1 and day_2 == 1 and hour_2 == 0 and minute_2 == 0 and not include_right:
                month_2 = 12
                day_2 = 31
                hour_2 = 23
                minute_2 = 59
                include_right = True
            
            index_1 = self.instant_to_index( month_1, day_1, hour_1, minute_1 )
            index_2 = self.instant_to_index( month_2, day_2, hour_2, minute_2 )
            
            if len( index_1 ) == 0:
                raise ValueError("MeteoProfile.get_conditions: Initial instant introduced was not found in the yearly DataFrame. This could be due to a transition to daylight saving time.")
            if len( index_2 ) == 0:
                raise ValueError("MeteoProfile.get_conditions: Final instant introduced was not found in the yearly DataFrame. This could be due to a transition to daylight saving time.")
            
            index_1 = index_1[ 0 ]
            index_2 = index_2[ 0 ]
            
            if include_right:
                index_2 = index_2 + 1
            
            if not index_2 > index_1:
                raise ValueError("MeteoProfile.get_conditions: Instants provided as positional arguments are not ordered in time.")
            
            result = result[ index_1 : index_2 ]
        
        elif len( args ) == 1:
            
            try:
                
                dt = args[ 0 ]
                
                month = int( dt.month )
                day = int( dt.day )
                hour = int( dt.hour )
                minute = int( dt.minute )
                
            except:
                
                raise ValueError("MeteoProfile.get_conditions: Positional argument must have attributes named 'month', 'day', 'hour' and 'minute', convertible to type 'int'.")
                
            index = self.instant_to_index( month, day, hour, minute )
            
            if len( index ) == 0:
                raise ValueError("MeteoProfile.get_conditions: Instant introduced was not found in the yearly DataFrame. This could be due to a transition to daylight saving time.")
                
            index = index[0]
            
            result_dict = {}
            
            for column in result.columns.tolist():
                
                if column == "timestamp":
                    continue
                
                result_dict[ column ] = float( result[ column ].values[ index ] )
                
            result = result_dict
            
        else:
            
            try:
                
                if month is not None:
                    month = int( month )
                if day is not None:
                    day = int( day )
                if hour is not None:
                    hour = int( hour )
                if minute is not None:
                    minute = int( minute )
                    
            except:
                raise ValueError("MeteoProfile.get_conditions: Arguments 'month', 'day', 'hour', and 'minute' must be either None or convertible to type 'int'.")
                
            if month is not None:
                
                result = result[ result[ "timestamp" ].dt.month == month ]
                
                if day is not None:
                    
                    result = result[ result[ "timestamp" ].dt.day == day ]
                    
                    if hour is not None:
                        
                        result = result[ result[ "timestamp" ].dt.hour == hour ]
                        
                        if len( result ) > 60:
                            result = result.head( 60 )
                        
                        if minute is not None:
                            result = result[ result[ "timestamp" ].dt.minute == minute ]
                            
                        if len( result ) == 0:
                            raise ValueError("MeteoProfile.get_conditions: Time span introduced was not found in the yearly DataFrame. This could be due to a transition to daylight saving time.")
        
        assert type( result ) in [ dict, pd.DataFrame ]
            
        if type( result ) is pd.DataFrame:
            
            result = result.reset_index( drop = True )
            
            result_columns = result.columns.tolist()
            
            if irradiance_units is not None:
                for column_name in self.irradiance_columns:
                    if column_name in result_columns:
                        result[ column_name ] = convert_units( result[ column_name ].values.tolist(), 'W/m2', irradiance_units )
            
            if temp_units is not None or T_units is not None:
                if temp_units is None and T_units is not None:
                    temp_units = T_units
                for column_name in self.temp_columns:
                    if column_name in result_columns:
                        result[ column_name ] = convert_units( result[ column_name ].values.tolist(), '°C', temp_units )
            
            if angle_units is not None:
                for column_name in self.angle_columns:
                    if column_name in result_columns:
                        result[ column_name ] = convert_units( result[ column_name ].values.tolist(), 'deg', angle_units )
                        
        else:
            
            result_keys = list( result.keys() )
            
            if irradiance_units is not None:
                for column_name in self.irradiance_columns:
                    if column_name in result_keys:
                        result[ column_name ] = convert_units( result[ column_name ], 'W/m2', irradiance_units )
            
            if temp_units is not None or T_units is not None:
                if temp_units is None and T_units is not None:
                    temp_units = T_units
                for column_name in self.temp_columns:
                    if column_name in result_keys:
                        result[ column_name ] = convert_units( result[ column_name ], '°C', temp_units )
            
            if angle_units is not None:
                for column_name in self.angle_columns:
                    if column_name in result_keys:
                        result[ column_name ] = convert_units( result[ column_name ], 'deg', angle_units )
            
        return result
                
    def compute_T_mains_Profile( self ):
        
        month_start_idx_list = [ 0 ]
        for month in range(2, 13):
            month_start_idx = self.instant_to_index( month, 1, 0, 0 )
            if len( month_start_idx ) == 0:
                month_start_idx = self.instant_to_index( month, 1, 1, 0 )
                assert len( month_start_idx ) > 0
            month_start_idx_list.append( month_start_idx[ 0 ] )
        month_start_idx_list.append( len( self._df_tmy ) )
        
        Monthly_Mean_T_amb_List = [  np.mean( self._df_tmy[ "Tamb" ].values[ month_start_idx_list[ month_index ] : month_start_idx_list[ month_index + 1 ] ] )  for month_index in range(12) ]
        
        T_amb_ann =  np.mean( self._df_tmy[ "Tamb" ].values ) 
        delta_T_amb = ( max(Monthly_Mean_T_amb_List) - min(Monthly_Mean_T_amb_List) )/2
        delta_T_offset = 3.3333333
        T_ref = 6.6666667
        K1 = 0.4
        K2 = 0.018
        K3 = 35*pi/180
        K4 = -3.1416e-4
        delta_T_mains = (K1 + K2*(T_amb_ann - T_ref))*delta_T_amb
        phi_lag = K3 + K4*(T_amb_ann - T_ref)
        phi_amb = (104.8 + 180)*pi/180
        T_mains_avg = T_amb_ann + delta_T_offset
        def T_mains_func(t):
            return T_mains_avg + delta_T_mains*sin(2*pi*t/8760 - phi_lag - phi_amb)
        t_list = np.linspace( 0, 8760 - 1/60, 8760*60 )
        
        self._df_tmy[ "Tmains" ] = [ T_mains_func(t)  for t in t_list ]