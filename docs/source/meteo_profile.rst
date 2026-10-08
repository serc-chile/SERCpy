Meteorological Profiles
=======================

Introduction
------------

The first and most fundamental step for achieving an accurate simulation of a solar energy system is to have precise data of the solar resource in the place where the simulation is carried out. **SERCpy** works with a kind of meteorological data known as "typical meteorological year" (TMY). Such a dataset is constructed by taking several years of meteorological data, and then constructing a single year by concatenating months of different years that are closest to the "expected conditions" for that month. Data of this type commonly has hourly resolution (i.e. 8760 data samples in total), but **SERCpy** can also process data files with up to 1-minute resolution, always considering that the data encompasses an entire year.  

Another factor that can greatly influence the performance of a solar energy system, and contribute to determine the scale of the storage device needed, is how power demand by the thermal load and availability of solar irradiance are sinchronized in time. In addition to the features of the class :doc:`DemandProfile <demand_profile_class>`, which allow the user to establish highly detailed demand profiles, the class :doc:`MeteoProfile <meteo_profile_class>` can automatically detect the time zone to which a certain location corresponds; this includes the eventual use of daylight saving time. Why is this important? Not considering this factor would cause that, in practice, energy demand gets displaced in time by one hour during approximately half of the year. 

Follow the :doc:`examples/MeteoProfile_tutorial` to get familiarized with the different construction modes of the class and some of the most relevant construction parameters, and then see the :doc:`documentation of the class and its methods <meteo_profile_class>` to delve deeper into the available functionalities and the parameters they work with.

Contents
--------

.. toctree::
  :maxdepth: 2

  meteo_profile_class
  examples/MeteoProfile_tutorial


