Fluids
======

**SERCpy's** "fluids" module is able to model pure water, water-glycol mixtures, and some commercial heat transfer fluids. All the models are generated with results of the library `CoolProp <https://coolprop.org/>`_.

The class that stores how the fluid's properties change with temperature is the class `Fluid`, whereas the class `FluidState` store the properties for a fixed temperature or specific enthalpy value.

Contents
--------

.. toctree::
   :maxdepth: 2
   :titlesonly:
  
   fluid_naming

.. currentmodule:: sercpy.fluids

.. autoclass:: Fluid

.. autoclass:: FluidState
