Fluid naming
============

A general rule that applies to all fluid names is that upper- and lower cases are indistinguishable to the platform, so the user does not have to worry about this. Moreover, special characters such as spaces, hyphens, dots, commas, and percentage signs are also ignored.

Water
-----

For pure water, acceptable names are `"w"` and `"water"`.

Water-glycol mixtures
---------------------

Water-glycol mixtures with both ethylene glycol and propylene glycol are supported.


        String defining the name of the fluid. Upper-case and lower-case variations introduced by the user are ignored, as well as spaces, hyphens, and percentage signs. For pure **water**, accepted values are "w" and "water".
        For **water-glycol mixtures**, the name must specify first the type of glycol, and then the percentage of glycol present in the mixture. Accepted glycol types are `"ethylene glycol"` or `"eg"` for ethylene glycol, and `"propylene glycol"` or `"pg"` for propylene glycol.
        Examples of acceptable names in this context are: `"ethylene glycol 60%"`, `"EG 40"`, `"propylene glycol 30%"`, and `"pg20"`. **Note**: The number after the ethylene glycol type is **always** interpreted as a percentage, regardless of whether it has a percentage sign.
        The maximum percentage allowed is 60%. For other **commercial heat transfer fluids** such as thermal oils, see the document on fluid naming.
