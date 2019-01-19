#!/usr/bin/env python

#   Copyright (c) 2018 Kurt Jacobson
#      <kurtcjacobson@gmail.com>
#
#   This file is part of QtPyVCP.
#
#   QtPyVCP is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 2 of the License, or
#   (at your option) any later version.
#
#   QtPyVCP is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with QtPyVCP.  If not, see <http://www.gnu.org/licenses/>.

# Description:
# Tool table viewer/editor.

import os
import sys

import linuxcnc
from pprint import pprint

from qtpy.QtCore import Slot, Property, Qt, QModelIndex, QAbstractTableModel, QRegExp, QSortFilterProxyModel
from qtpy.QtGui import QValidator, QRegExpValidator, QStandardItemModel
from qtpy.QtWidgets import QTableView, QMessageBox, QAbstractItemView, QSpinBox, QDoubleSpinBox, \
    QLineEdit, QStyledItemDelegate

# Set up logging
from qtpyvcp.utilities import logger
from qtpyvcp.utilities.info import Info
from qtpyvcp.plugins import getPlugin

LOG = logger.getLogger(__name__)
INFO = Info()


class ItemDelegate(QStyledItemDelegate):

    def __init__(self):
        super(ItemDelegate, self).__init__()
        self._padding = ' ' * 2

    def displayText(self, value, locale):

        if type(value) == int:
            return str(value)
        elif type(value) == float:
            return "{0:.4f}".format(value)

        return "{}{}".format(self._padding, value)

    def createEditor(self, parent, option, index):
        if index.column() in (0, 1):

            editor = QSpinBox(parent)
            editor.setMinimum(0)
            editor.setMaximum(100)
            return editor

        elif index.column() in (2, 3):
            editor = QDoubleSpinBox(parent)
            editor.setDecimals(4)
            editor.setMinimum(0)
            return editor

        elif index.column() == 4:
            editor = QLineEdit(parent)
            margins = editor.textMargins()
            padding = editor.fontMetrics().width(self._padding) + 1
            margins.setLeft(margins.left() + padding)
            editor.setTextMargins(margins)
            return editor

        return None

    def setEditorData(self, item, index):
        value = index.model().data(index, Qt.EditRole)
        if index.column() in (0, 1, 2, 3):
            item.setValue(value)
        else:
            item.setText(value)

    def setModelData(self, item, model, index):
        if index.column() in (0, 1, 2, 3):
            item.interpretText()
            value = item.value()
        else:
            value = item.text()

        model.setData(index, value, Qt.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)


class ToolItem(object):
    def __init__(self, data, parent=None):
        self.parentItem = parent
        self.itemData = data
        self.childItems = []

    def appendChild(self, item):
        self.childItems.append(item)

    def child(self, row):
        if row < 0:
            row = 0
            return self.childItems[row]
        elif row > self.childCount():
            row = self.childCount()
            return self.childItems[row - 1]

    def childCount(self):
        return len(self.childItems)

    def columnCount(self):
        return len(self.itemData)

    def data(self, column):
        try:
            return self.itemData[column]
        except IndexError:
            return None

    def parent(self):
        return self.parentItem

    def row(self):
        if self.parentItem:
            return self.parentItem.childItems.index(self)
        return 0


