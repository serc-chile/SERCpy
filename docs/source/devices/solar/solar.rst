Solar module
============

The module `sercpy.solar` contains two classes that are essential for **SERCpy**:
  
:doc:`SolarCollector <solar_collector_class>`
    Class that stores the features of an individual solar thermal collector.

:doc:`SolarField <solar_field_class>`
    Class that contains the information on how (and how many) collectors are arranged in a solar field. It is the class that actually carries out the computations to recreate the behavior of an actual solar field.

From these two classes, the only one that is properly a "device" is `SolarField`, in the sense that it has the necessary methods and attributes to interact with other device-type objects in the context of a simulation. `SolarCollector`, on the other hand, contains functions and attributes that are called by the `SolarField` instance to compute its results.

.. toctree::
  :hidden:

  solar_collector_class
  solar_field_class
