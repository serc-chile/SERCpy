# -*- coding: utf-8 -*-
"""
Created on Mon Aug 17 12:33:21 2026

@author: Adrian Riebel Brummer
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

def _mean_squared_error(list_1, list_2):
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
    ValueError
        When the arguments are not two lists of the same length, or their length
        is equal to zero.

    Returns
    -------
    float
        MSE result.

    """
    if len( list_1 ) != len( list_2 ) or len( list_1 ) == 0:
        raise ValueError("core._mean_squared_error: Arguments of the funcion must be two lists of the same length ( > 0 ).")
    return sum( [ ( x - y )**2 for x, y in zip( list_1, list_2 ) ] ) / len( list_1 )