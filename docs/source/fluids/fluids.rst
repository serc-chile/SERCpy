Fluids
======

**SERCpy's** "fluids" module is able to model pure water, water-glycol mixtures, and some commercial heat transfer fluids. All the models are generated with results of the library `CoolProp <https://coolprop.org/>`_.

Fluids other than water are assumed to be incompressible liquids; hence, pressure is not relevant for their properties. For water, absolute pressure must be specified by the user when initializing a :doc:`Fluid <fluid_class>` instance; this value determines the boiling temperature of the fluid. Absolute pressures from 20,000 to 4,000,000 Pa are supported, and water vapor properties are modeled for temperatures up to 350 °C.

The two main classes of this module are:

:doc:`Fluid <fluid_class>`
    Instances of this class store how the properties of the fluid change with temperature. Thus, it is the class that models the fluid.

:doc:`FluidState <fluidstate_class>`
    Instances of this class store the properties for a single temperature value of a :doc:`Fluid <fluid_class>` instance.

Contents
--------

.. toctree::
  :maxdepth: 2

  fluid_class
  fluidstate_class
