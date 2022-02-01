from typing import List
from enum import Enum

from soma.controller import Controller, Literal, directory
from soma.undefined import undefined

class PathFinder(Controller):
    ...


class BIDSFolder(Enum):
    sourcedata = 'sourcedata'
    rawdata = 'rawdata'
    derivative = 'derivative'


class BIDS(PathFinder):
    dataset_directory: directory()
    folder: Literal['sourcedata', 'rawdata', 'derivative'] = 'derivative'
    sub: str
    ses: str
    data_type: str
    task: str = None
    acq: str = None
    ce: str = None
    rec: str = None
    run: str = None
    echo: str = None
    part: str = None
    modality: str
    extension: str


    def build_path(self):
        '''
        The path has the following pattern:
          {folder}/sub-{sub}/ses-{ses}/{data_type}/sub-{sub}_ses-{ses}[_task-{task}][_acq-{acq}][_ce-{ce}][_rec-{rec}][_run-{run}][_echo-{echo}][_part-{part}]{modality}.{extension}
        '''
        
        path_list = [self.dataset_directory,
                     self.folder,
                    f'sub-{self.sub}'
                    f'ses-{self.ses}',
                    self.data_type]

        filename = [f'sub-{self.sub}',
                    f'ses-{self.ses}']
        for key in ('task', 'acq', 'ce', 'rec', 'run', 'echo', 'part'):
            value = gatattr(self, key)
            if value:
                filename.append(f'{key}-{value}')
        filename.append(f'{self.modality}.{self.extension}')
        path_list.append('_'.join(filename))
        return osp.join(*path_list)


class BrainVISA(PathFinder):
    dataset_directory: directory()
    center: str
    subject: str
    modality: str = None
    process: str = None
    analysis:str
    acquisition: str = None
    preprocessings: str = None
    longitudinal: list[str] = None
    prefix: str = None
    suffix: str = None
    extension: str = None

    def build_path(self):
        '''
        The path has the following pattern:
        {center}/{subject}/[{modality}/][{process/][{acquisition}/][{preprocessings}/][{longitudinal}/]{analysis}/[{prefix}_]{subject}[_to_avg_{longitudinal}}[_{suffix}][.{extension}]
        '''

        path_list = [dataset_directory,
                     self.center,
                     self.subject]
        for key in ('modality', 'process', 'acquisition', 'preprocessings', 'longitudinal'):
            value = gatattr(self, key)
            if value:
                path_list.append(value)
        path_list.append(self.analysis)

        filename = []
        if self.prefix:
            filename.append(f'{self.prefix}_')
        filename.append(self.subject)
        if self.longitudinal:
            filename.append(f'_to_avg_{self.longitudinal}')
        if self.suffix:
            filename.append(f'_{self.suffix}')
        if self.extension:
            filename.append(f'.{self.extension}')
        path_list.append(''.join(filename))
        return osp.join(*path_list)


    def values_for_center(self):
        if not osp.exists(self.dataset_directory):
            return 'Select a valid dataset_directory first'
        return os.listdir(self.dataset_directory)

    def values_for_center(self):
        if not osp.exists(self.dataset_directory):
            return 'Select a valid dataset_directory first'
        if not self.center:
            return 'Select a center first'
        
        return os.listdir(osp.join(self.dataset_directory, self.center))



