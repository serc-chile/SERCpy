Units
=====

SERCpy has its own unit management module, which has the feature that it can convert mass to volume and viceversa, and also mass flowrate to volumetric flowrate and viceversa, if the density of the substance involved is known.

Internally, classes and simulations work with SI units, except for temperature which is in °C. Furthermore, flowrates are internally treated as mass flowrates, although they can easily be converted to volumetric flowrates as just discussed. Nevertheless, the user can specify most variables with various possible units, and they are converted to the default system when processed. This section details all the possible units available to the user.

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

Time
~~~~

Available time units are:

  - `"s"` or `"second"`
  - `"min"` or `"minute"`
  - `"h"` or `"hr"` or `"hour"`
  - `"day"`
  - `"year"`

Energy
~~~~~~

Available energy units are:

  - `"J"` or `"j"`: Joule
  - `"kJ"` or `"kj"`: Kilojoule
  - `"MJ"`: Megajoule
  - `"GJ"`: Gigajoule
  - `"TJ"`: Terajoule
  - `"BTU"` or `"btu"`: British Thermal Unit
  - `"kBTU"` or `"kbtu"`: Kilo-BTU
  - `"MBTU"`: Mega-BTU
  - `"Wh"`: Watt-Hour
  - `"kWh"`': Kilowatt-Hour
  - `"MWh"`: Megawatt-Hour
  - `"GWh"`: Gigawatt-Hour

Pressure
~~~~~~~~

Available pressure units are:

  - `"Pa"` or `"pa"`: Pascal 
  - `"kPa"` or `"kpa"`: Kilopascal 
  - `"MPa"` or `"Mpa"`: Megapascal 
  - `"bar"`: Bar
  - `"mbar"`: Milibar
  - `"atm"` or `"ATM"`: Atmosphere
  - `"mmHg"` or `"mmhg"`: Milimeter of mercury
  - : 
  - `"psi"`: 
  - `"PSI"`: 

Unit converting function
------------------------

.. autofunction:: sercpy.units.convert_units
