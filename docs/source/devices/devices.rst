Devices
=======

.. currentmodule:: sercpy.devices

The concept of "device", in the context of **SERCpy**, encompasses the classes that model the components of a solar thermal energy system, such as:

- :doc:`Solar collectors and solar fields <solar/solar>`
- :doc:`Storage tanks <storage/storagetank_class>`
- :doc:`Heat Exchangers <heat_exchanger/heat_exchanger_class>`
- :doc:`Controllers <controller/controller>`
- :doc:`Pumps <pump/pump>`

.. toctree::
  :hidden:

  solar/solar
  storage/storagetank_class
  heat_exchanger/heat_exchanger_class
  controller/controller
  pump/pump

Main features of a device-type class
------------------------------------

In order for a class to be used as a device in a **SERCpy** simulation, it has to fulfill two basic requirements:

  - Method `compute_outputs`
      This is the method that gets called in every iteration of the simulation. No values are expected to be returned by this method; it is just expected to change the object's attributes. Two arguments (positional or keyword) are expected:

          - `operating_conditions`: Dictionary returned by :doc:`OperatingConditions <operating_conditions/operating_conditions>`' method `get_conditions`.
          - `iteration_number`: Number of the iteration within the time step. The first iteration should have the value `0`. This argument should **NOT** be confused with the time step number, which defines the moment in time that is being simulated. The time step number is not directly passed to the `compute_outputs` method; instead of that, it is used to determine the argument `operating_conditions`.

  - Attribute `convergence`
      This boolean value should become `True` when the device-type instance is in the right conditions to stop the iterations for the current time step. For most devices, this imples that the input values used to compute the outputs were similar enough in consecutive iterations. Some devices, however, such as :doc:`pumps <pump/pump>` and :doc:`controllers <controller/controller>`, require additional conditions to be satisfied.

.. _class_device:

Device (base class)
-------------------

.. autoclass:: Device

.. _class_outlet:

Outlet
------

.. autoclass:: Outlet
