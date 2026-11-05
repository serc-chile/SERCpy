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

Providing the "Incidence Angle Modifier" curve
---------------------------------------------

The IAM (Incidence Angle Modifier) curve is a feature of solar collectors that is published in most performance test reports. It indicates how the efficiency of the collector changes as a function of the angle with which the irradiance reaches the collector.

The IAM of the solar collector must be specified through the initialization argument `IAM`. This section clarifies the formats that this parameter can have.

Mono-axial IAM function
~~~~~~~~~~~~~~~~~~~~~~~

For most flat plate solar collectors, IAM can be considered to be a function of the angle of incidence (AOI), which is defined as the angle of the solar position with respect to a vector that is normal to the collector's plane. In other words, when the sun is pointing "directly" to the collector, the AOI is zero, and any deviation from that direction corresponds to the AOI. With mono-axial IAM curves, the correction factor that must be applied is completely defined by the AOI.

.. _iam_curve_from_list_of_values:

IAM curve from a list of values
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

One of the most common ways of defining the IAM curve is to report the values of the IAM correction factor for different AOI values, e.g. every ten degrees from `AOI=0°` to `AOI=90°`. If this is the case, the `IAM` argument can simply be a `list <https://docs.python.org/3/builtins/stdtypes.html#typesseq-list>`_ of the values reported. Some rules have to be taken into account:

- It is assumed that the first value of the list corresponds to `AOI=0` and the last one corresponds to `AOI=90`. Thus, the first value of the list is expected to be `1`, whereas the last value is expected to be `0`.
- The list can have any number of values. It is assumed that the values correspond to evenly-spaced angles. This means that, for a list with ten values, the values should correspond to AOI values equal to 0°, 10°, 20°, 30°, etc.

ASHRAE IAM model
^^^^^^^^^^^^^^^^

A common way of simplifying the definition of the IAM curve is to define it from a single value, commonly denoted as :math:`b`, and the formula:

.. math::

   K( \theta ) = 1 - b \; \left ( \frac{1}{ \cos ( \theta ) } - 1 \right )

where :math:`K` is the correction factor associated to IAM, and :math:`\theta` is the AOI.

To apply this IAM model to the `SolarCollector` class, the value of the argument `IAM` has to be a floating point number (`float <https://docs.python.org/3/builtins/functions.html#float>`_) representing the value of :math:`b`.

Extended ASHRAE model
^^^^^^^^^^^^^^^^^^^^^

A way to make the ASHRAE model more accurate is to extend the formula in the following way:

.. math::

   K( \theta ) = 1 - b_0 \; \left ( \frac{1}{ \cos ( \theta ) } - 1 \right ) - b_1 \; \left ( \frac{1}{ \cos ( \theta ) } - 1 \right ) ^ 2 - b_2 \; \left ( \frac{1}{ \cos ( \theta ) } - 1 \right ) ^ 3 ...

To apply this model to the `SolarCollector` class, the argument `IAM` must be a `dictionary <https://docs.python.org/3/tutorial/datastructures.html#dictionaries>`_ with the following format:

`IAM = { "b0": b0_value, "b1": b1_value, "b2": b2_value, .... }`

where `b0_value`, `b1_value`, `b2_value` are `float <https://docs.python.org/3/builtins/functions.html#float>`_ values representing :math:`b_0`, :math:`b_1`, and :math:`b_2` of the equation above. The dictionary can contain as many values as desired, provided that all indexes from `0` to the last index are present in the dictionary.

Bi-axial IAM function
~~~~~~~~~~~~~~~~~~~~~

For some collectors, particularly tubular ones, AOI is not enough to define the IAM correction factor, because the direction to which the sun is deviated from the normal makes a difference. Therefore, the angle of incidence is decomposed into two angles:

- The **transversal angle** is the projection of the incidence angle onto a plane that is normal to the tubes' direction.
- The **longitudinal angle** is the projection of the incidence angle onto a plane that is perpendicular to the last one defined, and also perpendicular to the collector's plane.

The IAM of collectors for which this angle decomposition is needed, is usually reported with two curves:

- A curve typically denoted as :math:`K_t`, which represents the IAM curve for transversal angles.
- A curve typically denoted as :math:`K_l`, which represents the IAM curve for longitudinal angles.

To provide these two curves to the `SolarCollector` instance, a `dictionary <https://docs.python.org/3/tutorial/datastructures.html#dictionaries>`_ must be constructed which has the keys `"Kl"` and `"Kt"`. The variable associated with each of these keys must be a `list <https://docs.python.org/3/builtins/stdtypes.html#typesseq-list>`_, with the same requirements discussed in the previous section :ref:`iam_curve_from_list_of_values`. Thus, the dictionary should look as follows:

`IAM = { "Kl": [ l0, l1, l2, ... ] , "Kt": [ t0, t1, t2, ... ] }`

where `l0`, `l1`, `l2`, `t0`, `t1`, `t2` are `float <https://docs.python.org/3/builtins/functions.html#float>`_ values representing the IAM curve associated to each component of the incidence angle.
