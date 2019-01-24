# -*- coding: utf-8 -*-
#
# Copyright © keithleygui Project Contributors
# Licensed under the terms of the MIT License
# (see LICENSE.txt for details)

import pkg_resources as pkgr
from qtpy import QtGui, QtCore, QtWidgets, uic
from keithleygui.config.main import CONF


UI_PATH = pkgr.resource_filename(__name__, 'output.ui')
name = "Output"

class Measurement(QtWidgets.QWidget):

    def __init__(self, mainWindow):
        super(self.__class__, self).__init__()
        # load user interface layout from .ui file
        uic.loadUi(UI_PATH, self)
        self.mainWindow = mainWindow

    @QtCore.Slot()
    def _on_sweep_clicked(self):
        """ Start a transfer measurement with current settings."""

        self.mainWindow.statusBar.showMessage('    Recording output curve.')
        # get sweep settings
        params = {'Measurement': 'output'}
        params['VdStart'] = self.scienDSpinBoxVdStart.value()
        params['VdStop'] = self.scienDSpinBoxVdStop.value()
        params['VdStep'] = self.scienDSpinBoxVdStep.value()
        VgListString = self.lineEditVgList.text()
        VgStringList = VgListString.split(',')
        params['VgList'] = [float(x) for x in VgStringList]

    def mfunction(self, keithley, params):

        sweepData = keithley.outputMeasurement(
            params['smu_gate'], params['smu_drain'], params['VdStart'],
            params['VdStop'], params['VdStep'], params['VgList'],
            params['tInt'], params['delay'], params['pulsed']
        )

        return sweepData

    @QtCore.Slot()
    def _on_load_default(self):
        """Load default settings to interface."""

        # output curve settings
        self.scienDSpinBoxVdStart.setValue(CONF.get('Sweep', 'VdStart'))
        self.scienDSpinBoxVdStop.setValue(CONF.get('Sweep', 'VdStop'))
        self.scienDSpinBoxVdStep.setValue(CONF.get('Sweep', 'VdStep'))
        txt = str(CONF.get('Sweep', 'VgList')).strip('[]')
        self.lineEditVgList.setText(txt)
