SolarCollector
==============

Instances of the class `SolarCollector` store the features of the individual collectors that make up a solar field, such as the size and the parameters of the efficiency curve.


.. currentmodule:: sercpy.solar

.. autoclass:: SolarCollector

Methods
-------

.. autosummary::
   :toctree: generated/

   SolarCollector.compute_outlet_state
   SolarCollector.compute_IAM
   SolarCollector.compute_flowrate_correction_factor

.. _iam_argument:

Defining the "Incidence Angle Modifier" curve
---------------------------------------------

The IAM (Incidence Angle Modifier) curve is a feature of solar collectors that is published in most performance test reports. It indicates how the efficiency of the collector changes as a function of the angle with which the irradiance reaches the collector.

Mono-axial IAM function
~~~~~~~~~~~~~~~~~~~~~~~

For most flat plate solar collectors, IAM can be considered to be a function of the angle of incidence (AOI), which is defined as the angle of the sun with respect to a vector which is normal to the collector's plane. In other words, when the sun is pointing "directly" to the collector, the AOI is zero, and any deviation from that direction is measured by the AOI.

