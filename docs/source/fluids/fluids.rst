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
    print( f"Water vaporization enthalpy: {water.h_fg} J/kg" )

Therminol 66
~~~~~~~~~~~~

.. code-block:: python

    # Import Fluid
    from sercpy.fluids import Fluid

    # Initialize a model for Therminol 66
    therminol = Fluid( 'Therminol 66' )

    # Define an instance of FluidState for the object just defined at 180 °C
    state_180 = therminol.state( T = 180 )
    
    # Print the density and specific heat capacity at that temperature
    print( f"Density of Therminol 66 at 180 °C: { state_180.D } kg/m3" )
    print( f"Specific heat capacity of Therminol 66 at 180 °C: { state_180.cp } J/kg °C" )

Water-glycol mixtures
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # Import Fluid
    from sercpy.fluids import Fluid

    # Initialize a model for a mixture of 40% propylene glycol v/v
    # Reference properties are computed at 80 °C
    glycol_mixture = Fluid( "propylene glycol 40%", T_ref = 80, mixture_type = 'v/v' )

    # Print reference density, cp, and thermal conductivity
    print( f"Reference density: { glycol_mixture.D_ref } kg/m3" )
    print( f"Reference cp: { glycol_mixture.cp_ref } J/kg °C" )
    print( f"Reference thermal conductivity: { glycol_mixture.k_ref } kg/m3" )
    
    # Print the maximum and minimum temperature the model supports
    print( f"Maximum temperature available: { glycol_mixture.T_max } °C" )
    print( f"Minumum temperature available: { glycol_mixture.T_min } °C" )
