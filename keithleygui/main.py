# -*- coding: utf-8 -*-
#
# Copyright © keithleygui Project Contributors
# Licensed under the terms of the MIT License
# (see LICENSE.txt for details)


# system imports
from __future__ import division, print_function, absolute_import
import os
import os.path as osp
import sys
import re
import pkg_resources as pkgr
import importlib
import visa
from qtpy import QtCore, QtWidgets, uic
from matplotlib.figure import Figure
from keithley2600 import TransistorSweepData, IVSweepData
import matplotlib as mpl
import numpy as np
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

# local imports
from keithleygui.utils.led_indicator_widget import LedIndicator
from keithleygui.utils.scientific_spinbox import ScienDSpinBox
from keithleygui.connection_dialog import ConnectionDialog
from keithleygui.config.main import CONF

MAIN_UI_PATH = pkgr.resource_filename('keithleygui', 'main.ui')
MPL_STYLE_PATH = pkgr.resource_filename('keithleygui', 'figure_style.mplstyle')


class KeithleyGuiApp(QtWidgets.QMainWindow):
    """ Provides a GUI for transfer and output sweeps on the Keithley 2600."""
    def __init__(self, keithley):
        super(self.__class__, self).__init__()
        # load user interface layout from .ui file
        uic.loadUi(MAIN_UI_PATH, self)

        self.keithley = keithley
        # create new list of smu's instead of reference to old list
        self.smu_list = list(self.keithley.SMU_LIST)

        self._set_up_tabs()  # create Keithley settings tabs
        self._set_up_fig()  # create figure area

        # restore last position and size
        self.restore_geometry()

        # create connection dialog
        self.connectionDialog = ConnectionDialog(self, self.keithley)

        # create LED indicator
        self.led = LedIndicator(self)
        self.led.setDisabled(True)  # Make the led non clickable
        self.statusBar.addPermanentWidget(self.led)
        self.led.setChecked(False)

        # load measurements ui
        self.measurements = self.importMeasurements()
        self.loadMeasurements()

        # prepare GUI
        self.connect_ui_callbacks()  # connect to callbacks
        self._on_load_default()  # load default settings into GUI
        self.actionSaveSweepData.setEnabled(False)  # disable save menu

        # update when keithley is connected
        self._update_gui_connection()

        # connection update timer: check periodically if keithley is connected
        # and busy, act accordingly
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self._update_gui_connection)
        self.timer.start(10000)  # Call every 10 seconds

    @staticmethod
    def _string_to_vd(string):
        try:
            return float(string)
        except ValueError:
            if 'trailing' in string:
                return 'trailing'
            else:
                raise ValueError('Invalid drain voltage.')

    def closeEvent(self, event):
        self.exit_()

    def importMeasurements(self):
            pysearchre = re.compile('.py$', re.IGNORECASE)
            pluginfiles = filter(pysearchre.search,
                                 os.listdir(osp.join(osp.dirname(__file__),
                                                 'measurements')))
            form_module = lambda fp: '.' + osp.splitext(fp)[0]
            plugins = map(form_module, pluginfiles)
            # import parent module / namespace
            importlib.import_module('keithleygui.measurements')
            modules = []
            for plugin in plugins:
                if not plugin.startswith('__'):
                    modules.append(importlib.import_module(plugin, package="keithleygui.measurements"))

            return modules

    def loadMeasurements(self):
        for measurement in self.measurements:
            self.tabWidgetSweeps.addTab(measurement.Measurement(self), measurement.name)


