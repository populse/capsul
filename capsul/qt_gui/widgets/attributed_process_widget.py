"""
Process or pipeline parameters view with attributes handling.

Classes
=======
:class:`AttributedProcessWidget`
--------------------------------
"""

import json

from soma.controller import Any, Controller, File, Path
from soma.qt_gui import qt_backend
from soma.qt_gui.controller import ControllerWidget
from soma.qt_gui.qt_backend import QtCore, QtGui
from soma.utils.weak_proxy import proxy_method


class AttributedProcessWidget(QtGui.QWidget):
    """Process interface with attributes completion handling"""

    def __init__(
        self,
        process,
        exec_meta=None,
        enable_attr_from_filename=False,
        enable_load_buttons=False,
        separate_outputs=True,
        user_data=None,
        user_level=0,
    ):
        """
        Parameters
        ----------
        process: Process instance
            if None, use exec_meta.executable instead
        exec_meta: executable metadata (ProcessMetadata) instance
            metadata with attributes to be displayed. If None, process.metadata
            is used instead - one of those two parameters should be defined.
        enable_attr_from_filename: bool (optional)
            if enabled, it will be possible to specify an input filename to
            build attributes from
        separate_outputs: bool
            if True, inputs and outputs (fields with output=True set) will
            be separated into two boxes.
        user_data: any type (optional)
            optional user data that can be accessed by individual control
            editors
        user_level: int
            the current user level: some fields may be marked with a non-zero
            user_level, and will only be visible if the ControllerWidget
            userl_evel is more than (or equal) the field level.
        """
        super().__init__()
        self.setLayout(QtGui.QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        if exec_meta is None:
            exec_meta = getattr(process, "metadata", None)
        self.exec_meta = exec_meta
        self._show_completion = False
        self.user_data = user_data
        self.separate_outputs = separate_outputs
        self._user_level = user_level

        if process is None:
            process = exec_meta.executable
        self.process = process

        splitter = QtGui.QSplitter(QtCore.Qt.Vertical)
        self.layout().addWidget(splitter)
        if exec_meta is not None:
            spl_up = QtGui.QWidget()
            spl_up.setLayout(QtGui.QVBoxLayout())
            splitter.addWidget(spl_up)
        else:
            spl_up = self

        filename_widget = None
        if enable_attr_from_filename and exec_meta is not None:
            c = Controller()
            c.add_field("attributes_from_input_filename", File, optional=True)
            filename_widget = ControllerWidget(c)  # , user_data=user_data)
            spl_up.layout().addWidget(filename_widget)
            self.input_filename_controller = c
            c.on_attribute_change.add(
                proxy_method(self, "on_input_filename_changed"),
                "attributes_from_input_filename",
            )
            filename_widget.setSizePolicy(
                QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed
            )

        # groupbox area to show attributes
        attrib_widget = QtGui.QGroupBox("Attributes:")
        attrib_widget.setFlat(True)
        attrib_widget.setAlignment(QtCore.Qt.AlignLeft)
        attrib_widget.setLayout(QtGui.QVBoxLayout())
        self.attrib_widget = attrib_widget
        spl_up.layout().addWidget(attrib_widget)
        attrib_widget.setSizePolicy(
            QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Preferred
        )

        hlay = QtGui.QHBoxLayout()
        spl_up.layout().addLayout(hlay)
        # CheckBox to completion rules or not
        self.checkbox_completion = QtGui.QCheckBox("Follow completion rules")
        self.checkbox_completion.setChecked(True)
        self.checkbox_completion.stateChanged.connect(self.on_use_completion_change)
        hlay.addWidget(self.checkbox_completion)

        # update button
        self.btn_update_compl = QtGui.QPushButton("Update Completion")
        self.btn_update_compl.setSizePolicy(
            QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed
        )
        self.btn_update_compl.clicked.connect(self.on_update_completion)
        hlay.addWidget(self.btn_update_compl)

        # Button Show/Hide completion
        self.btn_show_completion = QtGui.QCheckBox("Show completion")
        self.btn_show_completion.setSizePolicy(
            QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed
        )
        hlay.addWidget(self.btn_show_completion)
        self.btn_show_completion.stateChanged.connect(self.on_show_completion)

        CWidgetClass = ControllerWidget

        # groupbox area to show completion
        pwid = QtGui.QWidget()  # this one is just to add a bit of space
        pwid.setLayout(QtGui.QVBoxLayout())
        splitter.addWidget(pwid)
        if separate_outputs:
            param_widget = QtGui.QGroupBox("Inputs:")
        else:
            param_widget = QtGui.QGroupBox("Parameters:")
        param_widget.setFlat(True)
        param_widget.setAlignment(QtCore.Qt.AlignLeft)
        pwid.layout().addWidget(param_widget)
        param_widget.setLayout(QtGui.QVBoxLayout())
        param_widget.setSizePolicy(
            QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding
        )
        if separate_outputs:
            owid = QtGui.QWidget()  # this one is just to add a bit of space
            owid.setLayout(QtGui.QVBoxLayout())
            splitter.addWidget(owid)
            out_widget = QtGui.QGroupBox("Outputs:")
            out_widget.setFlat(True)
            out_widget.setAlignment(QtCore.Qt.AlignLeft)
            owid.layout().addWidget(out_widget)
            out_widget.setLayout(QtGui.QVBoxLayout())
            out_widget.setSizePolicy(
                QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding
            )

        # Create controller widget for process and object_attribute
        sel = None
        if separate_outputs:
            sel = False
        self.controller_widget = ControllerWidget(
            process,
            parent=param_widget,
            # user_data=user_data,
            user_level=user_level,
            output=sel,
        )
        if separate_outputs:
            self.outputs_cwidget = ControllerWidget(
                process,
                parent=out_widget,
                # user_data=user_data,
                user_level=user_level,
                output=True,
            )

        show_meta = False
        if exec_meta is not None:
            for field in exec_meta.fields():
                if field.is_list():
                    # iteration: assume fields exist
                    show_meta = True
                    break
                if len([f for f in getattr(exec_meta, field.name).fields()]) != 0:
                    show_meta = True
                    break

        if show_meta:
            self.controller_widget2 = CWidgetClass(
                exec_meta,
                parent=attrib_widget,
                # user_data=user_data,
                user_level=user_level,
            )
            # exec_meta.on_attribute_change.add(
            # proxy_method(self, 'on_attributes_changed'))
            # exec_meta.on_inner_value_change.add(
            # proxy_method(self, 'on_inner_value_changed'))
            ##for field in exec_meta.fields():
            ##getattr(exec_meta, field.name).on_attribute_change.add(
            ##proxy_method(self, 'on_attributes_changed'))
        else:
            self.controller_widget2 = CWidgetClass(
                Controller(),
                # user_data=user_data,
                user_level=user_level,
            )

        # Set controller of attributes and controller of process for each
        # corresponding area
        param_widget.layout().addWidget(self.controller_widget)
        if separate_outputs:
            out_widget.layout().addWidget(self.outputs_cwidget)
        attrib_widget.layout().addWidget(self.controller_widget2)

        if enable_load_buttons and show_meta:
            io_lay = QtGui.QHBoxLayout()
            self.layout().addLayout(io_lay)
            self.btn_load_json = QtGui.QPushButton("Load attributes")
            io_lay.addWidget(self.btn_load_json)
            self.btn_load_json.clicked.connect(self.on_btn_load_json)
            self.btn_save_json = QtGui.QPushButton("Save attributes")
            io_lay.addWidget(self.btn_save_json)
            self.btn_save_json.clicked.connect(self.on_btn_save_json)

        if not show_meta:
            if filename_widget:
                filename_widget.hide()
            attrib_widget.hide()
            self.checkbox_completion.hide()
            self.btn_show_completion.hide()
            if hasattr(self, "btn_load_json"):
                self.btn_load_json.hide()
                self.btn_save_json.hide()
            self.show_completion(True)  # hide file parts
        else:
            self.show_completion(False)  # hide file parts

        # if show_meta:
        # exec_meta.on_attribute_change.add(
        # self._completion_progress_changed, 'completion_progress')

    def __del__(self):
        exec_meta = self.exec_meta
        # if exec_meta is not None:
        # exec_meta.on_attribute_change.remove(
        # proxy_method(self, 'on_attributes_changed'))
        # exec_meta.on_inner_value_change.remove(
        # proxy_method(self, 'on_inner_value_changed'))
        ##for field in exec_meta.fields():
        ##getattr(exec_meta, field.name).on_attribute_change.remove(
        ##proxy_method(self, 'on_attributes_changed'))
        ##exec_meta.on_attribute_change.remove(
        ##self._completion_progress_changed, 'completion_progress')

    @property
    def user_level(self):
        return getattr(self, "_user_level", 0)

    @user_level.setter
    def user_level(self, value):
        self._user_level = value
        cw = getattr(self, "controller_widget", None)
        if cw:
            cw.user_level = value
        cw = getattr(self, "outputs_cwidget", None)
        if cw:
            cw.user_level = value
        cw = getattr(self, "controller_widget2", None)
        if cw:
            cw.user_level = value
        # re-hide file params if needed
        self.show_completion(self._show_completion)

    def on_attributes_changed(self):
        if self.exec_meta is not None:
            self.exec_meta.generate_paths(self.process)

    # def on_inner_value_changed(self, indices):
    # if self.exec_meta is not None:
    # self.exec_meta.generate_paths(self.process)

    def on_input_filename_changed(self, text):
        """
        Input file path to guess completion attributes changed: update
        attributes
        """
        exec_meta = self.exec_meta
        if exec_meta is not None:
            print("set attributes from path:", text)
            in_params = [
                p for p, ds in exec_meta.dataset_per_parameter.items() if ds == "input"
            ]
            if len(in_params) != 0:
                in_param = in_params[0]
                schema = getattr(exec_meta, exec_meta.schema_per_parameter[in_param])
            c_schema = exec_meta.execution_context.dataset["input"].schema
            try:
                metadata = c_schema.metadata(str(text))
                schema.import_dict(metadata)
                exec_meta.generate_paths(self.process)
            except ValueError as e:
                print(e)
                import traceback

                traceback.print_stack()
            except NotImplementedError:
                return

    def on_btn_load_json(self):
        """Load attributes from a json file"""
        exec_meta = self.exec_meta
        if exec_meta is None:
            print("No metadata for this process.")
            return
        # ask for a file name
        filename = qt_backend.getOpenFileName(
            self, "Select a .json attributes file", "", "JSON files (*.json)"
        )
        if filename is None:
            return
        print("load", filename)
        attributes = json.load(open(filename))
        print("loaded:", attributes)
        exec_meta.import_dict(attributes)

    def on_btn_save_json(self):
        """Save attributes in a json file"""
        exec_meta = self.exec_meta
        if exec_meta is None:
            print("No metadata for this process.")
            return
        # ask for a file name
        filename = qt_backend.getSaveFileName(
            self, "Select a .json attributes file", "", "JSON files (*.json)"
        )
        if filename is None or filename == "":
            return
        with open(filename, "w") as f:
            json.dump(exec_meta.asdict(), f)

    def set_use_completion(self):
        """
        Setup the completion doing its job
        """
        ret = QtGui.QMessageBox.critical(
            self,
            "Critical",
            "Going back to completion rules will reset all path files. Are you sure?",
            QtGui.QMessageBox.Ok,
            QtGui.QMessageBox.Cancel,
        )

        if ret == QtGui.QMessageBox.Ok:
            # reset attributes and fields of process
            process = self.process
            exec_meta = self.exec_meta
            if exec_meta is None:
                return
            # for field in exec_meta.fields():
            # getattr(exec_meta, field.name).on_attribute_change.add(
            # proxy_method(self, 'on_attributes_changed'))
            try:
                exec_meta.generate_paths(process)

                if (
                    hasattr(self, "input_filename_controller")
                    and self.input_filename_controller.attributes_from_input_filename
                    != ""
                ):
                    self.on_input_filename_changed(
                        self.input_filename_controller.attributes_from_input_filename
                    )
            except Exception as e:
                print(e)
                import traceback

                traceback.print_exc()
            self.attrib_widget.show()

        else:
            # reset it in a timer callback, otherwise the checkbox state is not
            # correctly recorded, and next time its state change will not
            # trigger the on_use_completion_change slot.
            QtCore.QTimer.singleShot(0, self._reset_completion_checkbox)

    def _reset_completion_checkbox(self):
        self.checkbox_completion.setChecked(False)

    def on_update_completion(self):
        process = self.process
        exec_meta = self.exec_meta
        if exec_meta is None:
            return
        exec_meta.generate_paths(process)
        self.controller_widget.update_fields()
        self.outputs_cwidget.update_fields()

    def on_use_completion_change(self, state):
        """
        Use completion checkbox callback
        """
        if state == QtCore.Qt.Checked:
            self.set_use_completion()
            self.btn_update_compl.show()
        else:
            self.attrib_widget.hide()
            self.btn_update_compl.hide()
            exec_meta = self.exec_meta
            if exec_meta is not None:
                # for field in exec_meta.fields():
                # getattr(exec_meta, field.name).on_attribute_change.remove(
                # proxy_method(self, 'on_attributes_changed'))
                self.btn_show_completion.setChecked(True)

    def show_completion(self, visible=None):
        """
        Show or hide completion (File, Directory, or Any parameters)

        Parameters
        ----------
        visible: bool (optional)
            show/hide. If None, switch the current visibility state.
        """

        if visible is None:
            visible = not self._show_completion
        self._show_completion = visible

        cwidgets = [self.controller_widget]
        if self.separate_outputs:
            cwidgets.append(self.outputs_cwidget)

        visibility = {True: [], False: []}
        for controller_widget in cwidgets:
            for field in controller_widget.controller.fields():
                if (
                    not field.is_path()
                    and field.type is not Any
                    and (
                        not field.is_list()
                        or len(field.subtypes()) == 0
                        or not isinstance(field.subtypes()[0], type)
                        or not issubclass(field.subtypes()[0], Path)
                    )
                ):
                    continue
                # group = field.metadata('group', None)
                # cwidget = controller_widget.groups[group]
                if field.metadata("forbid_completion", False):
                    # when completion is disabled, parameters are always
                    # visible
                    is_visible = True
                else:
                    hidden = field.metadata("hidden", False) or (
                        field.metadata("user_level") is not None
                        and field.metadata("user_level") > self.user_level
                    )
                    is_visible = visible and not hidden
                visibility[is_visible].append(field.name)

            controller_widget.set_visible(visibility[False], False)
            controller_widget.set_visible(visibility[True], True)

            # for group, group_widget in controller_widget._groups.items():
            # if [x for x in group_widget.hideable_widget.children()
            # if isinstance(x, QtGui.QWidget) and not x.isHidden()]:
            # group_widget.show()
            # else:
            # group_widget.hide()

    def on_show_completion(self, visible):
        """
        Toggle the visibility of paths parameters
        """
        self.show_completion(visible)

    def _completion_progress_changed(self, obj, name, old, new):
        completion_engine = getattr(self.attributed_process, "completion_engine", None)
        if completion_engine is not None:
            if not hasattr(self, "progressdialog"):
                self.progressdialog = QtGui.QWidget()
                self.layout().insertWidget(1, self.progressdialog)
                layout = QtGui.QHBoxLayout()
                self.progressdialog.setLayout(layout)
                layout.addWidget(QtGui.QLabel("Completion progress:"))
                self.progressbar = QtGui.QProgressBar()
                layout.addWidget(self.progressbar)
                self.progressbar.setRange(0, 100)
            value = int(
                round(
                    100
                    * completion_engine.completion_progress
                    / completion_engine.completion_progress_total
                )
            )
            self.progressbar.setValue(value)
            if value != 100:
                self.progressdialog.show()
                QtGui.qApp.processEvents()
            else:
                self.progressdialog.hide()
