#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

try:
    from traits.api import CTrait
except ImportError:
    from enthought.traits.api import CTrait


_type_to_trait_id = {
    int: 'Int',
    unicode: 'Unicode',
    str: 'Str',
    float: 'Float'
}


def trait_ids(trait):
    """Return the type of the trait: File, Enum etc...

    Parameters
    ----------
    trait: trait instance (mandatory)
        a trait instance

    Returns
    -------
    main_id: list
        the string description (type) of the input trait
    """
    main_id = trait.handler.__class__.__name__
    #print main_id
    inner_ids = []
    if main_id == 'TraitCoerceType':
        real_id = _type_to_trait_id.get(trait.handler.aType)
        if real_id:
            main_id = real_id
    elif main_id == 'TraitCompound':
        #print trait.handler, dir(trait.handler)
        #print trait.handler.handlers
        trait_description = []
        for sub_trait in trait.handler.handlers:
            sub_c_trait = CTrait(0)
            sub_c_trait.handler = sub_trait
            trait_description.extend(trait_ids(sub_c_trait))
        return trait_description
    else:
        inner_id = '_'.join((trait_ids(i)[0]
                             for i in trait.handler.inner_traits()))
        if not inner_id:
            klass = getattr(trait.handler, 'klass', None)
            if klass is not None:
                inner_ids = [i.__name__ for i in klass.__mro__]
            else:
                inner_ids = []
        else:
            inner_ids = [inner_id]
    if inner_ids:
        return [main_id + '_' + i for i in inner_ids]
    else:
        return [main_id]
