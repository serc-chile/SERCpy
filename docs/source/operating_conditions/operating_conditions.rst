System Operating Conditions
===========================

After having established a :doc:`Meteorological Profile </meteo_profile/meteo_profile>` and a :doc:`Demand Profile </demand_profile/demand_profile>`, the class `OperatingConditions` establishes the definitive profiles that will be passed to the solar system simulation. This class carries out two main tasks:

- It matches the demand schedule stored in the `DemandProfile` instance to the time zone data stored in the `MeteoProfile` instance. This includes eventual time shifts due to daiylight saving time.
- It converts the minutal data stored in these two objects to profiles lower time resolution. If needed, it can also keep the minutal resolution.

.. currentmodule:: sercpy.meteo_profile

.. autoclass:: MeteoProfile