class ToolModel(QStandardItemModel):
    def __init__(self, parent=None):
        super(ToolModel, self).__init__(parent)

        self.tool_table = getPlugin('tooltable')
        self.tool_list = list()

        self.table_header = [self.tool_table.COLUMN_LABELS[col]
                             for col in self.tool_table.columns]

        self.rootItem = ToolItem(self.table_header)

    def columnCount(self, parent=None):
        return len(self.table_header)

    def rowCount(self, parent=None):
        return len(self.tool_list)

    def flags(self, index):
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.table_header[section]

        return QAbstractTableModel.headerData(self, section, orientation, role)

    def index(self, row, column, parent):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        if not parent.isValid():
            parentItem = self.rootItem
        else:
            parentItem = parent.internalPointer()

        childItem = parentItem.child(row)
        if childItem:
            return self.createIndex(row, column, childItem)
        else:
            return QModelIndex()

    def parent(self, index):
        if not index.isValid():
            return QModelIndex()

        childItem = index.internalPointer()
        parentItem = childItem.parent()

        if parentItem == self.rootItem:
            return QModelIndex()

        return self.createIndex(parentItem.row(), 0, parentItem)

    def data(self, index, role=Qt.DisplayRole):
        return self._data(self.tool_list[index.row()], index.column(), role)

    def _data(self, item, column, role=Qt.DisplayRole):
        if role == Qt.EditRole:
            if column == 0:
                return int(item[0])
            elif column == 1:
                return int(item[1])
            elif column == 2:
                return float(item[2])
            elif column == 3:
                return float(item[3])
            elif column == 4:
                return float(item[4])
            elif column == 5:
                return str(item[5])

        elif role == Qt.DisplayRole:
            if column == 0:
                return item[0]
            elif column == 1:
                return item[1]
            elif column == 2:
                return item[2]
            elif column == 3:
                return item[3]
            elif column == 4:
                return item[4]
            elif column == 5:
                return item[5]

        elif role == Qt.TextAlignmentRole:
            if column == 0:
                return Qt.AlignVCenter | Qt.AlignCenter
            elif column == 1:
                return Qt.AlignVCenter | Qt.AlignCenter
            elif column == 2:
                return Qt.AlignVCenter | Qt.AlignRight
            elif column == 3:
                return Qt.AlignVCenter | Qt.AlignRight
            elif column == 4:
                return Qt.AlignVCenter | Qt.AlignRight
            elif column == 5:
                return Qt.AlignVCenter | Qt.AlignLeft
        else:
            return None

        """
        elif role == Qt.FontRole:

            font = QFont()
            font.setBold(True)
            return font
        """

    def setData(self, index, value, role):
        self.tool_list[index.row()][index.column()] = value
        return True

    def load_tool_table(self):

        del self.tool_list[:]

        for tool_data in self.tool_table.iterTools():
            self.tool_list.append(tool_data)

        self.rootItem.appendChild(ToolItem(self.tool_list, self.rootItem))

    def save_tool_table(self):

        tool_table = dict()
        tool_header = ['T', 'P', 'Z', 'D', 'R']
        for row_index in range(self.rowCount()):
            tool = dict()

            for col_index in range(self.columnCount()):
                item = self.tool_list[row_index][col_index]
                if item is not None and item != "":

                    tool[tool_header[col_index]] = item

            tool_table[row_index] = tool

        pprint(tool_table)

        getPlugin('tooltable').saveToolTable(tool_table)

    def newTool(self, row, dir):
        position = row + dir
        if position < 0:
            position = 0

        self.beginInsertRows(QModelIndex(), position, position)
        self.tool_list.insert(position, self.tool_table.newTool(tnum=position))
        self.endInsertRows()

    def removeTool(self, row):
        self.beginRemoveRows(QModelIndex(), row, row)
        self.tool_list.pop(row)
        self.endRemoveRows()

        return True

    def clearTable(self):
        self.beginResetModel()
        del self.tool_list[:]
        self.endResetModel()


class ProxyModel(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super(ProxyModel, self).__init__(parent)


class ToolTable(QTableView):

    def __init__(self, parent=None):
        super(ToolTable, self).__init__(parent)

        # This prevents doing unneeded initialization
        # when QtDesginer loads the plugin.
        if parent is None:
            return

        self.parent = parent

        self.cmd = linuxcnc.command()

        self.tool_model = ToolModel(self)

        delegate = ItemDelegate()

        self.setItemDelegate(delegate)

        self.horizontalHeader().setStretchLastSection(True)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.verticalHeader().hide()

        self.tool_table_file = INFO.getToolTableFile()

        self.tool_table_loaded = False
        self.loadToolTable()
        self.tool_table_loaded = True

        self.proxy_model = ProxyModel()
        self.proxy_model.setFilterKeyColumn(0)
        self.proxy_model.setSourceModel(self.tool_model)

        self.setModel(self.proxy_model)

        self.horizontalHeader().setSortIndicator(0, Qt.AscendingOrder)

    @Slot()
    def loadToolTable(self):
        if self.tool_table_loaded and not self.ask_dialog(
                "Do you want to re-load the tool table?\n All unsaved changes will be lost."):
            return

        fn = self.tool_table_file

        if fn is None:
            return

        if not os.path.exists(fn):
            LOG.warning("Tool table does not exist")
            return

        LOG.debug("Loading tool table: {0}".format(fn))

        self.tool_model.clearTable()
        self.tool_model.load_tool_table()

        self.selectRow(0)

    @Slot()
    def saveToolTable(self):
        if not self.ask_dialog("Do you wan't to save and load this tool table into the system?"):
            return

        self.tool_model.save_tool_table()
        self.cmd.load_tool_table()

    @Slot()
    def insertToolAbove(self):
        selected = self.selectedRow()
        self.tool_model.newTool(selected, -1)
        self.selectRow(selected)

    @Slot()
    def insertToolBelow(self):
        selected = self.selectedRow()
        self.tool_model.newTool(selected, +1)
        self.selectRow(selected)

    @Slot()
    def deleteSelectedTool(self):
        current_row = self.selectedRow()
        if current_row == -1:
            # no row selcted
            return
        current_tool = self.tool_model.tool_list[current_row][0]

        if not self.ask_dialog("Do you want to delete T{} ?".format(current_tool)):
            return

        self.tool_model.removeTool(current_row)

    @Slot()
    def removeAllTools(self, confirm=True):
        if confirm:
            if not self.ask_dialog("Do you want to delete the whole tool table?"):
                return

        for i in reversed(range(self.tool_model.rowCount())):
            self.tool_model.removeTool(i)

    def ask_dialog(self, message):
        box = QMessageBox.question(self.parent,
                                   'Are you sure?',
                                   message,
                                   QMessageBox.Yes,
                                   QMessageBox.No)
        if box == QMessageBox.Yes:
            return True
        else:
            return False

    def selectedRow(self):
        return self.selectionModel().currentIndex().row()
