# -*- coding: utf-8 -*-
''' Data selection, parsing, filtering from
    :py:mod:`FOM definitions <soma.fom>`.

Ex: find all raw T1 MRIs in a Bids sourcedata or rawdata directory::

    from capsul.datasel.data_selector import get_data_selector

    data_dir = '/home/hericart/raw_data'
    sel = get_data_selector(data_dir, fom='raw-bids-1.0',
                            upstream_selector={'type': 'exhaustive'})
    data = sel.get_data(
        data_types=['morphologist.capsul.import_t1_mri.ImportT1Mri.input'])

Here sel is a chain of 2 selectors: a :class:`~.data_parser.DataParser` which takes inputs from a :class:`~.data_selector.ExhaustiveDataSelector`. It is needed to parse every file in the data directory, otherwise only files matching the first possible pattern for the ``ImportT1Mri.input`` parameter will be considered.

We could also filter data, using the same selector::

    data = sel.get_data(
        data_types=['morphologist.capsul.import_t1_mri.ImportT1Mri.input'],
        data_filters={'.*': {'session': '2'}})

The returned ``data`` is a list. Each element of this list is a tuple
``(data_type, items)``, where ``data_type`` is one of the required ``data_types`` in the query, and items is a list of dicts. Each dict has a ``path`` key, and normally (there are exceptions) an ``attributes`` dict containing :py:mod:`FOM attributes <soma.fom>`.

Ex: query some Morphologist outputs in a database::

    data_dir = '/home/charles-axel/morphologist_data'
    sel = get_data_selector(data_dir, fom='morphologist-auto-1.0')
    data = sel.get_data(
        data_types=[
            'morphologist.capsul.morphologist.Morphologist.split_brain',
            'morphologist.capsul.morphologist.Morphologist.left_labelled_graph',
            'morphologist.capsul.morphologist.Morphologist.right_labelled_graph'
        ],
        type_labels=['split', 'left graph', 'right graph'],
        data_filters={'.*_graph': {'sulci_recognition_session': 'deep_cnn'}}
    )

If the database is large, we can build and use a SQLite database for it::

    data_dir = '/home/charles-axel/morphologist_data'
    sel = get_data_selector(data_dir, fom='morphologist-auto-1.0', type='sqlite')
    sel.build_sqlite_index(
        data_type='morphologist.capsul.morphologist.Morphologist.split_brain')
    # here split_brain does not matter actually, only the process is used.

    # then query:
    sel = get_data_selector(data_dir, type='sqlite')
    data = sel.get_data(
        data_types=[
            'morphologist.capsul.morphologist.Morphologist.split_brain',
            'morphologist.capsul.morphologist.Morphologist.left_labelled_graph',
            'morphologist.capsul.morphologist.Morphologist.right_labelled_graph'
        ],
        type_labels=['split', 'left graph', 'right graph'],
        data_filters={'.*_graph': {'sulci_recognition_session': 'deep_cnn'}}
    )

We can also save the data dict and reuse it in a filter selector::

    import json

    # save using a dict structure
    json_filename = '/tmp/select.json'
    with open(json_filename, 'w') as f:
        json.dump(dict(data), f)

    # then use a filter which reads from the JSON file
    # (we could directly use the dict instead of the JSON file, also):
    sel = get_data_selector(
            data_dir,
            type='filter',
            upstream_selector={'dict_list': json_filename})
    data = sel.get_data(
        data_types=['morphologist.capsul.morphologist.Morphologist.left_labelled_graph'],
        data_filters={'.*': {'sulci_recognition_session': 'deepcnn'}})
'''
