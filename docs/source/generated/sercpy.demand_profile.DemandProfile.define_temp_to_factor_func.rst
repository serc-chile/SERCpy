DemandProfile.define_temp_to_factor_func
========================================

One of the main features of DemandProfile instances is that they are capable of modeling how thermal demand varies because of changes in ambient temperature.

The method used by SERCpy is based on the `Paper presented by Jesper et al. (DOI: 10.1016/j.ecmx.2021.100085) <https://www.sciencedirect.com/science/article/pii/S2590174521000106>`_.

The authors of the aforementioned work proposed to classify thermal loads in four discrete levels of dependence of the thermal demand on ambient temperature. The result of applying their method can be visualized in the image below, which shows how the same yearly thermal energy demand gets distributed on a monthly basis by assuming each of the four levels of dependence, which are identified by the integers 0 to 3.

.. figure:: /images/Tamb_dependence_img.png
   :alt: Yearly thermal demand profiles assuming different levels of ambient temperature dependence
   :width: 600px
   :align: center
   
   Results of the same yearly thermal energy demand being distributed throughout the year while assuming different levels of dependence of thermal demand on ambient temperature.

The energy demand profiles shown in the image were generated with a temperature profile obtained from `Chilean Ministry of Energy's "Solar Energy Explorer <https://solar.minenergia.cl/inicio>`_, using the San Joaquin Campus of the `Pontifical Catholic University of Chile <https://www.uc.cl/en>`_ as a location.

.. currentmodule:: sercpy.demand_profile

.. automethod:: DemandProfile.open_profile_app
