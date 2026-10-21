Class Fluid
===========

.. currentmodule:: sercpy.fluids

.. autoclass:: Fluid

.. _fluid_naming:

Fluid naming
------------

As presented in the documentation of the class :class:`Fluid <Fluid>`, the most fundamental (and the only always-needed) parameter to initialize this class is the argument `fluid_name`, which defines the type of fluid. This section clarifies how to introduce this parameter correctly.

A general rule that applies to all fluid names is that upper- and lower cases are indistinguishable to the platform, so the user does not have to worry about this. Spaces and hyphens are also irrelevant.

Water
~~~~~

For pure water, acceptable names are `"w"` and `"water"`.

Water-glycol mixtures
~~~~~~~~~~~~~~~~~~~~~

Water-glycol mixtures with both ethylene glycol and propylene glycol are supported. To specify a mixture, the string must contain both the glycol type involved and the glycol percentage, e.g. `"ethylene glycol 40%"`. For ethylene glycol, both `"ethylene glycol"` and `"eg"` are valid as names, whereas for propylene glycol, `"propylene glycol"` and `"pg"` are valid. The number after the glycol type is **always** interpreted as a percentage, without the need to add a percentage symbol (`"%"`). Moreover, **only integer percentage values are valid**; e.g. `"12"` is valid, while `"12.5"` is not. The maximum percentage value allowed is 60%.

Hence, some examples of valid mixture names are:

- `"Ethylene Glycol 30"`
- `"ethylene glycol 42%"`
- `"EG50"`
- `"propylene glycol 60%"`
- `"propyleneglycol10%"`
- `"PG5"`

Commercial heat transfer fluids
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The commercial heat transfer fluids supported by **SERCpy** are:

- Therminol 55
- Therminol 66
- Therminol 72
- Therminol VP-1
- Therminol D-12
- Dowtherm A
- Dowtherm J
- Dowtherm Q
- Dynalene HC10
- Dynalene HC20
- Dynalene HC30
- Dynalene HC40
- Dynalene HC50
- Dynalene SF
- Paratherm CR
- Paratherm GLT
- Paratherm HE
- Paratherm HR
- Paratherm LR
- Paratherm MR
- Paratherm NF
- Syltherm 800
- Syltherm XLT
- Texatherm 22

All these names, when turned into `Python strings <https://docs.python.org/3/builtins/stdtypes.html#text-sequence-type-str>`_, are valid as values for the argument `fluid_name`.
