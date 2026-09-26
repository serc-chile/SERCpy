# -*- coding: utf-8 -*-
"""
Created on Mon Aug 17 22:08:31 2026

@author: Adrian Riebel Brummer
"""

from math import sin, cos, tan, arctan, pi
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
from .config import api_key as _api_key
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
    
    "tmy_file_path",
    "ghi_col_name",
    "dni_col_name",
    "dhi_col_name",
    "Tamb_col_name",
    
    "solar_field",
    
    "tz",
    
    ]
    
class MeteoProfile:
    
    def __init__(
            
            self, 
            *,
            
            location: Optional[ tuple ] = None,
            latitude: Optional[ float ] = None,
            longitude: Optional[ float ] = None,
            
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
            
            solar_field: Optional[ SolarField ] = None,
            
            tz: Optional[ str ] = 'auto',
            
            **kwargs):
        
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
            
        self.import_meteo_data(
            
            self._latitude,
            self._longitude,
            
            api_key,
            
            tmy_file_path,
            ghi_col_name,
            dni_col_name,
            dhi_col_name,
            Tamb_col_name,
            tmy_utc_offset,
            sep,
            delimiter,
            skiprows,
            
            
            )
    
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
                        altitude = float( line_list[1] )
                    except:
                        raise FileFormatError("MeteoProfile.import_solar_explorer_file: altitude could not be read in line 14 of the file.")
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
        
        return latitude, longitude, utc_offset, df
        
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
                    latitude, longitude, utc_offset, altitude = float( line_list[ 5 ] ), float( line_list[ 6 ] ), float( line_list[ 7 ] ), float( line_list[ 8 ] )
                except:
                    raise FileFormatError("MeteoProfile.import_SAM_file: Metadata could not be extracted from file (latitude, longitude, utc_offset, altitude).")
                break
            
        df = pd.read_csv( tmy_file_path, skiprows = 1 )
        
        try:
            df = df.filter( [ 'GHI','DNI','DHI','Tdry' ] )
            df = df.rename( columns = { 'Tdry': 'Tamb', } )
        except:
            raise FileFormatError("MeteoProfile.import_SAM_file: SAM-formatted file could not be processed.")
            
        return latitude, longitude, utc_offset, df
    
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
    def get_utc_offset( latitude, longitude ):
        
        timezone = timezone_at(lng = longitude, lat = latitude)
        
        if latitude >= 0:
            month = 1
        else:
            month = 7
        
        dt = datetime( year = 2025, month = month, day = 1, hour = 0, minute = 0, second = 0, tzinfo = ZoneInfo(timezone) )
        
        offset_hours = int( dt.utcoffset().total_seconds() )/3600
        
        return offset_hours
    
    @staticmethod
    def complete_irradiance_data(
            
            df: pd.DataFrame,
            latitude: Optional[ float ] = None,
            longitude: Optional[ float ] = None,
            *,
            ghi_col_name: Optional[ str ] = None,
            dni_col_name: Optional[ str ] = None,
            dhi_col_name: Optional[ str ] = None,
            utc_offset: Optional[ str ] = None,
            ):
        
        if ghi_col_name is not None:
            df = df.rename( columns = { ghi_col_name: 'GHI' } )
        if dni_col_name is not None:
            df = df.rename( columns = { dni_col_name: 'DNI' } )
        if dhi_col_name is not None:
            df = df.rename( columns = { dhi_col_name: 'DHI' } )
        
        columns = df.columns.tolist()
        
        if 'GHI' in columns and 'DNI' in columns and 'DHI' in columns:
            
            if ghi_col_name is not None:
                df = df.rename( columns = { 'GHI': ghi_col_name } )
            if dni_col_name is not None:
                df = df.rename( columns = { 'DNI': dni_col_name } )
            if dhi_col_name is not None:
                df = df.rename( columns = { 'DHI': dhi_col_name } )
            
            return df
        
        if latitude is None or longitude is None:
            raise LocationNeeded("MeteoProfile.complete_irradiance_data: Latitude and longitude are needed when one of the irradiance columns is missing (GHI, DNI, DHI).")
        
        if not any( [
                
                'GHI' in columns and 'DNI' in columns,
                'DNI' in columns and 'DHI' in columns,
                'GHI' in columns and 'DHI' in columns,
                
                ] ):
            
            raise ValueError("MeteoProfile.complete_irradiance_data: At least two irradiance columns have to be present in the DataFrame from the three: GHI, DNI, DHI.")
        
        if utc_offset is None:
            warnings.warn("MeteoProfile: Missing irradiance column will be calculated without information about the UTC offset of the data. The UTC offset will be inferred from the location introduced. This can lead to large errors if the assumption is incorrect.")
            tz = MeteoProfile.utc_offset_num_to_str( MeteoProfile.get_utc_offset(latitude, longitude) )
        
        else:
            tz = MeteoProfile.utc_offset_num_to_str( utc_offset )
        
        date_times = MeteoProfile.data_length_to_datetimes( len( df ), tz = tz )
        
        zenith_list = get_solarposition(date_times, latitude, longitude)[ 'apparent_zenith' ].astype(float).tolist()
        
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
                    DHI_list.append( max( [ GHI_list[i] - DNI_list[i]*cos( zenith_list[i] ) , 0 ] ) )
                    
            df[ 'DHI' ] = DHI_list
            
        elif 'DNI' in columns and 'DHI' in columns:
            DNI_list = df[ 'DNI' ].values.astype(float).tolist()
            DHI_list = df[ 'DHI' ].values.astype(float).tolist()
            GHI_list = []
            
            for i in range( len( DNI_list ) ):
                if zenith_list[i] > 90:
                    GHI_list.append( DHI_list[i] )
                else:
                    GHI_list.append( DNI_list[i]*cos( zenith_list[i] ) + DHI_list[i] )
                    
            df[ 'GHI' ] = GHI_list
                    
        elif 'GHI' in columns and 'DHI' in columns:
            GHI_list = df[ 'GHI' ].values.astype(float).tolist()
            DHI_list = df[ 'DHI' ].values.astype(float).tolist()
            DNI_list = []
            
            for i in range( len( GHI_list ) ):
                if zenith_list[i] > 85:
                    DNI_list.append( 0 )
                else:
                    DNI_list.append( max( [ GHI_list[i] - DHI_list[i] , 0 ] )/cos( zenith_list[i] ) )
                    
            df[ 'DNI' ] = DNI_list
            
        else:
            
            raise Exception("MeteoProfile.complete_irradiance_data: Unknown error.")
            
        if ghi_col_name is not None:
            df = df.rename( columns = { 'GHI': ghi_col_name } )
        if dni_col_name is not None:
            df = df.rename( columns = { 'DNI': dni_col_name } )
        if dhi_col_name is not None:
            df = df.rename( columns = { 'DHI': dhi_col_name } )
        
        return df
    
    @staticmethod
    def import_custom_file(
            
            tmy_file_path: str | Path,
            latitude: Optional[ float ] = None,
            longitude: Optional[ float ] = None,
            *,
            ghi_col_name: Optional[ str ] = None,
            dni_col_name: Optional[ str ] = None,
            dhi_col_name: Optional[ str ] = None,
            Tamb_col_name: str,
            utc_offset: Optional[ float ] = None,
            sep: Optional[ str ] = None,
            delimiter: Optional[ str ] = None,
            skiprows: Optional[ int ] = None,
            
            ):
        
        if sep is None and delimiter is not None:
            sep = delimiter
        
        try:
            
            df = pd.read_csv( 
                
                tmy_file_path,
                sep = sep,
                skiprows = skiprows
                
                )
            columns_to_rename = { Tamb_col_name: 'Tamb' }
            columns_to_keep = 'Tamb'
            if ghi_col_name is not None:
                columns_to_rename[ ghi_col_name ] = 'GHI'
                columns_to_keep.append( 'GHI' )
            if dni_col_name is not None:
                columns_to_rename[ dni_col_name ] = 'DNI'
                columns_to_keep.append( 'DNI' )
            if dhi_col_name is not None:
                columns_to_rename[ dhi_col_name ] = 'DHI'
                columns_to_keep.append( 'DHI' )
            
            df = df.rename( columns = columns_to_rename )
            df = df.filter( columns_to_keep )
        
        except:
            raise FileFormatError("MeteoProfile.import_custom_file: File could not be imported.")
            
        df = MeteoProfile.complete_irradiance_data( df, latitude, longitude, utc_offset = utc_offset )
        
        return df
    
    def import_meteo_data(
            
            self,
            
            latitude: Optional[ float ] = None,
            longitude: Optional[ float ] = None,
            
            ground_albedo: Optional[ float ] = 0.2,
            
            api_key: Optional[ str ] = None,
            
            tmy_file_path: Optional[ str | Path ] = None,
            ghi_col_name: Optional[ str ] = None,
            dni_col_name: Optional[ str ] = None,
            dhi_col_name: Optional[ str ] = None,
            Tamb_col_name: Optional[ str ] = None,
            utc_offset: Optional[ float ] = None,
            sep: Optional[ str ] = None,
            delimiter: Optional[ str ] = None,
            skiprows: Optional[ int ] = None,
            
            ):
        
        if latitude is not None:
            try:
                latitude = float( latitude )
            except:
                ValueError("MeteoPorfile.import_meteo_data: latitude must be convertible to type 'float'.")
        if longitude is not None:
            try:
                longitude = float( longitude )
            except:
                ValueError("MeteoPorfile.import_meteo_data: longitude must be convertible to type 'float'.")
                
        if latitude is not None or longitude is not None:
            if latitude is None or longitude is None:
                raise ValueError("MeteoProfile.import_meteo_data: latitude and longitude must be provided together.")
        
        if tmy_file_path is None:
            
            if latitude is None or longitude is None:
                raise ValueError("MeteoProfile.import_meteo_data: latitude and longitude must be provided if no data file is provided.")
            
            try:
                df_tmy = MeteoProfile.download_TMY(latitude, longitude, api_key)
            except OutOfChileError:
                raise ValueError("MeteoProfile.import_meteo_data: The location provided is not within the Chilean territory. A meteorological data file must be provided.")
            utc_offset = -4
                
        elif ghi_col_name is None and dni_col_name is None and dhi_col_name is None:
            
            file_format = MeteoProfile._get_file_format( tmy_file_path )
            
            coordinates_tolerance = 0.01
            if file_format == "Solar_Explorer":
                latitude_file, longitude_file, utc_offset, df_tmy = MeteoProfile.import_solar_explorer_file( tmy_file_path )
                
            elif file_format == "SAM":
                latitude_file, longitude_file, utc_offset, df_tmy = MeteoProfile.import_SAM_file( tmy_file_path )
                
            else:
                raise FileFormatError("MeteoProfile.import_meteo_data: The format of the data file could not be recognized. For custom files, the names of relevant columns must be specified.")
                
            if latitude is not None or longitude is not None:
                if abs( latitude - latitude_file ) > coordinates_tolerance:
                    warnings.warn("MeteoProfile.import_meteo_data: latitude value provided to the function does not match the latitude contained in the data file.")
                if abs( longitude - longitude_file ) > coordinates_tolerance:
                    warnings.warn("MeteoProfile.import_meteo_data: longitude value provided to the function does not match the longitude contained in the data file.")
            else:
                latitude = latitude_file
                longitude = longitude_file
                
        else:
            
            if latitude is None or longitude is None:
                raise ValueError("MeteoProfile.import_meteo_data: latitude and longitude must be provided along with custom-format data files.")
            
            df_tmy = MeteoProfile.import_custom_file(
                
                tmy_file_path,
                latitude,
                longitude,
                ghi_col_name = ghi_col_name,
                dni_col_name = dni_col_name,
                dhi_col_name = dhi_col_name,
                Tamb_col_name = Tamb_col_name,
                utc_offset = utc_offset,
                sep = sep,
                delimiter = delimiter,
                skiprows = skiprows
                
                )
            
        self.data_df = df_tmy
    
    @staticmethod
    def _get_file_format( file_path ):
        
        with open( file_path ) as file:
            first_line = file.readline().rstrip("\n")
            if first_line == "DATOS HORARIOS GENERADOS CON EL EXPLORADOR DE ENERGIA SOLAR PARA UN ANIO METEOROLOGICO TIPICO":
                return "Solar_Explorer"
            if first_line == "Source,Location ID,City,State,Country,Latitude,Longitude,Time Zone,Elevation":
                return "SAM"
            return None
        
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
        
        if argument_name == "tmy_file_path":
            try:
                value = Path( value )
            except:
                raise ValueError( "Class MeteoProfile: Argument 'tmy_file_path' must be convertible to type pathlib.Path." )
        
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
        api_key : str
            API key for the 'API Energias Renovables' website.
    
        Raises
        ------
        TMY_Error
        
            - Errors such as connection error, timeout error, incorrect API key, etc. Also raised when the latitude or longitude provided cannot be interpreted as floating point values.
            
            - If the site 'API Energias Renovables' is not able to produce the data requested because the location porvided is out of the allowed range.
    
        Returns
        -------
        df : pandas.DataFrame
            DataFrame containing the the data of a typical meteorological year (TMY) with the components: GHI, DNI, DHI, and ambient temperature. It has 8760 rows, one for each hour of a year. Irradiances are expressed in W/m2. Temperature is expressed in °C.
        altitude : float
            Altitude of the specified location (in meters).
    
        """
        
        global _api_key
        
        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except:
            raise TMY_Error("Function download_TMY: Parameters 'latitude' and 'longitude' must be convertible to type 'float'.")
        
        if api_key is None and _api_key is None:
            from .config import api_key as _api_key
            if _api_key is None:
                raise TMY_Error("MeteoProfile.download_TMY: No API key available. This key must either be provided as parameter to the function (argument 'api_key') or be saved with the function config.set_api_key.")
        elif api_key is None and _api_key is not None:
            api_key = _api_key
        
        if type( api_key ) is not str:
            raise TMY_Error( "MeteoProfile.download_TMY: api_key must be a string." )
            
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
                    extract_altitude = False
                    for line in lines:
                        if extract_altitude:
                            line_list = line.split(',')
                            altitude = float(line_list[-1])
                            extract_altitude = False
                        if line.startswith('Nombre,Longitud,Latitud,Altura Terreno (m)'):
                            extract_altitude = True
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
                    
                    return df, altitude
                
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
            
        except:
            raise TMY_Error("Function download_TMY: An unknown exception occurred when contacting 'API Energias Renovables' (url: https://api.minenergia.cl/).")
    
    def set_time_step(self, time_step):
        if hasattr(self, "_time_step") and self._time_step == time_step:
            return
        try:
            assert type(time_step) is int and time_step in [ 1, 2, 3, 4, 5, 6, 10, 12, 15, 20, 30, 60 ]
        except:
            raise ValueError("DemandProfile.set_time_step: time_step (in minutes) must be an integer within the possible values: 1, 2, 3, 4, 5, 6, 10, 12, 15, 20, 30, and 60")
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
        self._azimuth_profile = [ MeteoProfile.average_azimuth( self._azimuth_profile_minutal[ initial_minute : initial_minute + self._time_step ] ) for initial_minute in range(0, self._time_steps_per_year, self._time_step ) ]
    
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
        
    
    @staticmethod
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
                    raise ValueError("Function average_azimuth: midday found two times in a list.")
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
    
    def compute_poa_irradiance( self, solar_field ):
        
        coll_tilt_deg = solar_field.get_attribute( "coll_tilt" )
        coll_azimuth_deg = solar_field.get_attribute( "coll_azimuth" )
        coll_IAM = solar_field.get_attribute( "coll_IAM" )
        ground_fraction_covered = solar_field.get_attribute( "ground_fraction_covered" )
        row_width_to_coll_length_ratio = solar_field.get_attribute( "row_width_to_coll_length_ratio" )
        
        coll_tilt_rad = coll_tilt_deg*pi/180
        coll_azimuth_rad = coll_azimuth_deg*pi/180
        
        
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
            if solar_zenith == 0:
                solar_N = 0
                solar_E = 0
                solar_Z = 1
            elif solar_zenith == 180:
                solar_N = 0
                solar_E = 0
                solar_Z = -1
            else:
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
            if coll_E == 0 and coll_N == 0:
                trans = 0
                longi = 0
                aoi = 0
            elif coll_E == 0:
                trans = 0
                longi = arctan(abs(coll_N)/coll_Z)
                aoi = longi
            elif coll_N == 0:
                trans = arctan(abs(coll_E)/coll_Z)
                longi = 0
                aoi = trans
            else:
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
        
        assert len( self.DHI_Profile ) == len( self.DNI_Profile ) and len( self.DHI_Profile ) == len( self.GHI_Profile )
        
        for time_step in range( len( self.DNI_Profile ) ):
            
            if self.DHI_Profile[time_step] <= 0 and self.DNI_Profile[time_step] <= 0:
                
                First_Row_Irradiance_Profile.append( 0 )
                Shadeable_Rows_Irradiance_Profile.append( 0 )
                First_Row_IAM_Profile.append( 0 )
                Shadeable_Rows_IAM_Profile.append( 0 )
                
                continue
            
            aoi, longi, trans = incidence_angles( self.Zenith_Profile[time_step], self.Azimuth_Profile[time_step] )
            
            if doy_list is None:
                doy = int(time_step/self.time_steps_per_day) + 1
            else:
                doy = doy_list[ time_step ]
            relative_airmass = get_relative_airmass(self.Zenith_Profile[time_step], model = 'young1994')
            dni_extra = get_extra_radiation(doy)
            diff_irradiance = perez( coll_tilt_deg,
                                     coll_azimuth_deg,
                                     max([self.DHI_Profile[time_step], 0]),
                                     max([self.DNI_Profile[time_step], 0]),
                                     dni_extra,
                                     self.Zenith_Profile[time_step],
                                     self.Azimuth_Profile[time_step],
                                     relative_airmass,
                                     return_components = True )
            
            isotropic_irradiance_first_row = float( diff_irradiance['isotropic'] )
            isotropic_irradiance_shadeable_rows = isotropic_irradiance_first_row*diffuse_irradiance_fraction_shadeable_rows/diffuse_irradiance_fraction_non_shadeable_rows
            circumsolar_irradiance = float( diff_irradiance['circumsolar'] )
            horizon_irradiance = float( diff_irradiance['horizon'] )
            ref_irradiance = reflected_irradiance_fraction*ground_albedo*max([self.GHI_Profile[time_step], 0] )
            
            if aoi == None:
                
                beam_irradiance = 0
                beam_IAM = 0
                shading_factor = 0
                
            else:
                
                beam_irradiance = max( [ self.DNI_Profile[time_step]*cos(aoi), 0 ] ) + max( [ circumsolar_irradiance, 0 ] )
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
            
        self.First_Row_Irradiance_Profile = First_Row_Irradiance_Profile
        self.Shadeable_Rows_Irradiance_Profile = Shadeable_Rows_Irradiance_Profile
        self.First_Row_IAM_Profile = First_Row_IAM_Profile
        self.Shadeable_Rows_IAM_Profile = Shadeable_Rows_IAM_Profile
        
        self.Output_Profiles[ 'irradiance_first_row' ] = { 'output_type': 'irradiance', 'Profile': self.First_Row_Irradiance_Profile }
        self.Output_Profiles[ 'irradiance_shadeable_rows' ] = { 'output_type': 'irradiance', 'Profile': self.Shadeable_Rows_Irradiance_Profile }
        self.Output_Profiles[ 'IAM_first_row' ] = { 'output_type': 'ratio', 'Profile': self.First_Row_IAM_Profile }
        self.Output_Profiles[ 'IAM_shadeable_rows' ] = { 'output_type': 'ratio', 'Profile': self.Shadeable_Rows_IAM_Profile }
        