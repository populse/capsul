# -*- coding: utf-8 -*-
import unittest
import sys
import os
import os.path as osp
import shutil
import tempfile
import json
from pathlib import Path

from soma.controller import undefined

from capsul.dataset import ProcessMetadata, ProcessSchema
from capsul.api import (Capsul, executable, Pipeline)


class HemiPipeline(Pipeline):

    def pipeline_definition(self):
        self.add_process(
            'gw_segment',
            'capsul.pipeline.test.fake_morphologist.greywhiteclassificationhemi.GreyWhiteClassificationHemi',
            make_optional=['fix_random_seed', 'histo_analysis', 'edges', 'commissure_coordinates', 'lesion_mask_mode'])
        self.add_process(
            'gw_mesh',
            'capsul.test.test_tiny_morphologist.ProcessHemisphere')
        self.add_link('gw_segment.grey_white->gw_mesh.input')
        self.export_parameter('gw_segment', 'grey_white', 'gw_classif')
        self.do_not_export = [('gw_segment', 'side'), ('gw_segment', 'fix_random_seed'), ('gw_segment', 'histo_analysis'), ('gw_segment', 'edges'), ('gw_segment', 'commissure_coordinates'), ('gw_segment', 'lesion_mask_mode'), ('gw_segment', 'lesion_mask')]


class TestPipeline(Pipeline):

    def pipeline_definition(self):
        self.add_process('nobias', 'capsul.test.test_tiny_morphologist.BiasCorrection')

        self.add_switch('normalization', ['none', 'fakespm12', 'aims'], ['output'])
        self.add_process(
            'fakespm_normalization_12', 'capsul.test.test_tiny_morphologist.FakeSPMNormalization12')
        self.add_process('aims_normalization', 'capsul.test.test_tiny_morphologist.AimsNormalization')
        self.add_process('split', 'capsul.test.test_tiny_morphologist.SplitBrain')
        self.add_process('left_hemi', 'capsul.test.test_completion.HemiPipeline')
        self.add_process('right_hemi', 'capsul.test.test_completion.HemiPipeline')
        self.nodes['right_hemi'].nodes['gw_segment'].side = 'right'

        self.add_link('nobias.output->normalization.none_switch_output')

        self.add_link('nobias.output->fakespm_normalization_12.input')
        self.add_link('fakespm_normalization_12.output->normalization.fakespm12_switch_output')
        self.export_parameter('fakespm_normalization_12', 'template')
        self.add_link('nobias.output->aims_normalization.input')
        self.add_link('aims_normalization.output->normalization.aims_switch_output')

        self.export_parameter('nobias', 'output', 'nobias')

        self.add_link('normalization.output->split.input')
        self.export_parameter('normalization', 'output', 'normalized')
        self.add_link('split.left_output->left_hemi.split_brain')
        self.add_link('nobias.output->left_hemi.t1mri_nobias')
        self.export_parameter('left_hemi', 'gw_classif', 'left_gw_classif')
        self.export_parameter('left_hemi', 'output', 'left_gw_mesh')
        self.add_link('split.right_output->right_hemi.split_brain')
        self.add_link('nobias.output->right_hemi.t1mri_nobias')
        self.export_parameter('right_hemi', 'gw_classif', 'right_gw_classif')
        self.export_parameter('right_hemi', 'output', 'right_gw_mesh')



class TestPipelineBIDS(ProcessSchema, schema='bids',
                       process=TestPipeline):
    _ = {
        '*': {'pipeline': 'test_pipeline'}
    }

class TestPipelineBrainVISA(ProcessSchema, schema='brainvisa',
                            process=TestPipeline):
    _ = {
        '*': {'process': 'test_pipeline'},
    }
    _nodes = {
        'split': {
            'left_output':{'side': 'L'},
            'right_output': {'side': 'R'},
        }
    }


datasets = {
    'input': 'input',
    'template': 'shared',
    'nobias': 'output',
    'normalized': 'output',
    'left_gw_classif': 'output',
    'left_gw_mesh': 'output',
    'right_gw_classif': 'output',
    'right_gw_mesh': 'output',
}


