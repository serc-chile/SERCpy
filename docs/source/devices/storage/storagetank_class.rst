StorageTank
===========

Storage tanks are an essential component for most low-temperature solar thermal systems. They allow to store the solar energy, so that it can be delivered to the load when irradiance is not derectly available.

.. currentmodule:: sercpy.storage

.. autoclass:: StorageTank

Methods
-------

.. autosummary::
   :toctree: generated/

   StorageTank.compute_outputs

.. _inlet_outlet_ports_definition:

Setting the positions of the inlet/outlet ports
-----------------------------------------------

**Why do ports' positions matter?** As discussed above, vertical storage tanks tend to get stratified, which is a desirable behavior. Because of this, the temperature with which the heat transfer fluid leaves the tank depends on the height of the outlet port. The `StorageTank` model assumes that the fluid leaves the tank with the same temperature as the node where the output is located.

The positions of the inlet- and outlet ports in the tank can be specified at initialization with the parameter `io_relative_heights`, but this is not mandatory. In fact, if the `StorageTank` instance is used as part of one of the pre-defined system layouts included in **SERCpy**, the ports' positions are set automatically if they have not been set by the user.

The parameter `io_relative_heights` expresses the height of each port as a `float <https://docs.python.org/3.15/builtins/functions.html#float>`_ number in the range 0 - 1, where `0` corresponds to the bottom of the tank, and `1` corresponds to the top of the tank. The expected format for this parameter is a list of pairs, as follows:

`io_relative_heights = [ ( inlet_1_height, outlet_1_height ), ( inlet_2_height, outlet_2_height ), ... ]`

Where `inlet_1_height`, `outlet_1_height`, `inlet_2_height`, and `outlet_2_height` are values in the range 0 - 1 as already discussed. Internally, the `StorageTank` instance determines to which node each height corresponds.

As the user may have noticed, the parameter `io_relative_heights` not only specifies where the inlets and outlets are located, but also how many inlet/outlet pairs the tank has. When computing its outputs, the `StorageTank` instance treats the flowrates entering the tank through the inlet ports as imposed operating conditions, and sets the flowrate in each outlet to the same value as the flowrate that is entering the tank thorugh the inlet of the same inlet/outlet pair. 

Setting the ports' positions after initialization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

As discussed above, it is not mandatory to specify the heights of the inlet- and outlet ports when initializing the tank. The parameter `io_relative_heights` can simply be skipped.

Nevertheless, it is necessary that this feature of the tank is specified before calling the method :meth:`StorageTank.compute_outputs` for the first time. To set the inlet/outlet heights after initialization, the method :meth:`StorageTank.set_io_relative_heights` must be called. This method can also be used to *change* inlet/outlet positions defined previously. However, the number of inlet/outlet pairs must be conserved.

The main purpose of this feature is that the inlet/outlet positions get set internally by **SERCpy** when the tank is included in one of the pre-defined system layouts.

.. _inlet_flow_modeling:

Inlet flow modeling
-------------------

As already stated, the flows leaving the tank are assumed to have the same temperature as the node where the outlet is physically located.

For inlet flows, there is a harder question to answer: which node does an entering flow actually *enter*? This question comes from a simple fact: when an entering flow has a different temperature from the fluid inside the tank at the height where the inlet is located, the flow tends rise or sink due to density differences.

The user can set how inlet flows are modeled through the parameter `inlet_mode`. This parameter must be a string and can have three values:

   `"fixed_inlets"`
      The flows that enter the tank are assumed to stay in the node where the inlet is physically located. One could say that, with this inlet mode, the phenomenon just discussed is being neglected, but this is actually not true because of the :ref:`algorithm to correct temperature inversions <temperature_inversions>`.
   `"temperature_seeking"`
      The flows are assumed to flow directly to the node that is closest to their temperature. This model becomes unrealistic when the node that best matches the inlet flow's temperature is several nodes appart from where the inlet is actually located.
   `"AFD"`
      This string stands for "Advanced Flowrate Distribution", which is
      a model presented by Saloux and Candanedo in 2019[2]_.
      This modeling method can be described as a way of establishing a continuum between the two models just discussed.

.. _temperature_inversions:

Temperature inversions
----------------------

A stratified tank keeps a temperature difference between its top part and its bottom part, with the top part being hotter than the bottom part. This temperature difference can be maintained during relatively long periods of time because the hotter fluid has a lower density; hence, it does not tend to mix with the fluid below it.

A "temperature inversion" is a state in which the fluid in a certain part of the tank is hotter than the fluid above it. This condition is not stable, since the hot fluid will quickly rise or mix with the fluid layers above it.

In the `StorageTank` model, a temperature inversion can occur when, by the end of a time step, the temperature computed for a certain node is higher than the temperature of the nodes above it. This is corrected by mixing the nodes involved in the temperature inversion, so that there are no temperature inversions at the moment of computing the next time step. This correction algorithm is used more intesively when the parameter `inlet_mode` is set to `"fixed_inlets"` (see :ref:`inlet_flow_modeling`).
