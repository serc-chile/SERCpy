Fluids
======

**SERCpy's** "fluids" module is able to model pure water, water-glycol mixtures, and some commercial heat transfer fluids. All the models are generated with results of the library `CoolProp <https://coolprop.org/>`_.

Fluids other than water are assumed to be incompressible liquids; hence, pressure is not relevant for their properties. For water, absolute pressure must be specified by the user when initializing a :doc:`Fluid <fluid_class>` instance; this value determines the boiling temperature of the fluid. Absolute pressures from 20,000 to 4,000,000 Pa are supported, and water vapor properties are modeled for temperatures up to 350 °C.

The two main classes of this module are:

:doc:`Fluid <fluid_class>`
    Instances of this class store how the properties of the fluid change with temperature. Thus, it is the class that models the fluid.

:doc:`FluidState <fluidstate_class>`
    Instances of this class store the properties for a single temperature value of a :doc:`Fluid <fluid_class>` instance.

.. toctree::
  :hidden:

  fluid_class
  fluidstate_class

Examples
--------

Water
~~~~~

.. code-block:: python

    # Import Fluid
    from sercpy.fluids import Fluid

    # Initialize a model for water at 2 bar absolute pressure
    water = Fluid( 'water', p = 200000 )

    # Print the vaporization enthalpy
    print( water.h_fg )

Therminol 66
~~~~~~~~~~~~

.. code-block:: python

    # Initialize a model for Therminol 66
    therminol = Fluid( 'Therminol 66' )

    # Define an instance of FluidState for the object just defined at 180 °C
    state_180 = therminol.state( T = 180 )
    
    # Print the density and specific heat capacity at that temperature
    print( f"Density at 180 °C: { state_180.D }" )
    print( f"Specific heat capacity at 180 °C: { state_180.cp }" )