# =============================================================================
# GUI setup
# =============================================================================

    def restore_geometry(self):
        x = CONF.get('Window', 'x')
        y = CONF.get('Window', 'y')
        w = CONF.get('Window', 'width')
        h = CONF.get('Window', 'height')

        self.setGeometry(x, y, w, h)

    def save_geometry(self):
        geo = self.geometry()
        CONF.set('Window', 'height', geo.height())
        CONF.set('Window', 'width', geo.width())
        CONF.set('Window', 'x', geo.x())
        CONF.set('Window', 'y', geo.y())

    def _set_up_fig(self):

        # set up figure itself
        with mpl.style.context(['default', MPL_STYLE_PATH]):
            self.fig = Figure(facecolor="None")
            self.fig.set_tight_layout('tight')
            self.ax = self.fig.add_subplot(111)

        self.ax.set_title('Sweep data', fontsize=10)
        self.ax.set_xlabel('Voltage [V]', fontsize=9)
        self.ax.set_ylabel('Current [A]', fontsize=9)

        # This needs to be done programmatically: it is impossible to specify
        # different label colors and tick colors in a .mplstyle file
        self.ax.tick_params(axis='both', which='major', direction='out', labelcolor='black',
                            color=[0.5, 0.5, 0.5, 1], labelsize=9)

        self.canvas = FigureCanvas(self.fig)
        self.canvas.setStyleSheet("background-color:transparent;")

        height = self.frameGeometry().height()
        self.canvas.setMinimumWidth(height)
        self.canvas.draw()

        self.gridLayout2.addWidget(self.canvas)

    def _set_up_tabs(self):
        """Create a settings tab for every SMU."""

        # get number of SMUs, create tab and grid tayout lists
        self.ntabs = len(self.smu_list)
        self.tabs = [None]*self.ntabs
        self.gridLayouts = [None]*self.ntabs

        self.labelsCbx = [None]*self.ntabs
        self.comboBoxes = [None]*self.ntabs

        self.labelsLimI = [None]*self.ntabs
        self.scienDSpinBoxsLimI = [None]*self.ntabs
        self.labelsUnitI = [None]*self.ntabs

        self.labelsLimV = [None]*self.ntabs
        self.scienDSpinBoxsLimV = [None]*self.ntabs
        self.labelsUnitV = [None]*self.ntabs

        # create a tab with combobox and scienDSpinBoxs for each SMU
        # the tab number i corresponds to the SMU number
        for i in range(0, self.ntabs):
            self.tabs[i] = QtWidgets.QWidget()
            self.tabs[i].setObjectName('tab_%s' % str(i))
            self.tabWidgetSettings.addTab(self.tabs[i], self.smu_list[i])

            self.gridLayouts[i] = QtWidgets.QGridLayout(self.tabs[i])
            self.gridLayouts[i].setObjectName('gridLayout_%s' % str(i))

            self.labelsCbx[i] = QtWidgets.QLabel(self.tabs[i])
            self.labelsCbx[i].setObjectName('labelsCbx_%s' % str(i))
            self.labelsCbx[i].setAlignment(QtCore.Qt.AlignRight)
            self.labelsCbx[i].setText('Sense type:')
            self.gridLayouts[i].addWidget(self.labelsCbx[i], 0, 0, 1, 1)

            self.comboBoxes[i] = QtWidgets.QComboBox(self.tabs[i])
            self.comboBoxes[i].setObjectName('comboBox_%s' % str(i))
            self.comboBoxes[i].setMinimumWidth(150)
            self.comboBoxes[i].setMaximumWidth(150)
            self.comboBoxes[i].addItems(['local (2-wire)', 'remote (4-wire)'])
            if CONF.get(self.smu_list[i], 'sense') is 'SENSE_LOCAL':
                self.comboBoxes[i].setCurrentIndex(0)
            elif CONF.get(self.smu_list[i], 'sense') is 'SENSE_REMOTE':
                self.comboBoxes[i].setCurrentIndex(1)
            self.gridLayouts[i].addWidget(self.comboBoxes[i], 0, 1, 1, 2)

            self.labelsLimI[i] = QtWidgets.QLabel(self.tabs[i])
            self.labelsLimI[i].setObjectName('labelLimI_%s' % str(i))
            self.labelsLimI[i].setAlignment(QtCore.Qt.AlignRight)
            self.labelsLimI[i].setText('Current limit:')
            self.gridLayouts[i].addWidget(self.labelsLimI[i], 1, 0, 1, 1)

            self.scienDSpinBoxsLimI[i] = ScienDSpinBox(self.tabs[i])
            self.scienDSpinBoxsLimI[i].setObjectName('scienDSpinBoxLimI_%s' % str(i))
            self.scienDSpinBoxsLimI[i].setMinimumWidth(90)
            self.scienDSpinBoxsLimI[i].setMaximumWidth(90)
            self.scienDSpinBoxsLimI[i].setAlignment(QtCore.Qt.AlignRight)
            self.scienDSpinBoxsLimI[i].setValue(CONF.get(self.smu_list[i], 'limiti'))
            self.scienDSpinBoxsLimI[i].setSuffix("A")
            self.gridLayouts[i].addWidget(self.scienDSpinBoxsLimI[i], 1, 1, 1, 1)

            self.labelsLimV[i] = QtWidgets.QLabel(self.tabs[i])
            self.labelsLimV[i].setObjectName('labelLimV_%s' % str(i))
            self.labelsLimV[i].setAlignment(QtCore.Qt.AlignRight)
            self.labelsLimV[i].setText('Voltage limit:')
            self.gridLayouts[i].addWidget(self.labelsLimV[i], 2, 0, 1, 1)

            self.scienDSpinBoxsLimV[i] = ScienDSpinBox(self.tabs[i])
            self.scienDSpinBoxsLimV[i].setObjectName('scienDSpinBoxLimV_%s' % str(i))
            self.scienDSpinBoxsLimV[i].setMinimumWidth(90)
            self.scienDSpinBoxsLimV[i].setMaximumWidth(90)
            self.scienDSpinBoxsLimV[i].setAlignment(QtCore.Qt.AlignRight)
            self.scienDSpinBoxsLimV[i].setValue(CONF.get(self.smu_list[i], 'limitv'))
            self.scienDSpinBoxsLimV[i].setSuffix("V")
            self.gridLayouts[i].addWidget(self.scienDSpinBoxsLimV[i], 2, 1, 1, 1)

    def connect_ui_callbacks(self):
        """Connect buttons and menues to callbacks."""
        #self.pushButtonTransfer.clicked.connect(self._on_sweep_clicked)
        #self.pushButtonOutput.clicked.connect(self._on_sweep_clicked)
        #self.pushButtonIV.clicked.connect(self._on_sweep_clicked)
        self.pushButtonRun.clicked.connect(self._on_sweep_clicked)
        self.pushButtonAbort.clicked.connect(self._on_abort_clicked)

        self.comboBoxGateSMU.currentIndexChanged.connect(self._on_smu_gate_changed)
        self.comboBoxDrainSMU.currentIndexChanged.connect(self._on_smu_drain_changed)

        self.actionSettings.triggered.connect(self.connectionDialog.open)
        self.actionConnect.triggered.connect(self._on_connect_clicked)
        self.actionDisconnect.triggered.connect(self._on_disconnect_clicked)
        self.action_Exit.triggered.connect(self.exit_)
        self.actionSaveSweepData.triggered.connect(self._on_save_clicked)
        self.actionLoad_data_from_file.triggered.connect(self._on_load_clicked)
        self.actionSaveDefaults.triggered.connect(self._on_save_default)
        self.actionLoadDefaults.triggered.connect(self._on_load_default)

