Fluids
======

**SERCpy's** "fluids" module is able to model pure water, water-glycol mixtures, and some commercial heat transfer fluids. All the models are generated with results of the library `CoolProp <https://coolprop.org/>`_.

Fluids other than water are assumed to be incompressible liquids; hence, pressure is not relevant for their properties. For water, absolute pressure must be specified by the user when initializing a :doc:`Fluid <fluid_class>` instance; this value determines the boiling temperature of the fluid. Absolute pressures from 20,000 to 4,000,000 Pa are supported, and water vapor properties are modeled for temperatures up to 350 °C.

The two main classes of this module are:

.. list-table::
   :class: borderless
   :widths: 30 70

   * - ``--verbose``
     - Print detailed output.
   * - ``--output PATH``
     - Write results to PATH.

:doc:`Fluid <fluid_class>`: Instances of this class store how the properties of the fluid change with temperature. Thus, it is the class that models the fluid.

:doc:`FluidState <fluidstate_class>`: etsgdfdf

The class that stores how the fluid's properties change with temperature is the class :doc:`Fluid <fluid_class>`, whereas the class :doc:`FluidState <fluidstate_class>` stores the properties for a fixed temperature or specific enthalpy value.

.. toctree::
  :hidden:

  fluid_class
  fluidstate_class
