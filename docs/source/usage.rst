Usage
=====

.. _installation:

Installation
------------

To use SERCpy, first install it using pip:

.. code-block:: console

   (.venv) $ pip install sercpy

Setting the API key for "Energias Renovables" by Chile's Ministry of Energy
------------

If you are going to simulate solar energy systems within the Chilean territory and have an API key for `Ministry of Energy's "Energias Renovables" website <https://api.minenergia.cl>`_, use the following code lines to store the key and use it in the future without introducing it every time:

.. doctest::

   >>> from sercpy.config import set_api_key
   >>> set_api_key( "your_API_Key_as_a_string" )

You can then check whether the API key was saved successfully:

.. doctest::

   >>> from sercpy.config import api_key
   >>> print( api_key )
   your_API_Key_as_a_string

Creating demand profiles
----------------

To compute and obtain the demand conditions of a thermal load throughout an entire operation year, use the class ``DemandProfile``:

.. autoclass:: sercpy.thermal.demand_profile.DemandProfile


