Demand Profiles
===============

Introduction
------------

Solar energy is intermittent by nature. For this reason, being able to estimate the power demanded by a thermal load with a high time-resolution is a crucial step in the development of an accurate simulation of a solar thermal energy system that would, eventually, deliver energy to that thermal load.

Another factor that can greatly impact the performance of a solar thermal system is the fact that thermal loads tend to demand more energy during time periods in which solar energy availability is lower, such as winter, and on days with lower temperature in general.

:doc:`DemandProfile <demand_profile_class>` is a class provided by **SERCpy** that seeks to address both of these issues. It offers the users several construction modes so that they can choose the one that best matches their case and the data they have access to.

Follow the :doc:`DemandProfile_tutorial` to get familiarized with the different construction modes of the class and some of the most relevant construction parameters, and then see the :doc:`documentation of the class and its methods <demand_profile_class>` to delve deeper into the functionalities and the parameters.

Contents
--------

.. toctree::
  :maxdepth: 2

  demand_profile_class
  Tamb_dependence
  examples/DemandProfile_tutorial

