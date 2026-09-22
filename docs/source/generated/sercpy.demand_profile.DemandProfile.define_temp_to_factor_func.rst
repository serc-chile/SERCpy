DemandProfile.define_temp_to_factor_func
========================================

One of the main features of DemandProfile instances is that they are capable of modeling how thermal demand varies because of changes in ambient temperature.

The method used by SERCpy is based on the `Paper presented by Jesper et al. (DOI: 10.1016/j.ecmx.2021.100085) <https://www.sciencedirect.com/science/article/pii/S2590174521000106>`_

The authors of that work proposed to classify thermal loads in four discrete levels of dependence of the thermal demand on ambient temperature. 

.. figure:: /images/Tamb_dependence_img.png
   :alt: Yearly thermal demand profiles assuming different levels of ambient temperature dependence
   :width: 600px
   :align: center

   The same total yearly demand 

.. currentmodule:: sercpy.demand_profile

.. automethod:: DemandProfile.open_profile_app
