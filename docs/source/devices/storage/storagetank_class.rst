StorageTank
===========

Instances of the class `SolarCollector` store the features of the individual collectors that make up a solar field, such as the size and the parameters of the efficiency curve.


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

`io_relative_heights = [ ( inlet_1_height, outlet_1_height ), ( inlet_2_height, outlet_2_height )  ]`

Where `inlet_1_height`, `outlet_1_height`, `inlet_2_height`, and `outlet_2_height` are values in the range 0 - 1 as already discussed. Internally, the `StorageTank` instance determines to which node each height corresponds.

As the user may have noticed, the parameter `io_relative_heights` not only specifies where the inlets and outlets are located, but also how many inlet/outlet pairs the tank has. When computing its outputs, the `StorageTank` instance treats the flowrates entering the tank through the inlet ports as imposed operating conditions, and sets the flowrate in each outlet to be the same as the flowrate that is entering the tank thorugh the inlet of the same inlet/outlet pair. 

