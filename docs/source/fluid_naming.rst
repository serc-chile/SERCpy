Fluid naming
============

**SERCpy's** `Fluid` class is able to model pure water, water-glycol mixtures, and some commercial heat transfer fluids. All the models are gerenated with results of the library `CoolProp <https://coolprop.org/>`_

A general rule that applies to all fluid names is that upper- and lower cases are indistinguishable to the platform, so the user does not have to worry about this. Moreover, special characters such as spaces, hyphens, dots, commas, and percentage signs are also ignored.

Water
-----

For pure water, acceptable names are `"w"` and `"water"`.

Water-glycol mixtures
---------------------

Water-glycol mixtures with both ethylene glycol and propylene glycol are supported.
