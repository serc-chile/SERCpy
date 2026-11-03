Azimuthal angles
================

Both for identifying the solar position in the sky and for specifying the orientation of a solar collector field, an azimuthal angle is needed.
Unlike other angles such as the collector tilt or the solar zenith, the azimuthal angle may cause confusion since there are different possible, and plausible, ways of specifying it.

**SERCpy** uses the same convention as `pvlib <https://pvlib-python.readthedocs.io/en/stable/>`_, which could be summarized as "degrees east of north".
This means that north, east, south, and west correspond to 0°, 90°, 180°, and 360° respectively. See the image below for more clarification.
Azimuthal angles alwatys have to be larger than or equal to zero, and less than 360. The number 360 is not allowed because it is equivalent to 0. Angles are always specified in degrees.

.. figure:: /images/azimuth.png
   :alt: Azimuthal angle convention used by SERCpy
   :width: 400px
   :align: center

   Azimuthal angles corresponding to each cardinal direction, according to the convention used by **SERCpy**
