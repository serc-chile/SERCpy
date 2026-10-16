# -*- coding: utf-8 -*-
"""
Created on Wed Oct 14 09:46:22 2026

@author: Adrian Riebel Brummer
"""

class Outlet:
    
    pass

class Device:
    
    def set_inputs( self, **kwargs ):
        
        if "flowrate" in self._needed_tolerances and not "flowrate_tolerance" in kwargs:
            raise ValueError( f"{type(self).__name__}.set_inputs: 'flowrate_tolerance' must be specified." )
        
    
    def set_connections(  )