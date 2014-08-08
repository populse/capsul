#-------------------------------------------------------------------------
class ListCreateWidget(object):

    class ListController(Controller):
        pass

    @staticmethod
    def is_valid_trait(trait):
        item_trait = trait.inner_traits[0]
        create_widget = ControllerWidget.find_create_control_from_trait(
            item_trait)
        return create_widget is not None

    @classmethod
    def create_widget(cls, parent, name, trait, value):

        item_trait = trait.inner_traits[0]
        # print '!ListCreateWidget!', name, 'List( %s )' % trait_ids(
        # item_trait )
        list_controller = cls.ListController()
        for i in xrange(len(value)):
            list_controller.add_trait(str(i), item_trait)
            trait = list_controller.trait(str(i))
            trait.order = i
            setattr(list_controller, str(i), value[i])
        result = ControllerCreateWidget.create_widget(
            parent, name, None, list_controller)
        control_instance = result[0]
        control_instance.controller_widget.connect_controller()
        control_instance.item_trait = item_trait
        control_instance.list_controller = list_controller
        control_instance.connected = False
        return result

    @staticmethod
    def update_controller(controller_widget, name, control_instance):
        items = [getattr(control_instance.list_controller, str(i))
                 for i in xrange(len(control_instance.list_controller.user_traits()))]
        # print '!update_controller!', name, len( items ), items
        setattr(controller_widget.controller, name, items)

    @classmethod
    def update_controller_widget(cls, controller_widget, name, control_instance, control_label):
        was_connected = control_instance.connected
        cls.disconnect_controller(
            controller_widget, name, control_instance, control_label)
        control_instance.controller_widget.disconnect_controller()
        items = getattr(controller_widget.controller, name)
        len_widget = len(control_instance.list_controller.user_traits())
        # print '!update_controller_widget!', name, len_widget, items
        user_traits_changed = False
        if len(items) < len_widget:
            for i in xrange(len(items), len_widget):
                control_instance.list_controller.remove_trait(str(i))
            user_traits_changed = True
        elif len(items) > len_widget:
            for i in xrange(len_widget, len(items)):
                control_instance.list_controller.add_trait(
                    str(i), control_instance.item_trait)
                trait = control_instance.list_controller.trait(str(i))
                trait.order = i
            user_traits_changed = True
        for i in xrange(len(items)):
            setattr(control_instance.list_controller, str(i), items[i])
        # print '!update_controller_widget! done', name
        control_instance.controller_widget.connect_controller()
        if user_traits_changed:
            control_instance.list_controller.user_traits_changed = True
        if was_connected:
            cls.connect_controller(
                controller_widget, name, control_instance, control_label)

    @classmethod
    def connect_controller(cls, controller_widget, name, control_instance, control_label):
        if not control_instance.connected:
            def list_controller_hook(obj, key, old, new):
                # print '!list_controller_hook!', ( obj, key, old, new )
                items = getattr(controller_widget.controller, name)
                items[int(key)] = new
            for n in control_instance.list_controller.user_traits():
                control_instance.list_controller.on_trait_change(
                    list_controller_hook, n)
            controller_hook = SomaPartial(
                cls.update_controller_widget, controller_widget, name, control_instance, control_label)
            controller_widget.controller.on_trait_change(
                controller_hook, name + '[]')
            control_instance._controller_connections = (
                list_controller_hook, controller_hook)
            control_instance.connected = True

    @staticmethod
    def disconnect_controller(controller_widget, name, control_instance, control_label):
        if control_instance.connected:
            list_controller_hook, controller_hook = control_instance._controller_connections
            controller_widget.controller.on_trait_change(
                controller_hook, name + '[]', remove=True)
            for n in control_instance.list_controller.user_traits():
                control_instance.list_controller.on_trait_change(
                    list_controller_hook, n, remove=True)
            del control_instance._controller_connections
            control_instance.connected = False

