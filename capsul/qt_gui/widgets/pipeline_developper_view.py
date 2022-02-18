# -*- coding: utf-8 -*-
"""
This is a compatibility module for the former, misspelled,
pipeline_developper_view (with two "p"s) which should be spelled
pipeline_developer_view.
It contains a compatibility class, PipelineDevelopperView (with two "p"s) which
should be spelled PipelineDeveloperView now. This class issues a deprecation
warning and otherwise behaves the same.
"""

from .pipeline_developer_view import *
import warnings


warnings.warn(
    'capsul.pipeline_developper_view is deprecated. Please use '
    'capsul.pipeline_developer_view (with one "p") instead.',
    DeprecationWarning)


class PipelineDevelopperView(PipelineDeveloperView):
    '''
    This is a compatibility class for the former, misspelled,
    PipelineDevelopperView (with two "p"s) which should be spelled
    PipelineDeveloperView now. This class issues a deprecation warning and
    otherwise behaves the same.
    '''
    def __init__(self, pipeline=None, parent=None, show_sub_pipelines=False,
                 allow_open_controller=False, logical_view=False,
                 enable_edition=False, userlevel=0):

        warnings.warn(
            'PipelineDevelopperView is deprecated. Please use '
            'PipelineDeveloperView (with one "p") instead.',
            DeprecationWarning)
        super(PipelineDevelopperView, self).__init__(
            pipeline=pipeline, parent=parent,
            show_sub_pipelines=show_sub_pipelines,
            allow_open_controller=allow_open_controller,
            logical_view=logical_view,
            enable_edition=enable_edition,
            userlevel=userlevel)
