"""
This is a setup.py script generated by py2applet

Usage:
    python setup.py py2app
"""

from setuptools import setup
import os

APP = ['ts_conv/converter_gui.py']
cwd = os.getcwd()
DATA_FILES = [('i18n',[cwd+'/i18n/trainscanner_ja.qm'])]
#OPTIONS = {'argv_emulation': True}
OPTIONS = {
    'iconfile':'trainscanner.icns',
    'plist': {'CFBundleShortVersionString':'0.7.0',}
}

setup(
    app=APP,
    name="TS Converter",
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
