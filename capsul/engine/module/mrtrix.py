# -*- coding: utf-8 -*-
from __future__ import absolute_import

import os
from capsul import engine
import six


def init_settings(capsul_engine):
    with capsul_engine.settings as settings:
        settings.ensure_module_fields(
            "mrtrix",
            [
                dict(
                    name="directory",
                    type="str",
                    description="Directory where mrtrix is installed",
                )
            ],
        )

        # init a single config
        config = settings.config("mrtrix", "global")
        if not config:
            settings.new_config(
                "mrtrix", "global", {capsul_engine.settings.config_id_field: "mrtrix"}
            )


def check_notably_invalid_config(conf):
    """
    Checks if the given module config is obviously invalid, for instance
    if a mandatory path is not filled

    Returns
    -------
    invalid: list
        list of invalid config keys
    """
    invalid = []
    for k in ("directory",):
        if getattr(conf, k, None) is None:
            invalid.append(k)
    return invalid


def activate_configurations():
    """
    Activate the mrtrix module (set env variables) from the global
    configurations, in order to use them via
    :mod:`capsul.in_context.mrtrix` functions
    """
    conf = engine.configurations.get("capsul.engine.module.mrtrix", {})
    mrtrix_dir = conf.get("directory")
    if mrtrix_dir:
        os.environ["MRTRIXPATH"] = six.ensure_str(mrtrix_dir)
    elif "MRTRIXPATH" in os.environ:
        del os.environ["MRTRIXPATH"]


def edition_widget(engine, environment, config_id="mrtrix"):
    """Edition GUI for mrtrix config - see
    :class:`~capsul.qt_gui.widgets.settings_editor.SettingsEditor`
    """
    from soma.qt_gui.controller_widget import ScrollControllerWidget
    from soma.controller import Controller
    import types
    import traits.api as traits

    def validate_config(widget):
        widget.update_controller()
        controller = widget.controller_widget.controller
        with widget.engine.settings as session:
            conf = session.config(config_id, widget.environment)
            values = {"config_id": config_id}
            for k in ["directory"]:
                value = getattr(controller, k)
                if value is traits.Undefined:
                    value = None
                values[k] = value
            if conf is None:
                session.new_config(config_id, widget.environment, values)
            else:
                for k, value in values.items():
                    if k == "config_id":
                        continue
                    setattr(conf, k, values[k])

    controller = Controller()

    controller.add_trait(
        "directory",
        traits.Directory(traits.Undefined, desc="Directory where mrtrix is installed"),
    )

    conf = engine.settings.select_configurations(environment, {"mrtrix": "any"})
    if conf:
        fconf = conf.get("capsul.engine.module.mrtrix", {})
        controller.directory = fconf.get("directory", traits.Undefined)

    widget = ScrollControllerWidget(controller, live=True)
    widget.engine = engine
    widget.environment = environment
    widget.accept = types.MethodType(validate_config, widget)

    return widget
