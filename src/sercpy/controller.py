# -*- coding: utf-8 -*-
"""
Created on Sat Nov 14 23:18:38 2026

@author: Adrian Riebel Brummer
"""

class ControlSignal:
    """
    Object that stores the control signal of a controller.
    
    Like the class :ref:`Outlet <class_outlet>`, it has the purpose of being used
    to establish the connection between the controller and the devices
    that receive its signals.
    
    Attributes
    ----------
    signal_value : float
        Value in the range 0 - 1, representing the output signal of the controller.
        
    signal : float
        Alias for `signal_value`.
    
    """
    @property
    def signal_value(self):
        if not hasattr( self, "_signal_value" ):
            raise AttributeError("ControlSignal: signal value has not been assigned.")
        return self._signal_value
    
    @signal_value.setter
    def signal_value( self, value ):
        try:
            value = float( value )
        except:
            raise TypeError("ControlSignal: signal value must be a float.")
        if not ( value >= 0 and value <= 1 ):
            raise ValueError("ControlSignal: signal value must be in the range 0 <= signal_value <= 1.")
        self._signal_value = value
    
    @property
    def signal(self):
        return self.signal_value
    
    @signal.setter
    def signal(self, value):
        self.signal_value = value