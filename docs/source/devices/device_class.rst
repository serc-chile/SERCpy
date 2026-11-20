Device (base class)
===================

.. currentmodule:: sercpy.devices

As stated below in the :ref:`documentation of the class Device <class_device>`, this is not a class meant to be used directly, but as a base to develop inherited classes.

Main features of a device-type class
------------------------------------

In order for a class to be used as a device in a **SERCpy** simulation, it has to fulfill two basic requirements:

  - Method `compute_outputs`
      This is the method that gets called in every iteration of the simulation. No values are expected to be returned by this method; it is just expected to change the object's attributes. Two arguments (positional or keyword) are expected:

          - `operating_conditions`: Dictionary returned by :doc:`OperatingConditions <operating_conditions/operating_conditions>`' method `get_conditions`.
          - `iteration_number`: Number of the iteration within the time step. The first iteration should have the value `0`. This argument should **NOT** be confused with the time step number, which defines the moment in time that is being simulated. The time step number is not directly passed to the `compute_outputs` method; instead of that, it is used to determine the argument `operating_conditions`.

  - Attribute `convergence`
      This boolean value should become `True` when the device-type object is in the right conditions to stop the iterations for the current time step. For most devices, this implies that the input values used to compute the outputs were similar enough in consecutive iterations. Some devices, however, such as :doc:`pumps <pump/pump>` and :doc:`controllers <controller/controller>`, require additional conditions to be satisfied.

.. _class_device:

.. autoclass:: Device

Device methods
--------------

.. toctree::
  :hidden:

  device_methods/set_connections_method
  device_methods/set_convergence_criteria_method
  device_methods/compute_input_convergence_method
