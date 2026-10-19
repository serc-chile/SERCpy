Fluid naming
============

A general rule that applies to all fluid names is that upper- and lower cases are indistinguishable to the platform, so the user does not have to worry about this. Moreover, special characters such as spaces, hyphens, and percentage signs are also ignored.

Water
-----

For pure water, acceptable names are `"w"` and `"water"`.

Water-glycol mixtures
---------------------

Water-glycol mixtures with both ethylene glycol and propylene glycol are supported. To specify a mixture, the string must contain both the glycol type involved and the glycol percentage, e.g. `"ethylene glycol 40%"`. For ethylene glycol, both `"ethylene glycol"` and `"eg"` are valid as names, whereas for propylene glycol, `"propylene glycol"` and `"pg"` are valid. The number after the glycol type is **always** interpreted as a percentage, without the need to add a percentage symbol (`"%"`). Moreover, **only integer percentage values are valid**. Since dots are ignored, a percentage value equal to `"25.8"` will be read as `"258"`; this will throw an error. On the other hand, a percentage equal to "`5.5`" will be read as 55; this will be accepted but will be interpreted as a different percentage from the one specified by the user.

Hence, some examples of valid mixtures are:

- `"Ethylene Glycol 30"`
- `"ethylene glycol 42%"`
- `"EG50"`
- `"propylene glycol 48%"`
- `"PG5"`


        String defining the name of the fluid. Upper-case and lower-case variations introduced by the user are ignored, as well as spaces, hyphens, and percentage signs. For pure **water**, accepted values are "w" and "water".
        For **water-glycol mixtures**, the name must specify first the type of glycol, and then the percentage of glycol present in the mixture. Accepted glycol types are `"ethylene glycol"` or `"eg"` for ethylene glycol, and `"propylene glycol"` or `"pg"` for propylene glycol.
        Examples of acceptable names in this context are: `"ethylene glycol 60%"`, `"EG 40"`, `"propylene glycol 30%"`, and `"pg20"`. **Note**: The number after the ethylene glycol type is **always** interpreted as a percentage, regardless of whether it has a percentage sign.
        The maximum percentage allowed is 60%. For other **commercial heat transfer fluids** such as thermal oils, see the document on fluid naming.
