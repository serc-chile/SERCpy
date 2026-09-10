Usage
=====

.. _installation:

Installation
------------

**The library will soon be available for installation via pip.**

Setting the API key for "Energias Renovables" by Chile's Ministry of Energy
---------------------------------------------------------------------------

If you are going to simulate solar energy systems within the Chilean territory and have an API key for `Ministry of Energy's "Energias Renovables" website <https://api.minenergia.cl>`_, use the following code lines to store the key and use it in the future without introducing it every time:

.. doctest::

   >>> from sercpy.config import set_api_key
   >>> set_api_key( "your_API_Key_as_a_string" )

You can then check whether the API key was saved successfully:

.. doctest::

   >>> from sercpy.config import api_key
   >>> print( api_key )
   your_API_Key_as_a_string

After doing this, meteorological data files will be downloaded automatically from the aforementioned site when initializing simulations within the Chilean territory.

Running a simulation in 3 steps
-------------------------------

1. Creating the meteorological profile
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In order to generate a meteorological profile...

2. Creating the demand profile
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To compute and obtain the demand conditions of a thermal load throughout an entire operation year, use the class ``DemandProfile``:

.. autoclass:: sercpy.thermal.demand_profile.DemandProfile


3. Configuring the solar energy system
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The solar system consists of...
