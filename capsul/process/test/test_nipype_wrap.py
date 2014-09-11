#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# System import
import os
import unittest

# Capsul import
from capsul.process import get_process_instance
from capsul.process import NipypeProcess


class TestNipypeWrap(unittest.TestCase):
    """ Class to test the nipype interfaces wrapping.
    """

    def test_nipype_automatic_wrap(self):
        """ Method to test if the automatic nipype interfaces wrap work
        properly.
        """
        from nipype.interfaces.fsl import BET
        nipype_process = get_process_instance("nipype.interfaces.fsl.BET")
        self.assertTrue(isinstance(nipype_process, NipypeProcess))
        self.assertTrue(isinstance(nipype_process._nipype_interface, BET))

    def test_nipype_monkey_patching(self):
        """ Method to test the monkey patching used to work in user
        specified directories.
        """
        nipype_process = get_process_instance("nipype.interfaces.fsl.BET")
        nipype_process.in_file = os.path.abspath(__file__)
        self.assertEqual(
            nipype_process._nipype_interface._list_outputs()["out_file"],
            os.path.join(os.getcwd(), "test_nipype_wrap_brain.nii"))
        nipype_process.set_output_directory("/home")
        self.assertEqual(
            nipype_process._nipype_interface._list_outputs()["out_file"],
            os.path.join("/home", "test_nipype_wrap_brain.nii"))