# =============================================================================
# Measurement callbacks
# =============================================================================

    def apply_smu_settings(self):
        """
        Applies SMU settings to Keithley before a measurement.
        Warning: self.keithley.reset() will reset those settings.
        """
        for i in range(0, self.ntabs):

            smu = getattr(self.keithley, self.smu_list[i])

            if self.comboBoxes[i].currentIndex() == 0:
                smu.sense = smu.SENSE_LOCAL
            elif self.comboBoxes[i].currentIndex() == 1:
                smu.sense = smu.SENSE_REMOTE

            lim_i = self.scienDSpinBoxsLimI[i].value()
            smu.source.limiti = lim_i
            smu.trigger.source.limiti = lim_i

            lim_v = self.scienDSpinBoxsLimV[i].value()
            smu.source.limitv = lim_v
            smu.trigger.source.limitv = lim_v

    @QtCore.Slot()
    def _on_sweep_clicked(self):
        """ Start a transfer measurement with current settings."""

        if self.keithley.busy:
            msg = ('Keithley is currently used by antoher program. ' +
                   'Please try again later.')
            QtWidgets.QMessageBox.information(self, str('error'), msg)

            return

        self.apply_smu_settings()

        # receive the measurement-specific parameters
        tab = self.tabWidgetSweeps.currentIndex()
        tabWidget = self.tabWidgetSweeps.widget(tab)
        params = tabWidget._on_sweep_clicked()

        # get acquisition settings
        params['tInt'] = self.scienDSpinBoxInt.value()  # integration time
        params['delay'] = self.scienDSpinBoxSettling.value()  # stabilization

        smugate = self.comboBoxGateSMU.currentText()  # gate SMU
        params['smu_gate'] = getattr(self.keithley, smugate)
        smudrain = self.comboBoxDrainSMU.currentText()
        params['smu_drain'] = getattr(self.keithley, smudrain)  # drain SMU

        params['pulsed'] = bool(self.comboBoxSweepType.currentIndex())

        # check if integration time is valid, return otherwise
        freq = self.keithley.localnode.linefreq

        if params['tInt'] > 25.0/freq or params['tInt'] < 0.001/freq:
            msg = ('Integration time must be between 0.001 and 25 ' +
                   'power line cycles of 1/(%s Hz).' % freq)
            QtWidgets.QMessageBox.information(self, str('error'), msg)

            return

        # create measurement thread with params dictionary
        self.measureThread = MeasureThread(self.keithley, params, tabWidget.mfunction)
        self.measureThread.finishedSig.connect(self._on_measure_done)

        # run measurement
        self._gui_state_busy()
        self.measureThread.start()

    def _on_measure_done(self, sd):
        self.statusBar.showMessage('    Ready.')
        self._gui_state_idle()
        self.actionSaveSweepData.setEnabled(True)

        self.sweep_data = sd
        self.plot_new_data()
        if not self.keithley.abort_event.is_set():
            self._on_save_clicked()

    @QtCore.Slot()
    def _on_abort_clicked(self):
        """
        Aborts current measurement.
        """
        self.keithley.abort_event.set()