class TestCompletion(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.tmp = Path(self.tmp_dir)

        self.bids = brainvisa = self.tmp / 'bids'
        self.brainvisa = brainvisa = self.tmp / 'brainvisa'

        # Configuration base dictionary
        config = {
            'builtin': {
                'config_modules': [
                    'capsul.test.test_fake_morphologist',
                ],
                'dataset': {
                    'input': {
                        'path': str(self.bids),
                        'metadata_schema': 'bids',
                    },
                    'output': {
                        'path': str(self.brainvisa),
                        'metadata_schema': 'brainvisa',
                    },
                    'shared': {
                        'path': str(self.brainvisa),
                        'metadata_schema': 'shared',
                    },
                }
            }
        }

        self.capsul = Capsul('test_fake_morphologist')
        self.capsul.config.import_dict(config)


    def tearDown(self):
        if hasattr(self, 'tmp_dir'):
            if os.path.exists(self.tmp_dir):
                shutil.rmtree(self.tmp_dir)
            del self.tmp_dir
        Capsul.delete_singleton()

    def test_pipeline_completion(self):

        pipeline = executable('capsul.test.test_completion.TestPipeline')

        engine = self.capsul.engine()
        execution_context = engine.execution_context(pipeline)
        input = str(self.tmp / 'bids'/'rawdata'/'sub-aleksander'/'ses-m0'/'anat'/'sub-aleksander_ses-m0_T1w.nii')

        # write an input file which should exist
        os.makedirs(osp.dirname(input))
        with open(input, 'w') as f:
            f.write('INPUT\n')

        metadata = ProcessMetadata(pipeline, execution_context,
                                   datasets=datasets)

        input_metadata = execution_context.dataset['input'].schema.metadata(
            input)

        self.assertEqual(input_metadata, {
            'folder': 'rawdata',
            'sub': 'aleksander',
            'ses': 'm0',
            'data_type': 'anat',
            'suffix': 'T1w',
            'extension': 'nii',
        })

        metadata.bids = input_metadata
        metadata.generate_paths(pipeline)

        params = dict((i,
            getattr(pipeline, i, undefined)) for i in ('input', 'template',
                'nobias', 'normalized', 'left_gw_classif', 'left_gw_mesh', 'right_gw_classif', 'right_gw_mesh'))

        expected = {
            'input': '!{dataset.input.path}/rawdata/sub-aleksander/ses-m0/anat/sub-aleksander_ses-m0_T1w.nii',
            'template': '!{fakespm.directory}/template',
            'nobias': '!{dataset.output.path}/whaterver/aleksander/test_pipeline/m0/default_analysis/nobias_aleksander.nii',
            'normalized': '!{dataset.output.path}/whaterver/aleksander/test_pipeline/m0/default_analysis/nobias_aleksander.nii',
            'left_gw_classif': '!{dataset.output.path}/whaterver/aleksander/test_pipeline/m0/default_analysis/segmentation/Lgrey_white_aleksander.nii',
            'left_gw_mesh': '!{dataset.output.path}/whaterver/aleksander/test_pipeline/m0/default_analysis/Laleksander.nii',
            'right_gw_classif': '!{dataset.output.path}/whaterver/aleksander/test_pipeline/m0/default_analysis/segmentation/Rgrey_white_aleksander.nii',
            'right_gw_mesh': '!{dataset.output.path}/whaterver/aleksander/test_pipeline/m0/default_analysis/Raleksander.nii',
        }

        self.maxDiff = 3000
        self.assertEqual(params, expected)

    @unittest.skip('not working yet')
    def test_iteration_completion(self):

        expected_completion = {
            'input': [
                '!{dataset.input.path}/rawdata/sub-aleksander/ses-m0/anat/sub-aleksander_ses-m0_T1w.nii',
                '!{dataset.input.path}/rawdata/sub-aleksander/ses-m0/anat/sub-aleksander_ses-m0_T1w.nii',
                '!{dataset.input.path}/rawdata/sub-aleksander/ses-m0/anat/sub-aleksander_ses-m0_T1w.nii',
            ],
            'right_gw_classif': [
                '!{dataset.output.path}/whaterver/aleksander/test_pipeline/m0/default_analysis/segmentation/Rgrey_white_aleksander.nii',
                '!{dataset.output.path}/whaterver/aleksander/test_pipeline/m0/default_analysis/segmentation/Rgrey_white_aleksander.nii',
                '!{dataset.output.path}/whaterver/aleksander/test_pipeline/m0/default_analysis/segmentation/Rgrey_white_aleksander.nii',
            ],
        }

        expected_resolution = {
        }

        pipeline = self.capsul.executable_iteration(
            'capsul.test.test_completion.TestPipeline',
            non_iterative_plugs=['template'])

        engine = self.capsul.engine()
        execution_context = engine.execution_context(pipeline)

        input = str(self.tmp / 'bids'/'rawdata'/'sub-aleksander'/'ses-m0'/'anat'/'sub-aleksander_ses-m0_T1w.nii')

        # write an input file which should exist
        os.makedirs(osp.dirname(input))
        with open(input, 'w') as f:
            f.write('INPUT\n')

        metadata = ProcessMetadata(pipeline, execution_context,
                                   datasets=datasets)

        input_metadata = execution_context.dataset['input'].schema.metadata(
            input)

        normalizations = ['none', 'aims', 'fakespm12']
        inputs = [input_metadata] * 3
        pipeline.normalization = normalizations
        metadata.bids = inputs
        metadata.generate_paths(pipeline)

        self.maxDiff = 11000
        for name, value in expected_completion.items():
            self.assertEqual(getattr(pipeline, name), value,
                             f'Differing value for parameter {name}')
        pipeline.resolve_paths(execution_context)
        for name, value in expected_resolution.items():
            self.assertEqual(getattr(pipeline, name), value,
                             f'Differing value for parameter {name}')


def test():
    """ Function to execute unitest
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCompletion)
    runtime = unittest.TextTestRunner(verbosity=2).run(suite)
    return runtime.wasSuccessful()


if __name__ == "__main__":
    print("RETURNCODE: ", test())
    if '-v' in sys.argv[1:]:
        from soma.qt_gui.qt_backend import Qt
        from capsul.qt_gui.widgets.pipeline_developer_view \
            import PipelineDeveloperView

        app = Qt.QApplication.instance()
        if app is None:
            app = Qt.QApplication([])

        pipeline = executable('capsul.test.test_completion.TestPipeline')

        pv = PipelineDeveloperView(
            pipeline, allow_open_controller=True, enable_edition=True,
            show_sub_pipelines=True)
        pv.auto_dot_node_positions()
        pv.show()
        app.exec_()