def test():
    """ Function to execute unitest
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestNipypeWrap)
    runtime = unittest.TextTestRunner(verbosity=2).run(suite)
    return runtime.wasSuccessful()


if __name__ == "__main__":
    test()


    {'MANDATORY_PATH': '/usr/share/gconf/ubuntu.mandatory.path', 'XDG_GREETER_DATA_DIR': '/var/lib/lightdm-data/grigis', 'GNOME_DESKTOP_SESSION_ID': 'this-is-deprecated', 'LESSOPEN': '| /usr/bin/lesspipe %s', 'QT_IM_MODULE': 'ibus', 'LOGNAME': 'grigis', 'USER': 'grigis', 'PATH': '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games', 'XDG_VTNR': '7', 'GNOME_KEYRING_CONTROL': '/run/user/1000/keyring-yeEuKN', 'GTK_IM_MODULE': 'ibus', 'DISPLAY': ':0', 'SSH_AGENT_PID': '1825', 'LANG': 'fr_FR.UTF-8', 'TERM': 'xterm', 'SHELL': '/bin/bash', 'XDG_SESSION_PATH': '/org/freedesktop/DisplayManager/Session0', 'XAUTHORITY': '/home/grigis/.Xauthority', 'LANGUAGE': 'fr_FR', 'SESSION_MANAGER': 'local/slimer:@/tmp/.ICE-unix/1912,unix/slimer:/tmp/.ICE-unix/1912', 'SHLVL': '1', 'QT_QPA_PLATFORMTHEME': 'appmenu-qt5', 'JOB': 'dbus', 'TEXTDOMAIN': 'im-config', 'QT4_IM_MODULE': 'xim', 'CLUTTER_IM_MODULE': 'xim', 'WINDOWID': '27262987', 'SESSIONTYPE': 'gnome-session', 'XMODIFIERS': '@im=ibus', 'HOME': '/home/grigis', 'SELINUX_INIT': 'YES', 'COMPIZ_BIN_PATH': '/usr/bin/', 'XDG_RUNTIME_DIR': '/run/user/1000', 'INSTANCE': '', 'PYTHONPATH': ':/home/grigis/git/nsap:/home/grigis/git/nsap-src:/home/grigis/git/soma-workflow/python:/home/grigis/svn/capsul/trunk:/home/grigis/git/pypreprocess:/home/grigis/git/qmri:/home/grigis/git/genibabel', 'COMPIZ_CONFIG_PROFILE': 'ubuntu', 'SSH_AUTH_SOCK': '/run/user/1000/keyring-yeEuKN/ssh', 'VTE_VERSION': '3409', 'GDMSESSION': 'ubuntu', 'IM_CONFIG_PHASE': '1', 'TEXTDOMAINDIR': '/usr/share/locale/', 'GNOME_KEYRING_PID': '1756', 'XDG_SEAT_PATH': '/org/freedesktop/DisplayManager/Seat0', 'LESSCLOSE': '/usr/bin/lesspipe %s %s', 'XDG_CURRENT_DESKTOP': 'Unity', 'XDG_SESSION_ID': 'c2', 'DBUS_SESSION_BUS_ADDRESS': 'unix:abstract=/tmp/dbus-xma43zS1sF', '_': '/usr/bin/ipython', 'DEFAULTS_PATH': '/usr/share/gconf/ubuntu.default.path', 'SESSION': 'ubuntu', 'DESKTOP_SESSION': 'ubuntu', 'UPSTART_SESSION': 'unix:abstract=/com/ubuntu/upstart-session/1000/1758', 'XDG_CONFIG_DIRS': '/etc/xdg/xdg-ubuntu:/usr/share/upstart/xdg:/etc/xdg', 'GTK_MODULES': 'overlay-scrollbar:unity-gtk-module', 'UBUNTU_MENUPROXY': '1', 'GDM_LANG': 'fr_FR', 'XDG_DATA_DIRS': '/usr/share/ubuntu:/usr/share/gnome:/usr/local/share/:/usr/share/', 'PWD': '/home/grigis/svn/capsul/trunk/test', 'SSH_AGENT_LAUNCHER': 'upstart', 'COLORTERM': 'gnome-terminal', 'XDG_MENU_PREFIX': 'gnome-', 'LS_COLORS': 'rs=0:di=01;34:ln=01;36:mh=00:pi=40;33:so=01;35:do=01;35:bd=40;33;01:cd=40;33;01:or=40;31;01:su=37;41:sg=30;43:ca=30;41:tw=30;42:ow=34;42:st=37;44:ex=01;32:*.tar=01;31:*.tgz=01;31:*.arj=01;31:*.taz=01;31:*.lzh=01;31:*.lzma=01;31:*.tlz=01;31:*.txz=01;31:*.zip=01;31:*.z=01;31:*.Z=01;31:*.dz=01;31:*.gz=01;31:*.lz=01;31:*.xz=01;31:*.bz2=01;31:*.bz=01;31:*.tbz=01;31:*.tbz2=01;31:*.tz=01;31:*.deb=01;31:*.rpm=01;31:*.jar=01;31:*.war=01;31:*.ear=01;31:*.sar=01;31:*.rar=01;31:*.ace=01;31:*.zoo=01;31:*.cpio=01;31:*.7z=01;31:*.rz=01;31:*.jpg=01;35:*.jpeg=01;35:*.gif=01;35:*.bmp=01;35:*.pbm=01;35:*.pgm=01;35:*.ppm=01;35:*.tga=01;35:*.xbm=01;35:*.xpm=01;35:*.tif=01;35:*.tiff=01;35:*.png=01;35:*.svg=01;35:*.svgz=01;35:*.mng=01;35:*.pcx=01;35:*.mov=01;35:*.mpg=01;35:*.mpeg=01;35:*.m2v=01;35:*.mkv=01;35:*.webm=01;35:*.ogm=01;35:*.mp4=01;35:*.m4v=01;35:*.mp4v=01;35:*.vob=01;35:*.qt=01;35:*.nuv=01;35:*.wmv=01;35:*.asf=01;35:*.rm=01;35:*.rmvb=01;35:*.flc=01;35:*.avi=01;35:*.fli=01;35:*.flv=01;35:*.gl=01;35:*.dl=01;35:*.xcf=01;35:*.xwd=01;35:*.yuv=01;35:*.cgm=01;35:*.emf=01;35:*.axv=01;35:*.anx=01;35:*.ogv=01;35:*.ogx=01;35:*.aac=00;36:*.au=00;36:*.flac=00;36:*.mid=00;36:*.midi=00;36:*.mka=00;36:*.mp3=00;36:*.mpc=00;36:*.ogg=00;36:*.ra=00;36:*.wav=00;36:*.axa=00;36:*.oga=00;36:*.spx=00;36:*.xspf=00;36:', 'XDG_SEAT': 'seat0'}

