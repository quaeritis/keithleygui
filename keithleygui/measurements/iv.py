# -*- coding: utf-8 -*-
#
# Copyright © keithleygui Project Contributors
# Licensed under the terms of the MIT License
# (see LICENSE.txt for details)

import pkg_resources as pkgr
from qtpy import QtCore, QtWidgets, uic
from keithley2600 import IVSweepData
from keithleygui.config.main import CONF
import numpy as np


UI_PATH = pkgr.resource_filename(__name__, 'iv.ui')
name = "IV"

class Measurement(QtWidgets.QWidget):

    def __init__(self, mainWindow):
        super(self.__class__, self).__init__()
        # load user interface layout from .ui file
        uic.loadUi(UI_PATH, self)
        self.mainWindow = mainWindow

    @QtCore.Slot()
    def _on_sweep_clicked(self):
        """ Start a transfer measurement with current settings."""

        self.mainWindow.statusBar.showMessage('    Recording IV curve.')
        # get sweep settings
        params = {'Measurement': 'iv'}
        params['VStart'] = self.scienDSpinBoxVStart.value()
        params['VStop'] = self.scienDSpinBoxVStop.value()
        params['VStep'] = self.scienDSpinBoxVStep.value()

        params['smu_sweep'] = self.comboBoxSweepSMU.currentText()
        
        return params

    def mfunction(self, keithley, params):

        step = np.sign(params['VStop'] - params['VStart']) * abs(params['VStep'])
        sweeplist = np.arange(params['VStart'], params['VStop'] + step, step)
        vSweep, iSweep = keithley.voltageSweepSingleSMU(
            getattr(keithley, params['smu_sweep']), sweeplist, params['tInt'],
            params['delay'], params['pulsed']
        )

        keithley.reset()

        sweepData = IVSweepData(vSweep, iSweep)
        return sweepData

    @QtCore.Slot()
    def _on_load_default(self):
        """Load default settings to interface."""

        # Set SMU selection comboBox status
        cmb_list = list(self.mainWindow.smu_list)  # get list of all SMUs

        # iv curve settings
        self.scienDSpinBoxVStart.setValue(CONF.get('Sweep', 'VStart'))
        self.scienDSpinBoxVStop.setValue(CONF.get('Sweep', 'VStop'))
        self.scienDSpinBoxVStep.setValue(CONF.get('Sweep', 'VStep'))
        try:
            idx_sweep = cmb_list.index(CONF.get('Sweep', 'smu_sweep'))
        except ValueError:
            idx_sweep = 0
            msg = 'Could not find last used SMUs in Keithley driver.'
            QtWidgets.QMessageBox.information(self, str('error'), msg)

        self.mainWindow.comboBoxGateSMU.setCurrentIndex(idx_sweep)
        self.comboBoxSweepSMU.clear()
        self.comboBoxSweepSMU.addItems(self.mainWindow.smu_list)
