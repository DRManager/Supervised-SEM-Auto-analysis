# -*- coding: utf-8 -*-

from .core import ImageViewer
from ..plugins import Plugin
from PyQt5.QtWidgets import (QLabel, QLineEdit, QTableWidget, QTableWidgetItem, 
                             QMessageBox)
from PyQt5.QtCore import Qt, pyqtSlot
import pandas as pd
import numpy as np
import copy
import json
import matplotlib.pyplot as plt

class XSEMViewer(ImageViewer):
    """Subclass of ImageViewer. Front end image viewer.
    
    To implement data transfer, summary, and further data processing.
    Also involve detail information about image and plugin.
    """
    def __init__(self):
        super().__init__()
        try:
            with open('ViewerSetting.json', 'r') as f:
                setting_dic = json.load(f)
                self._chip_name_pos = setting_dic['chip_name']
                self._label_lvl = setting_dic['label_level']
        except:
            self._chip_name_pos = [1,3]
            self._label_lvl = 690
        self._enter_label_lvl.setText(str(self._label_lvl))
        
        self.setWindowTitle("Supervised SEM Auto-analysis")
        
        self._data_summary = pd.DataFrame()
        self._data_raw = {}
        self._current_special_data = None # To record data which doesn't have consistent format
        self._special_data_summary = {}
        self._current_data = None
        
        self.image_tag = QLineEdit()
        self.image_tag.setReadOnly(True)
        self.chip_tag = QLineEdit()
        self.chip_tag.setReadOnly(True)
        self.name_range = QLineEdit()
        self.name_range.setText(','.join(map(str, self._chip_name_pos)))
        self.name_range.editingFinished.connect(self._update_chip_name)  
        self.excel_name = QLineEdit()
        self.excel_name.setText('DataSummary')
        self.relevant_information = QLabel(' ')

        self.right_panel.addWidget(QLabel('Image Name:'), 0, 0)
        self.right_panel.addWidget(self.image_tag, 0, 1)
        self.right_panel.addWidget(QLabel('Name Position(eg. 1,3):'), 0, 2)
        self.right_panel.addWidget(self.name_range, 0, 3)
        self.right_panel.addWidget(QLabel('Save to Excel:'), 0, 4)
        self.right_panel.addWidget(self.excel_name, 0, 5)
        self.right_panel.addWidget(QLabel('Chip Name:'), 1, 0)
        self.right_panel.addWidget(self.chip_tag, 1, 1, 1, 1)
        self.right_panel.addWidget(self.relevant_information, 2, 0, 1, 3)
        
        table_section = Plugin(dock='bottom')
        table_section.name = 'Data Table'
        self._table_current = QTableWidget()
        self._table_summary = QTableWidget()
        table_section.layout.addWidget(self._table_current, 0, 0)
        table_section.layout.addWidget(self._table_summary, 0, 1)
        self += table_section
        self.setCorner(Qt.BottomRightCorner, Qt.RightDockWidgetArea)      
        self.assist_plugins.append(table_section)
    
    def _main_plugin_info(self, plugin):
        """Show plugin information. Connect signal from plugins
        """
        super()._main_plugin_info(plugin)    
        if hasattr(plugin, 'information'):
            self.relevant_information.setText(plugin.information)
        
        # Connect data transfer signal
        if hasattr(plugin, 'data_transfer_sig'):
            plugin.data_transfer_sig.connect(self.data_receive)
            
        # Connect special data transfer signal
        if hasattr(plugin, 'special_data_transfer_sig'):
            plugin.special_data_transfer_sig.connect(self.special_data_receive)
    
    @pyqtSlot()
    def _close_main_plugin(self):
        """Override by subclass to control reaction when main plugin is closed"""
        self._table_current.setRowCount(0)
        self._table_current.setColumnCount(0)
        self._current_data = None
    
    def _extra_img_info(self):
        """inherent by subclass"""   
        self.image_tag.setText(self._img_names[self._img_idx])
        self._update_chip_name()
    
    def _update_chip_name(self):
        name, pos = self.name_parser()
        if name is not None:
            self.chip_name = name
            self._chip_name_pos = pos
        else:
            self.chip_name = self.image_name
            self._chip_name_pos = None
        self.chip_tag.setText(self.chip_name)
        
    def name_parser(self):
        """
        Parse image name to obtain sample name if the format is more complicated
        """
        self.image_name = self.image_tag.text()
        pos = self.name_range.text()
        try:
            pos = list(map(int, pos.split(',')))
        except:
            return None, None
        if len(pos) == 2:
            start, end = pos
            if start >= 1 and start <= len(self.image_name) and end >= 1 and end <= len(self.image_name):   
                return self.image_name[start-1:end].strip(), pos
            else:
                return None, None
        else:
            return None, None
    
    def _refresh(self):
        """Reset current data if new image is loaded"""
        super()._refresh()
        self._current_data = None
    
    @pyqtSlot(list, list, dict)
    def data_receive(self, vert_header, hori_header, data):
        """Slot for data transfer signal from plugin
        """
        # Fill in the table first
        self._table_current.clear()
        measure_count = len(vert_header)
        point_count = len(hori_header)
        
        self._table_current.setRowCount(measure_count)
        self._table_current.setColumnCount(point_count+2)
        hori_labels = ['Avg', 'Std'] + hori_header
        self._table_current.setHorizontalHeaderLabels(hori_labels)
        self._table_current.setVerticalHeaderLabels(vert_header)        
        # if no data needs to be displayed
        if point_count == 0:
            return 
        # Fill in all the data
        for i in range(measure_count):
            measure = vert_header[i]
            for j in range(point_count):
                self._table_current.setItem(i, j+2, QTableWidgetItem('%.1f' %(data[measure][j])))            
            mean = np.nanmean(data[measure])
            std = np.nanstd(data[measure])
            self._table_current.setItem(i, 0, QTableWidgetItem('%.1f' %mean))
            self._table_current.setItem(i, 1, QTableWidgetItem('%.1f' %std))           
        self._table_current.resizeColumnsToContents()
        # copy the data into dataframe
        self._current_data = copy.deepcopy(data) # Need to make a new copy 
    
    @pyqtSlot(dict)
    def special_data_receive(self, data):
        """Slot to transfer special data from plugin
        """
        self._current_special_data = data
        
                                        
    def save_data(self):
        if self._current_data is None and self._current_special_data is None:
            return
        super().save_data()
        # Update raw data
        if self._current_data is not None:
            if self.chip_name in self._data_raw:
                for measurement in self._current_data:
                    if measurement not in self._data_raw[self.chip_name]:
                        self._data_raw[self.chip_name][measurement] = np.array([])
                    self._data_raw[self.chip_name][measurement] = \
                                  np.concatenate((self._data_raw[self.chip_name][measurement], 
                                                     self._current_data[measurement]))
            else:
                self._data_raw[self.chip_name] = copy.deepcopy(self._current_data)   # Create new copy                    
            # Update summary
            for measurement in self._current_data:
                raw_data = self._data_raw[self.chip_name][measurement]
                avg = np.nanmean(raw_data)
                std = np.nanstd(raw_data)
                if self.chip_name in self._data_summary.index and measurement in self._data_summary.columns.levels[0]:
                    self._data_summary.loc[self.chip_name][(measurement, 'avg')] = avg
                    self._data_summary.loc[self.chip_name][(measurement, 'std')] = std
                else:
                    chip_data = {self.chip_name:{(measurement, 'avg'): avg, (measurement, 'std'): std}}
                    df = pd.DataFrame.from_dict(chip_data, orient='index')
                    if self.chip_name not in self._data_summary.index:
                        self._data_summary = pd.concat([self._data_summary, df], axis=0)
                    else:
                        self._data_summary = pd.concat([self._data_summary, df], axis=1)
            self.update_summary()
        if self._current_special_data is not None:
            if self.chip_name in self._special_data_summary:
                for key in self._current_special_data.keys():
                    self._special_data_summary[self.chip_name][key] = \
                    np.concatenate((self._special_data_summary[self.chip_name][key], self._current_special_data[key]))
            else:
                self._special_data_summary[self.chip_name] = copy.deepcopy(self._current_special_data)
        self._saveExcel()
        
   
    def update_summary(self):
        # TODO: change the horizontal header to multilevel index if possible
        levels = self._data_summary.columns.levels
        labels = self._data_summary.columns.labels
        hori_header = [levels[0][i] + '(' + levels[1][j] + ')' for i, j in zip(labels[0], labels[1])]
        table = self._table_summary
        table.setRowCount(len(self._data_raw))
        table.setColumnCount(len(hori_header))
        table.setHorizontalHeaderLabels(hori_header)
        table.setVerticalHeaderLabels(self._data_summary.index)        
        for i in range(len(self._data_raw)):
            for j in range(len(hori_header)):
                table.setItem(i, j, QTableWidgetItem('%.1f' %self._data_summary.ix[i,j]))
        table.resizeColumnsToContents()
        
    def closeEvent(self, event):
        reply = QMessageBox.question(self, 'Message',
            "Do you want to exit the analysis?\n(Data summary will be automatically saved)", 
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()
            
#        self._data_summary.to_excel(self.excel_name.text() + '.xlsx')
#        reform_raw_data = {(outerKey, innerKey): pd.Series(series) for outerKey, innerDict in 
#                  self._data_raw.items() for innerKey, series in innerDict.items()}
#        raw_df = pd.DataFrame.from_dict(reform_raw_data)
#        raw_df.to_excel('raw_data.xlsx')
        
        self._saveSettings('ViewerSetting.json')        
        super().closeEvent(event)
    
    def _saveExcel(self):
        self._data_summary.to_excel(self.excel_name.text() + '.xlsx')
        reform_raw_data = {(outerKey, innerKey): pd.Series(series) for outerKey, innerDict in 
                  self._data_raw.items() for innerKey, series in innerDict.items()}
        raw_df = pd.DataFrame.from_dict(reform_raw_data)
        raw_df.to_excel('raw_data.xlsx')
        
        """ The following is under development for special data transfer
        """
        if len(self._special_data_summary.keys()) > 0:
            special_data = {(chip_name, column) : cd_list for chip_name, innerDict 
                            in self._special_data_summary.items() for 
                            column, cd_list in innerDict.items()}
            for i in self._special_data_summary.keys():
                f = plt.figure(figsize=(8, 12))
                plt.plot(self._special_data_summary[i]['Left'], self._special_data_summary[i]['Depth'], 'r.')
                plt.plot(self._special_data_summary[i]['Right'], self._special_data_summary[i]['Depth'], 'b.')
                plt.xlabel('X (nm)')
                plt.ylabel('Depth (nm)')
                plt.show()
                ff = plt.figure(figsize=(8,12))
                plt.plot(self._special_data_summary[i]['Bulk_CD'], self._special_data_summary[i]['Depth'], 'b.')
                plt.xlabel('CD (nm)')
                plt.ylabel('Depth (nm)')
                plt.show()
            pd.DataFrame(special_data).to_excel('SpecialData.xlsx')
        
    
    def _saveSettings(self, file_name):
        setting_dic = {'chip_name':self._chip_name_pos, 'label_level':self._label_lvl}
        with open(file_name, 'w') as f:
            json.dump(setting_dic, f)
            
    def help(self):
        helpstr = ("CD measurement of channels",
                   "Adjust the reference line (if needed) and click update")
        return '\n'.join(helpstr)