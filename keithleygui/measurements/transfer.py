# -*- coding: utf-8 -*-
#
# Copyright © keithleygui Project Contributors
# Licensed under the terms of the MIT License
# (see LICENSE.txt for details)

import pkg_resources as pkgr
from qtpy import QtCore, QtWidgets, uic
from keithleygui.config.main import CONF


UI_PATH = pkgr.resource_filename(__name__, 'transfer.ui')
name = "Transfer"

class Measurement(QtWidgets.QWidget):

    def __init__(self, mainWindow):
        super(self.__class__, self).__init__()
        # load user interface layout from .ui file
        uic.loadUi(UI_PATH, self)
        self.mainWindow = mainWindow

    @QtCore.Slot()
    def _on_sweep_clicked(self):
        """ Start a transfer measurement with current settings."""

        self.mainWindow.statusBar.showMessage('    Recording transfer curve.')
        # get sweep settings
        params = {'Measurement': 'transfer'}
        params['VgStart'] = self.scienDSpinBoxVgStart.value()
        params['VgStop'] = self.scienDSpinBoxVgStop.value()
        params['VgStep'] = self.scienDSpinBoxVgStep.value()
        VdListString = self.lineEditVdList.text()
        VdStringList = VdListString.split(',')
        params['VdList'] = [self._string_to_Vd(x) for x in VdStringList]

        return params

    def mfunction(self, keithley, params):

        sweepData = keithley.transferMeasurement(
            params['smu_gate'], params['smu_drain'], params['VgStart'],
            params['VgStop'], params['VgStep'], params['VdList'],
            params['tInt'], params['delay'], params['pulsed']
        )

        return sweepData

    @QtCore.Slot()
    def _on_load_default(self):
        """Load default settings to interface."""

        # transfer curve settings
        self.scienDSpinBoxVgStart.setValue(CONF.get('Sweep', 'VgStart'))
        self.scienDSpinBoxVgStop.setValue(CONF.get('Sweep', 'VgStop'))
        self.scienDSpinBoxVgStep.setValue(CONF.get('Sweep', 'VgStep'))
        txt = str(CONF.get('Sweep', 'VdList')).strip('[]')
        self.lineEditVdList.setText(txt)

    def _string_to_Vd(self, string):
        try:
            return float(string)
        except ValueError:
            if 'trailing' in string:
                return 'trailing'
            else:
                raise ValueError('Invalid drain voltage.')
