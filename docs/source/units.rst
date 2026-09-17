Units
=====

SERCpy has its own unit management module, called "units", which has the feature that it can convert mass to volume and viceversa, and also mass flowrate to volumetric flowrate and viceversa, if the density of the substance involved is known.

Internally, classes and simulations work with SI units, except for temperature which is expressed in °C. Furthermore, flowrates are internally treated as mass flowrates, although they can easily be converted to volumetric flowrates as just discussed. Nevertheless, the user can specify most variables with various possible units, and they are converted to the default system when processed. This section details all the possible units available to the user.

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
  - `"cal"`: **Small** calorie, equivalent to 4.184 J
  - `"kcal"`: Kilo-Calorie or **large** calorie, equivalent to 4184 J
  - `"Mcal"`: Mega-Calorie, equivalent to 1,000,000 small calories
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
  - `"psi"` or `"PSI"`: Pounds per square inch 

Area
~~~~

Available area units are:

  - `"m2"`: Square meter
  - `"cm2"`: Square centimeter
  - `"hm2"`: Square hectometer, equivalent to 10,000 square meters
  - `"in2"`: Square inch
  - `"ft2"`: Square foot
  - `"ha"` or `"Ha"` or `"HA"`: Hectare, equivalent to 1 square hectometer

Volume
~~~~~~

Available volume units are:

  - `"m3"`: Cubic meter
  - `"L"`: Liter
  - `"ft3"`: Cubic foot
  - `"in3"`: Cubic inch
  - `"gal"` or `"gallon"`: US gallon, equivalent to 231 cubic inches or, approximately, 3.7854 L
  - `"bbl"` or `"barrel"`: US standard oil barrel, equivalent to 158.99 L
  - `"dm3"`: Cubic decimeter, equivalent to 1 L
  - `"cm3"`: Cubic centimeter
  - `"mm3"`: Cubic milimeter

Mass
~~~~

Available mass units are:

  - `"kg"` or `"KG"`: Kilogram
  - `"g"`: Gram
  - `"Mg"`: Megagram, equivalent to 1 metric ton
  - `"mg"`: Miligram
  - `"lb"`: Pound
  - `"short_ton"` or `"short ton"` or `"st"`: Short ton, equivalent to 2,000 lb
  - `"metric_ton"` or `"metric ton"` or `"tonne"`: Metric ton, equivalent to 1,000 kg

The platform avoids the use of the unit name `"ton"` because it may lead to confussion between the concepts of "short ton", equivalent to 2,000 lb, and metric ton or tonne, equivalent to 1,000 kg.

Power
~~~~~

Power is a special type of quantity because the units can be created from the energy and time units already specified (see  :ref:`compound_units`), and also be chosen from the following list of named units:
  
  - `"W"` or  `"w"`: Watt 
  - `"kW"` or `"kw"`: Kilowatt 
  - `"MW"` or `"Mw"`: Megawatt
  - `"HP"` or `"hp"` or `"Hp"`: Horsepower

.. _compound_units:

Compound units
~~~~~~~~~~~~~~

Some quantities relevant for SERCpy are expressed in units that do not have a specific name, but are instead constructed from more basic units. A simple example is mass flowrate, which is expressed in terms of `M/t`, where `M` is a mass unit and `t` is a time unit.

The rules for constructing units are the following:

  - Division of units is expressed with `"/"`.
  - Multiplication of units is expressed by placing a space between the units.
  - All units at the right side of `"/"` are interpreted as being raised to `-1`. For example, in the case of specific heat capacity units, `"J/kg K"` is correct without the need to put `"kg K"` between parenthesis.

Quantities that can be constructed in this way are:

  - Mass flowrate units: `"M/t"`
  - Volumetric flowrate units: `"V/t"`
  - Power units: `"E/t"`
  - Density units: `"M/V"`
  - Specific heat capacity units: `"E/M T"`
  - Specific energy units (e.g heating value of fuels): `"E/M"`

Where:

  - `M` stands for any mass unit
  - `V` stands for any volume unit
  - `E` stands for any energy unit
  - `T` stands for any temperature unit
  - `t` stands for any time unit

Unit converting function
------------------------

The main tool that allows to work with different units is the function `convert_units`, which is documented below. This function is used internally by the functions and classes to convert the units specified by the user to the default unit system; therefore, it is not crucial for the user to learn to use this function.

.. autofunction:: sercpy.units.convert_units
