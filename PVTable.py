from qtpy import QtCore, QtGui
from qtpy.QtGui import QPainter, QColor, QPen, QImage, QPixmap
from qtpy.QtWidgets import (QApplication, QWidget,
QFrame, QLabel, QHBoxLayout, QVBoxLayout, 
QLineEdit, QPushButton, QTableWidget, QSpinBox, 
QComboBox, QMessageBox, QFileDialog, QTableWidgetItem,
QSpacerItem, QSizePolicy)
from pydm import Display
from pydm.widgets import PyDMLabel, PyDMLineEdit, PyDMRelatedDisplayButton
from pydm.widgets.datetime import PyDMDateTimeLabel
from pydm.widgets.channel import PyDMChannel
from functools import partial
from datetime import datetime
import csv
import os
import string
import pandas as pd
import epics

## Test PV: SIOC:SYS0:MG01:HEARTBEAT
class MainWindow(Display):

    #def __init__(self, *args, **kwargs):        
     #   super(MainWindow, self).__init__(*args, **kwargs)
    def __init__(self, parent=None, macros=None, args=None):        
        super(MainWindow, self).__init__(args=args, parent=parent, macros=macros)
        self.main_layout = QVBoxLayout()
        self.setWindowTitle('PV Table')
        self.setMinimumSize(1155,517)
        self.setLayout(self.main_layout)
        
        self.spacer = QSpacerItem(100,10,QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)

        self.makeMainFrames()
        self.setupTitle()
        self.setupTable()
        self.setupHeader()
        self.setupFooter()
        self.setupEGET()
        self.editRows()

        if macros:
            self.macros = macros
            if 'PV' in self.macros.keys():
                try:
                    self.table.cellWidget(0, 0).setText(macros['PV'])
                    self.passPV(0)
                except:
                    print('Error with loading single PV')
            elif 'CSV' in self.macros.keys():
                try:
                    self.applyCSVFile(macros['CSV'])
                except:
                    print('Error: File not found')
        else:
            self.macros = {'PV': '',
                           'CSV': ''}

    def makeFrame(self, orientation):
        frame = QFrame()
        if orientation == 'H':
            layout = QHBoxLayout()
        elif orientation == 'V':
            layout = QVBoxLayout()
        frame.setLayout(layout)

        new_frame = (frame, layout)
        
        return new_frame

    def fillLayout(self, layout, widgets):
        for widget in widgets:
            try:
                layout.addWidget(widget)
            except:
                layout.addItem(widget)

    def makeMainFrames(self):
        self.title_frame = self.makeFrame('H')
        self.header_frame = self.makeFrame('H')
        self.eget_frame = self.makeFrame('H')
        self.table_frame = self.makeFrame('V')
        self.footer_frame = self.makeFrame('H')

        frames = [self.title_frame[0], self.header_frame[0], self.eget_frame[0], self.table_frame[0], self.footer_frame[0]]
        self.fillLayout(self.main_layout, frames)

    def setupTitle(self):
        self.title_frame[0].setStyleSheet('background-color: rgb(127,127,127); color: rgb(242,242,242)')
        img = QImage()
        img.load('SLAC_LogoSD_W.png')
        pixmap = QPixmap.fromImage(img)

        img = QLabel()
        img.setMaximumHeight(30)
        img.setPixmap(pixmap.scaled(img.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))

        title = QLabel('PV Table')
        title.setStyleSheet('QLabel {font-size: 24px; font-weight: bold}')
        self.title_frame[1].addWidget(img)
        self.title_frame[1].addItem(self.spacer)
        self.title_frame[1].addWidget(title)
        self.title_frame[1].addItem(self.spacer)
        self.title_frame[0].setMaximumHeight(50)

    def setupTable(self):
        self.table = QTableWidget()
        self.table.setRowCount(200)
        self.table.setColumnCount(10)

        col_widths = [200, 200, 80, 80, 100, 80, 160, 40, 60, 80]
        for i in range(self.table.columnCount()):
            self.table.setColumnWidth(i, col_widths[i])

        self.table_headers = ['PV', 'Description',
                            'Value', 'Alarm', 'Saved Value',
                            'Difference', 'Save Timestamp',
                            'Save', 'Restore', 'Set']
        self.table.setHorizontalHeaderLabels(self.table_headers)

        for i in range(self.table.rowCount()):
            self.setupRow(i)

        self.table_frame[1].addWidget(self.table)

    def setupRow(self, index):
        self.table.setCellWidget(index, 0, QLineEdit())
        self.table.cellWidget(index, 0).editingFinished.connect(partial(self.passPV, index))
        self.table.cellWidget(index, 0).textChanged.connect(partial(self.passPV, index))
        self.resetRow(index)

    def resetRow(self, index):
        for j in range(1, self.table.columnCount()):
            self.table.setCellWidget(index, j, PyDMLabel(' '))
            self.table.cellWidget(index, j).setText(None)
            self.table.cellWidget(index, j).setAlignment(QtCore.Qt.AlignCenter)
        self.table.cellWidget(index, 2).setProperty('precisionFromPV', True)
        self.table.removeCellWidget(index, 4)
        self.table.setItem(index, 4, QTableWidgetItem())
        self.table.setCellWidget(index, 7, QPushButton('Save'))
        self.table.setCellWidget(index, 8, QPushButton('Restore'))
        self.table.setCellWidget(index, 9, PyDMLineEdit())
        self.table.cellWidget(index, 7).clicked.connect(partial(self.savePV, index))
        self.table.cellWidget(index, 8).clicked.connect(partial(self.restorePV, index))

    def passPV(self, index):
        pv = self.table.cellWidget(index, 0).text()
        if '#' in pv:
            self.resetRow(index)
            strings = pv.split('#')
            colors = ['white', 'cyan', 'darkcyan', 'red', 'darkred', 'magenta', 'darkmagenta', 'green', 'darkgreen', 'yellow', 'gray', 'darkgray', 'lightgray', 'blue', 'darkblue', 'black']
            darkcolors = ['green', 'darkgreen', 'blue', 'darkblue', 'black', 'darkred', 'darkmagenta', 'red']
            for split in strings:
                if split in colors:
                    style = 'font-weight: bold; background-color: ' + split
                    for i in range(4):
                        self.table.cellWidget(index, i).setStyleSheet(style)
                    for i in range(4,5):
                        self.table.item(index, i).setBackground(QColor(split))
                    for i in range(5,7):
                        self.table.cellWidget(index, i).setStyleSheet(style)
                if split in darkcolors:
                    font = style + '; color: white;'
                    self.table.cellWidget(index, 0).setStyleSheet(font)
        elif pv == '':
            self.resetRow(index)
        else:
            for i in range(4):
                self.table.cellWidget(index, i).setStyleSheet(None)
            for i in range(4,5):
                self.table.item(index, i).setBackground(QColor('transparent'))
            for i in range(5,9):
                self.table.cellWidget(index, i).setStyleSheet(None)
            self.table.cellWidget(index, 1).channel = pv + '.DESC'
            self.table.cellWidget(index, 2).channel = pv
            self.table.cellWidget(index, 3).channel = pv + '.SEVR'
            self.chan1 = PyDMChannel(self.table.cellWidget(index, 2).channel, value_slot = partial(self.differenceCalc, foobar = index))
            self.chan1.connect()
            self.table.cellWidget(index, 9).channel = pv

    def savePV(self, index):
        ## Check that channel is connected
        if self.table.cellWidget(index, 2).channel:  
            value = self.table.cellWidget(index, 2).text()
            self.table.item(index, 4).setText(value)
            now = datetime.now()
            dt_string = now.strftime("%m/%d/%Y %H:%M:%S")
            self.table.cellWidget(index, 6).setText(dt_string)
            self.table.item(index, 4).setBackground(QtGui.QColor(159, 157, 154))

    def saveAll(self):
        for i in range(self.table.rowCount()):
            self.savePV(i)

    def restorePV(self, index):
        if self.table.item(index, 4).text():
            value = self.table.item(index, 4).text()
            pv = epics.PV(self.table.cellWidget(index, 0).text())
            pv.put(value)

    def restoreAll(self):
        pv_list = []
        value_list = []
        for i in range(self.table.rowCount()):
            if self.table.item(i, 4).text():
                try:
                    value = self.table.item(i, 4).text()
                    value = float(value)
                    value_list.append(value)
                    pv = self.table.cellWidget(i, 0).text()            
                    pv_list.append(pv)
                    epics.caput_many(pv_list, value_list)
                except:
                    a = 1

    def differenceCalc(self, new_val, foobar):
        live = self.table.cellWidget(foobar, 2).text()
        saved = self.table.item(foobar, 4).text()
        if saved:
            self.table.item(foobar, 4).setBackground(QtGui.QColor(159, 157, 154))
            if live != saved:
                self.table.item(foobar, 4).setBackground(QtGui.QColor(255, 157, 154))
            try:
                live = float(live)
                saved = float(saved)
                diff = live - saved
                self.table.cellWidget(foobar, 5).setText(str(diff))
            except:
                a = 1

    def setupHeader(self):
        self.header_frame[0].setMaximumHeight(40)

        row_lbl = QLabel('Number of Rows:')
        self.row_spin = QSpinBox()
        self.row_spin.setValue(10)
        self.row_spin.setKeyboardTracking(False)
        self.row_spin.setRange(1,200)
        self.row_spin.valueChanged.connect(self.editRows)

        fltr_lbl = QLabel('Filter:')
        self.fltr_edit = QLineEdit()
        self.fltr_edit.returnPressed.connect(self.doSearch)
        fltr_btn = QPushButton('Search')
        fltr_btn.clicked.connect(self.doSearch)
        fltr_rst_btn = QPushButton('Reset')
        fltr_rst_btn.clicked.connect(self.resetSearch)

        combo_lbl = QLabel('Menu:')
        self.combo_btn = QComboBox()
        combo_items = ['Export to CSV', 'Load Snapshot',
                       'Load with eget', 'Clear Saves (Confirm)', 
                       'Clear Table (Confirm)',]
        self.combo_btn.addItems(combo_items)
        self.combo_btn.activated.connect(self.comboChoice)

        header_widgets = [row_lbl, self.row_spin, self.spacer, fltr_lbl, self.fltr_edit, fltr_btn, fltr_rst_btn, self.spacer, combo_lbl, self.combo_btn] 

        self.fillLayout(self.header_frame[1], header_widgets)

    def editRows(self):
        new_num_rows = self.row_spin.value()
        total_num_rows = self.table.rowCount()

        for i in range(total_num_rows):
            self.table.hideRow(i)
        for i in range(new_num_rows):
            self.table.showRow(i)

        #if new_num_rows > 199:
         #   self.insert_btn.setEnabled(False)
        #else:
         #   self.insert_btn.setEnabled(True)

    def doSearch(self):
        search_text = self.fltr_edit.text()
        if search_text == '':
            self.editRows()
        for i in range(self.table.rowCount()):
            pv = self.table.cellWidget(i, 0).text()
            if search_text.upper() not in pv.upper():
                self.table.hideRow(i)

    def resetSearch(self):
        self.fltr_edit.setText('')
        self.editRows()

    def comboChoice(self):
        if self.combo_btn.currentIndex() == 0:
            self.exportToCSV()
        elif self.combo_btn.currentIndex() == 1:
            self.loadSnapshot()
        elif self.combo_btn.currentIndex() == 2:
            self.showEGETFrame()
        elif self.combo_btn.currentIndex() == 3:
            self.clearConfirm(self.clearSaves, 'Saves')
        elif self.combo_btn.currentIndex() == 4:
            self.clearConfirm(self.clearTable, 'Table')

    def exportToCSV(self):
        list_data = []
        shown_rows = int(self.row_spin.text())
        for i in range(shown_rows):
            list_row = []
            for j in range(self.table.columnCount()):
                if j in [0,1,2,3,5,6,9,10]:
                    cell_text = self.table.cellWidget(i,j).text()
                    if not cell_text:
                        cell_text = ' '
                elif j == 4:
                    cell_text = self.table.item(i,j).text()
                    if not cell_text:
                        cell_text = ' '
                elif j in [7,8]:
                    cell_text = ' '
                list_row.append(cell_text)
            list_data.append(list_row)
        df = pd.DataFrame(list_data, columns = self.table_headers)
        file_dialog = QFileDialog()
        file_dialog.setDefaultSuffix('.csv')
        try:        
            csv_file = file_dialog.getSaveFileName(self, 'Save File','',  'Comma-separated values (*.csv)')[0]
            df.to_csv(csv_file)
        except IOError:
            a = 1 

    def loadSnapshot(self):
        file_dialog = QFileDialog()
        try:
            csv_file = file_dialog.getOpenFileName(self, 'Open File', '', 'Comma-separated values (*.csv)')
            
            if csv_file != '':
                self.applyCSVFile(csv_file[0])

        except IOError:
            a = 1  

    def applyCSVFile(self, filename):
        df = pd.read_csv(filename)
        pvs = list(df.PV)
        self.clearTable()
        self.row_spin.setValue(len(pvs))

        for i in range(len(pvs)):
            self.table.cellWidget(i, 0).setText(str(df.PV.iloc[i]))
            self.table.item(i, 4).setText(str(df['Saved Value'].iloc[i]))
            self.table.cellWidget(i, 6).setText(str(df['Save Timestamp'].iloc[i]))

    def clearConfirm(self, fxn, items):
        msg = QMessageBox()
        msg.setWindowTitle('Confirm ' + str(items) + ' Clear')
        msg.setText('Are you sure you want to clear the ' + items.lower() + '?')
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.No)
        msg.buttonClicked.connect(partial(self.clearConfirmClicked, fxn = fxn))
        x = msg.exec_()           

    def clearConfirmClicked(self, i, fxn):
        button_clicked = i.text()
        if button_clicked == '&Yes':
            fxn()

    def clearTable(self):
        self.table.deleteLater()
        self.setupTable()
        self.editRows()

    def clearSaves(self):
        for i in range(self.table.rowCount()):
            if self.table.item(i, 4).text():
                self.table.item(i, 4).setText('')
                self.table.item(i, 4).setBackground(QtGui.QColor(159, 157, 154))
                self.table.cellWidget(i, 5).setText('')
                self.table.cellWidget(i, 6).setText('')

    def setupFooter(self):
        self.footer_frame[0].setMaximumHeight(40)
        #insert_lbl = QLabel('Insert Row Below:')
        #self.insert_spin = QSpinBox()
        #self.insert_spin.setRange(1,199)
        #self.insert_btn = QPushButton('Insert Row')
        #self.insert_btn.clicked.connect(self.insertRow)

        save_all_btn = QPushButton('Save All')
        save_all_btn.clicked.connect(self.saveAll)
        
        restore_all_btn = QPushButton('Restore All')
        restore_all_btn.setEnabled(False)
        #restore_all_btn.clicked.connect(self.restoreAll)

        helpfile = 'pv_table_help.ui'
        help_btn = PyDMRelatedDisplayButton('Help...', filename = helpfile)
        help_btn.setMaximumWidth(80)
        help_btn.setProperty('openInNewWindow', True)

        footer_widgets = [self.spacer, save_all_btn, restore_all_btn, help_btn]
        self.fillLayout(self.footer_frame[1], footer_widgets)

    #def insertRow(self):
     #   insert_row = self.insert_spin.value()
      #  num_rows = self.row_spin.value() + 1
       # self.table.insertRow(insert_row)
        #for i in range(insert_row, num_rows):
         #   self.setupRow(i)
        #self.row_spin.setValue(num_rows)

    def setupEGET(self):
        self.eget_edit = QLineEdit()
        self.eget_edit.setPlaceholderText('Enter eget command')
        self.eget_edit.returnPressed.connect(self.runEGET)

        self.eget_btn = QPushButton('Run')
        self.eget_btn.clicked.connect(self.runEGET)

        eget_widgets = [self.spacer, self.eget_edit, self.eget_btn]
        self.fillLayout(self.eget_frame[1], eget_widgets)

        self.eget_frame[0].setMaximumHeight(40)
        self.eget_frame[0].hide()

    def showEGETFrame(self):
        self.eget_frame[0].show()

    def runEGET(self):
        command = self.eget_edit.text()
        startswith = command.startswith('eget')
        if startswith:
            try:
                stream = os.popen(command)
                output = stream.read()
                split_lines = output.splitlines()
                new_lines = []
                for line in split_lines:
                    line = str(line)
                    line = ''.join(line.split())
                    if ':' in line:
                        new_lines.append(line)
                
                length = len(new_lines)
                self.row_spin.setValue(length)
                self.editRows()

                for i in range(len(new_lines)):
                    self.table.cellWidget(i, 0).setText(new_lines[i])
                    self.passPV(i)
            except:
                print('Error with eget command')
        else:
            print('Error: Not an eget command')