# =============================================================================
# Interface callbacks
# =============================================================================

    @QtCore.Slot(int)
    def _on_smu_gate_changed(self, int_smu):
        """ Triggered when the user selects a different gate SMU. """

        if int_smu == 0 and len(self.smu_list) < 3:
            self.comboBoxDrainSMU.setCurrentIndex(1)
        elif int_smu == 1 and len(self.smu_list) < 3:
            self.comboBoxDrainSMU.setCurrentIndex(0)

    @QtCore.Slot(int)
    def _on_smu_drain_changed(self, int_smu):
        """ Triggered when the user selects a different drain SMU. """

        if int_smu == 0 and len(self.smu_list) < 3:
            self.comboBoxGateSMU.setCurrentIndex(1)
        elif int_smu == 1 and len(self.smu_list) < 3:
            self.comboBoxGateSMU.setCurrentIndex(0)

    @QtCore.Slot()
    def _on_connect_clicked(self):
        self.keithley.connect()
        self._update_gui_connection()
        if not self.keithley.connected:
            msg = ('Keithley cannot be reached at %s. ' % self.keithley.visa_address
                   + 'Please check if address is correct and Keithley is ' +
                   'turned on.')
            QtWidgets.QMessageBox.information(self, str('error'), msg)

    @QtCore.Slot()
    def _on_disconnect_clicked(self):
        self.keithley.disconnect()
        self._update_gui_connection()
        self.statusBar.showMessage('    No Keithley connected.')

    @QtCore.Slot()
    def _on_save_clicked(self):
        """Show GUI to save current sweep data as text file."""
        prompt = 'Save as .txt file.'
        filename = 'untitled.txt'
        formats = 'Text file (*.txt)'
        filepath, _ = QtWidgets.QFileDialog.getSaveFileName(self, prompt, filename, formats)
        if len(filepath) < 4:
            return
        self.sweep_data.save(filepath)

    @QtCore.Slot()
    def _on_load_clicked(self):
        """Show GUI to load sweep data from file."""
        prompt = 'Please select a data file.'
        filepath, _ = QtWidgets.QFileDialog.getOpenFileName(self, prompt)
        if not osp.isfile(filepath):
            return

        self.sweep_data = TransistorSweepData()
        self.sweep_data.load(filepath)

        with mpl.style.context(['default', MPL_STYLE_PATH]):
            self.plot_new_data()
        self.actionSaveSweepData.setEnabled(True)

    @QtCore.Slot()
    def _on_save_default(self):
        """Saves current settings from GUI as defaults."""

        # save transfer settings
        CONF.set('Sweep', 'VgStart', self.scienDSpinBoxVgStart.value())
        CONF.set('Sweep', 'VgStop', self.scienDSpinBoxVgStop.value())
        CONF.set('Sweep', 'VgStep', self.scienDSpinBoxVgStep.value())

        vdlist_str = self.lineEditVdList.text().split(',')
        vd_list = [self._string_to_vd(x) for x in vdlist_str]
        CONF.set('Sweep', 'VdList', vd_list)

        # save output settings
        CONF.set('Sweep', 'VdStart', self.scienDSpinBoxVdStart.value())
        CONF.set('Sweep', 'VdStop', self.scienDSpinBoxVdStop.value())
        CONF.set('Sweep', 'VdStep', self.scienDSpinBoxVdStep.value())

        vglist_str = self.lineEditVgList.text().split(',')
        vg_list = [float(x) for x in vglist_str]
        CONF.set('Sweep', 'VgList', vg_list)

        # save iv settings
        CONF.set('Sweep', 'VStart', self.scienDSpinBoxVStart.value())
        CONF.set('Sweep', 'VStop', self.scienDSpinBoxVStop.value())
        CONF.set('Sweep', 'VStep', self.scienDSpinBoxVStep.value())

        CONF.set('Sweep', 'smu_sweep', self.comboBoxSweepSMU.currentText())

        # save general settings
        CONF.set('Sweep', 'tInt', self.scienDSpinBoxInt.value())
        CONF.set('Sweep', 'delay', self.scienDSpinBoxSettling.value())

        # get combo box status
        idx_pulsed = self.comboBoxSweepType.currentIndex()
        CONF.set('Sweep', 'pulsed', bool(idx_pulsed))

        CONF.set('Sweep', 'gate', self.comboBoxGateSMU.currentText())
        CONF.set('Sweep', 'drain', self.comboBoxDrainSMU.currentText())

        for i in range(0, self.ntabs):

            if self.comboBoxes[i].currentIndex() == 0:
                CONF.set(self.smu_list[i], 'sense', 'SENSE_LOCAL')
            elif self.comboBoxes[i].currentIndex() == 1:
                CONF.set(self.smu_list[i], 'sense', 'SENSE_REMOTE')

            CONF.set(self.smu_list[i], 'limiti', self.scienDSpinBoxsLimI[i].value())
            CONF.set(self.smu_list[i], 'limitv', self.scienDSpinBoxsLimV[i].value())

    @QtCore.Slot()
    def _on_load_default(self):
        """Load default settings to interface."""

        # Set SMU selection comboBox status
        cmb_list = list(self.smu_list)  # get list of all SMUs

        # receive the measurement-specific values
        for i in range(0, self.tabWidgetSweeps.count()):
            self.tabWidgetSweeps.widget(i)._on_load_default()

        # other
        self.scienDSpinBoxInt.setValue(CONF.get('Sweep', 'tInt'))
        self.scienDSpinBoxSettling.setValue(CONF.get('Sweep', 'delay'))

        # set PULSED comboBox index (0 if pulsed == False, 1 if pulsed == True)
        pulsed = CONF.get('Sweep', 'pulsed')
        self.comboBoxSweepType.setCurrentIndex(int(pulsed))

        # We have to comboBoxes. If there are less SMU's, extend list.
        while len(cmb_list) < 2:
            cmb_list.append('--')

        self.comboBoxGateSMU.clear()
        self.comboBoxDrainSMU.clear()
        self.comboBoxGateSMU.addItems(cmb_list)
        self.comboBoxDrainSMU.addItems(cmb_list)

        try:
            idx_gate = cmb_list.index(CONF.get('Sweep', 'gate'))
            idx_drain = cmb_list.index(CONF.get('Sweep', 'drain'))
            self.comboBoxGateSMU.setCurrentIndex(idx_gate)
            self.comboBoxDrainSMU.setCurrentIndex(idx_drain)
        except ValueError:
            self.comboBoxGateSMU.setCurrentIndex(0)
            self.comboBoxDrainSMU.setCurrentIndex(1)
            msg = 'Could not find last used SMUs in Keithley driver.'
            QtWidgets.QMessageBox.information(self, str('error'), msg)

        for i in range(0, self.ntabs):
            sense = CONF.get(self.smu_list[i], 'sense')
            if sense == 'SENSE_LOCAL':
                self.comboBoxes[i].setCurrentIndex(0)
            elif sense == 'SENSE_REMOTE':
                self.comboBoxes[i].setCurrentIndex(1)

            self.scienDSpinBoxsLimI[i].setValue(CONF.get(self.smu_list[i], 'limiti'))
            self.scienDSpinBoxsLimV[i].setValue(CONF.get(self.smu_list[i], 'limitv'))

    @QtCore.Slot()
    def exit_(self):
        self.keithley.disconnect()
        self.timer.stop()
        self.save_geometry()
        self.deleteLater()

