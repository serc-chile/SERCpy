Dependence on ambient temperature
=================================

Depending on the type of thermal load involved, the heat demand can be more or less dependent on the environmental conditions.
An obvious example is the case of space heating, where the demand can be negligible in summer in comparison to winter.

One of the main features of **SERCpy's** DemandProfile class is that it is capable of modeling how thermal demand varies because of changes in ambient temperature.

The method used by **SERCpy** is based on the `paper presented by Jesper et al. (DOI: 10.1016/j.ecmx.2021.100085) <https://www.sciencedirect.com/science/article/pii/S2590174521000106>`_.

The authors of the aforementioned work proposed to classify thermal loads in four discrete levels of dependence of the thermal demand on the ambient temperature. The result of applying their method can be visualized in the image below, which shows how the same yearly thermal energy demand gets distributed on a monthly basis by assuming each of the four levels of dependence, which are identified by the integers 0 to 3. The temperature profile used to generate the demand profiles was obtained from `Chilean Ministry of Energy's "Solar Energy Explorer" <https://solar.minenergia.cl/inicio>`_, using the San Joaquin Campus of the `Pontifical Catholic University of Chile <https://www.uc.cl/en>`_ as location.

.. figure:: /images/Tamb_dependence_img.png
   :alt: Yearly thermal demand profiles assuming different levels of ambient temperature dependence
   :width: 600px
   :align: center
   
   Results of the same yearly thermal energy demand being distributed throughout the year while assuming different levels of dependence of thermal demand on ambient temperature.

The thermal demand is determined on a daily basis using the average temperature of the corresponding day to obtain a scalar factor that is proportional to the total demand of that day. The dependence level determines how much that scalar factor changes depending on the daily temperature. It was also stated by the authors of the `study <https://www.sciencedirect.com/science/article/pii/S2590174521000106>`_ that the accuracy of the algorithm can be improved by obtaining a corrected version of the daily temperature that also considers the temperature of the three preceding days:

.. math::

   T_{i, corr} = \frac{ T_i + 0.5 \cdot T_{i-1} + 0.25 \cdot T_{i-2} + 0.125 \cdot T_{i-3}  }{1+0.5+0.25+0.125}

Two limitations of the method just exposed are the following:

   - **The levels of dependence are discrete.** As can be seen in the picture, the first dependence level (0) corresponds to a thermal load that presents almost no dependence on ambient temperature, whereas in the second level (1), the thermal demand in June and July is more than twice the demand in December and January. Therefore, there is a considerable spectrum of intermediate cases being left aside.
   - **Most users do now know to which dependence level they belong.** The numbers associated with each dependence level (integers 0 to 3) have little mathematical meaning, other than "the larger the value, the steeper the increase in demand when temperature drops". Thus, this classification method has little applicability without a method to determine the level of dependence of each user.

