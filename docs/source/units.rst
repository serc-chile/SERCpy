Units
=====

SERCpy has its own unit management module, which has the feature that it can convert mass to volume and viceversa, and also mass flowrate to volumetric flowrate and viceversa, if the density of the substance involved is known.

Internally, classes and simulations work with SI units, except for temperature which is in °C. Nevertheless, the user can specify most variables with various possible units, and they are converted to the default system when processed.

Flowrates are expressed as mass flowrates by default, although they can easily be converted to volumetric flowrates as just discussed.

The main tool to work with units is the function `convert_units`, which belongs to the module `units` and is documented below.

Available units
---------------

Temperature
~~~~~~~~~~~

Available temperature units are:

  - `"K"` or `"°K"`: Kelvin
  - `"C"` or `"°C"`: Celsius
  - `"F"` or `"°F"`: Fahrenheit
  - `"R"` or `"°R"`: Rankine




Unit converting function
------------------------

.. autofunction:: sercpy.units.convert_units