# =============================================================================
# Interface states
# =============================================================================

    def _update_gui_connection(self):
        """Check if Keithley is connected and update GUI."""
        if self.keithley.connected and not self.keithley.busy:
            try:
                test = self.keithley.localnode.model
                self._gui_state_idle()
            except (visa.VisaIOError, visa.InvalidSession, OSError):
                self.keithley.disconnect()
                self._gui_state_disconnected()

        elif self.keithley.connected and self.keithley.busy:
            self._gui_state_busy()

        elif not self.keithley.connected:
            self._gui_state_disconnected()

    def _gui_state_busy(self):
        """Set GUI to state for running measurement."""


        self.pushButtonRun.setEnabled(False)
        self.pushButtonAbort.setEnabled(True)

        self.actionConnect.setEnabled(False)
        self.actionDisconnect.setEnabled(False)

        self.statusBar.showMessage('    Measuring.')
        self.led.setChecked(True)

    def _gui_state_idle(self):
        """Set GUI to state for IDLE Keithley."""


        self.pushButtonRun.setEnabled(True)
        self.pushButtonAbort.setEnabled(False)

        self.actionConnect.setEnabled(False)
        self.actionDisconnect.setEnabled(True)
        self.statusBar.showMessage('    Ready.')
        self.led.setChecked(True)

    def _gui_state_disconnected(self):
        """Set GUI to state for disconnected Keithley."""

        self.pushButtonRun.setEnabled(False)
        self.pushButtonAbort.setEnabled(False)

        self.actionConnect.setEnabled(True)
        self.actionDisconnect.setEnabled(False)
        self.statusBar.showMessage('    No Keithley connected.')
        self.led.setChecked(False)

