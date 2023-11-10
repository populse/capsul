import json
import os
import os.path as osp
import shutil
import tempfile
import unittest

from soma.controller import undefined

from capsul.config import ApplicationConfiguration
from capsul.config.configuration import (
    default_engine_start_workers,
    default_builtin_database,
)

expected_default_builtin_database = default_builtin_database.copy()
expected_default_builtin_database["path"] = osp.expandvars(
    expected_default_builtin_database["path"]
).format(app_name="single_conf")


class TestConfiguration(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        if hasattr(self, "tmp_dir"):
            if os.path.exists(self.tmp_dir):
                shutil.rmtree(self.tmp_dir)
            del self.tmp_dir

    def test_single_configuration(self):
        user_file = osp.join(self.tmp_dir, "user_conf.json")
        conf_dict = {
            "builtin": {
                "database": "builtin",
                "persistent": True,
                "start_workers": default_engine_start_workers,
                "matlab": {},
                "spm": {
                    "spm12_standalone": {
                        "directory": "/usr/local/spm12_standalone",
                        "standalone": True,
                    },
                    "spm8": {
                        "directory": "/usr/local/spm8",
                        "standalone": False,
                        "version": "8",
                    },
                },
            },
            "databases": {
                "builtin": default_builtin_database,
            },
        }
        with open(user_file, "w") as f:
            json.dump(conf_dict, f)
        app_config = ApplicationConfiguration("single_conf", user_file=user_file)
        self.maxDiff = 2500
        self.assertEqual(
            app_config.asdict(),
            {
                "app_name": "single_conf",
                "site": {
                    "builtin": {
                        "database": "builtin",
                        "persistent": True,
                        "start_workers": default_engine_start_workers,
                    },
                    "databases": {
                        "builtin": expected_default_builtin_database,
                    },
                },
                "user": conf_dict,
                "merged_config": conf_dict,
                "user_file": user_file,
            },
        )

    def test_config_as_dict(self):
        conf_dict = {
            "builtin": {
                "database": "builtin",
                "persistent": True,
                "start_workers": default_engine_start_workers,
                "matlab": {},
                "spm": {
                    "spm12_standalone": {
                        "directory": "/usr/local/spm12_standalone",
                        "standalone": True,
                    },
                    "spm8": {
                        "directory": "/usr/local/spm8",
                        "standalone": False,
                        "version": "8",
                    },
                },
            },
            "databases": {
                "builtin": default_builtin_database,
            },
        }

        app_config = ApplicationConfiguration("single_conf", user=conf_dict)
        self.maxDiff = None
        self.assertEqual(
            app_config.asdict(),
            {
                "app_name": "single_conf",
                "site": {
                    "builtin": {
                        "persistent": True,
                        "database": "builtin",
                        "start_workers": default_engine_start_workers,
                    },
                    "databases": {
                        "builtin": expected_default_builtin_database,
                    },
                },
                "user": conf_dict,
                "merged_config": conf_dict,
            },
        )

    def test_config_merge(self):
        user_conf_dict = {
            "builtin": {
                "spm": {
                    "spm12_standalone": {
                        "directory": "/usr/local/spm12_standalone",
                        "standalone": True,
                    },
                }
            }
        }
        site_conf_dict = {
            "builtin": {
                "spm": {
                    "spm12_standalone": {
                        "directory": "/i2bm/local/spm12_standalone",
                        "version": "12",
                        "standalone": True,
                    },
                    "spm8": {
                        "directory": "/i2bm/local/spm8",
                        "version": "8",
                        "standalone": False,
                    },
                },
                "fsl": {
                    "fsl5": {
                        "directory": "/i2bm/local/fsl",
                        "setup_script": "/i2bm/local/fsl/etc/fslconf/fsl.sh",
                    }
                },
            }
        }
        merged_conf_dict = {
            "builtin": {
                "database": "builtin",
                "persistent": True,
                "start_workers": default_engine_start_workers,
                "matlab": {},
                "spm": {
                    "spm12_standalone": {
                        "directory": "/usr/local/spm12_standalone",
                        "version": "12",
                        "standalone": True,
                    },
                    "spm8": {
                        "directory": "/i2bm/local/spm8",
                        "version": "8",
                        "standalone": False,
                    },
                },
                "fsl": {
                    "fsl5": {
                        "directory": "/i2bm/local/fsl",
                        "setup_script": "/i2bm/local/fsl/etc/fslconf/fsl.sh",
                    }
                },
            },
            "databases": {
                "builtin": expected_default_builtin_database,
            },
        }

        site_file = osp.join(self.tmp_dir, "site_conf.json")
        with open(site_file, "w") as f:
            json.dump(site_conf_dict, f)
        app_config = ApplicationConfiguration(
            "single_conf", site_file=site_file, user=user_conf_dict
        )
        app_config.site = site_conf_dict
        self.assertEqual(app_config.merged_config.asdict(), merged_conf_dict)
