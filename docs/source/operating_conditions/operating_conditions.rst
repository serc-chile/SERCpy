System Operating Conditions
===========================

After having established a :doc:`Meteorological Profile </meteo_profile/meteo_profile>` and a :doc:`Demand Profile </demand_profile/demand_profile>`, the class `OperatingConditions` extracts the data stored by the instances of these two classes and establishes the definitive profiles that will be passed to the solar system simulation. The two main tasks carried out by `OperatingConditions` instances are:

- To match the demand schedule stored in the `DemandProfile` instance to the time zone data stored in the `MeteoProfile` instance. This includes eventual time shifts due to daiylight saving time.
- To convert the minutal data stored in these two objects to profiles with lower time resolution. The minutal resolution can also be conserved by setting the time step to 1 minute.

.. currentmodule:: sercpy.operating_conditions

.. autoclass:: OperatingConditions