# =============================================================================
# Plotting commands
# =============================================================================

    def plot_new_data(self):
        """
        Plots the sweep data curves.
        """
        self.ax.clear()  # clear current plot

        xdata = self.sweep_data.get_column(0)
        ydata = self.sweep_data.data[:, 1:]

        if self.sweep_data.sweep_type == 'transfer':
            self.ax.set_title('Transfer data')
            lines = self.ax.semilogy(xdata, np.abs(ydata))

        elif self.sweep_data.sweep_type == 'output':
            self.ax.set_title('Output data')
            lines = self.ax.semilogy(xdata, np.abs(ydata))

        elif self.sweep_data.sweep_type == 'iv':
            self.ax.set_title('IV sweep data')
            lines = self.ax.plot(xdata, ydata)

        self.ax.legend(lines, self.sweep_data.column_names[1:])
        self.ax.set_xlabel(str(self.sweep_data.titles[0]))
        self.ax.set_ylabel('Current [A]')
        self.ax.autoscale(axis='x', tight=True)
        self.canvas.draw()


class MeasureThread(QtCore.QThread):

    startedSig = QtCore.Signal()
    finishedSig = QtCore.Signal(object)

    def __init__(self, keithley, params, mfunction):
        QtCore.QThread.__init__(self)
        self.keithley = keithley
        self.params = params
        self.mfunction = mfunction

    def __del__(self):
        self.wait()

    def run(self):
        self.startedSig.emit()
        sweepData = self.mfunction(self.keithley, self.params)
        self.finishedSig.emit(sweepData)


def run():

    import sys
    import argparse
    from keithley2600 import Keithley2600

    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", help="increase output verbosity",
                        action="store_true")
    args = parser.parse_args()
    if args.verbose:
        import keithley2600
        keithley2600.log_to_screen()

    keithley_address = CONF.get('Connection', 'VISA_ADDRESS')
    visa_library = CONF.get('Connection', 'VISA_LIBRARY')
    keithley = Keithley2600(keithley_address, visa_library)

    app = QtWidgets.QApplication(sys.argv)
    app.aboutToQuit.connect(app.deleteLater)

    keithley_gui = KeithleyGuiApp(keithley)
    keithley_gui.show()
    app.exec_()


if __name__ == '__main__':
    run()
