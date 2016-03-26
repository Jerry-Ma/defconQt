"""
The *listView* submodule
------------------------

The *listView* submodule provides a widget that can conveniently display Python
lists_.

.. _lists: https://docs.python.org/3/tutorial/introduction.html#lists
"""
from PyQt5.QtCore import pyqtSignal, QAbstractTableModel, QModelIndex, Qt
from PyQt5.QtWidgets import QAbstractItemView, QTreeView

__all__ = ["ListView"]


class AbstractListModel(QAbstractTableModel):

    def __init__(self, lst, parent=None):
        super().__init__(parent)
        self._setList(lst)
        self._headerTitles = []

    # implementation-specific methods

    def _data(self, row, column):
        raise NotImplementedError

    def _setData(self, row, column, value):
        raise NotImplementedError

    def _columnCount(self):
        raise NotImplementedError

    def _rowCount(self):
        raise NotImplementedError

    def _insertRows(self):
        raise NotImplementedError

    def _removeRows(self):
        raise NotImplementedError

    # other methods

    def list(self):
        return list(self._list)

    def _setList(self, lst):
        self._list = lst

    def headerTitles(self):
        return list(self._headerTitles)

    def setHeaderTitles(self, titles):
        assert len(titles) <= len(self._list)
        self._headerTitles = titles

    # builtins

    def data(self, index, role=Qt.DisplayRole):
        if index.isValid() and role in (Qt.DisplayRole, Qt.EditRole):
            row, column = index.row(), index.column()
            return self._data(row, column)
        return None

    def setData(self, index, value, role=Qt.EditRole):
        if index.isValid() and role == Qt.DisplayRole:
            row, column = index.row(), index.column()
            self._setData(row, column, value)
            self.dataChanged.emit(index, index, [role])
            return True
        return super().setData(index, value, role)

    def columnCount(self, parent=QModelIndex()):
        # flat table
        # http://stackoverflow.com/a/27333368/2037879
        if parent.isValid():
            return 0
        return self._columnCount()

    def rowCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        return self._rowCount()

    def insertRows(self, row, count, parent=QModelIndex()):
        if parent.isValid():
            return False
        self.beginInsertRows(parent, row, row+count-1)
        self._insertRows(row, count)
        self.endInsertRows()
        return True

    def removeRows(self, row, count, parent=QModelIndex()):
        if parent.isValid():
            return False
        self.beginRemoveRows(parent, row, row+count-1)
        self._removeRows(row, count)
        self.endRemoveRows()
        return True

    def dropMimeData(self, data, action, row, column, parent):
        if parent.isValid():
            return False
        # force column 0, we want to drag column onto the start of the
        # drop spot, otherwise it will be split between two new columns
        return super().dropMimeData(data, action, row, 0, parent)

    def flags(self, index):
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable \
            | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled \
            | Qt.ItemNeverHasChildren

    def supportedDropActions(self):
        return Qt.CopyAction | Qt.MoveAction

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            if section >= len(self._headerTitles):
                return None
            else:
                return self._headerTitles[section]
        return super().headerData(section, orientation, role)


class FlatListModel(AbstractListModel):

    def __init__(self, lst, columnCount=1, parent=None):
        super().__init__(lst, parent)
        self._columns = columnCount

    def _data(self, row, column):
        return self._list[row * self._columns + column]

    def _setData(self, row, column, value):
        self._list[row * self._columns + column] = value

    def _columnCount(self):
        return self._columns

    def _rowCount(self):
        return len(self._list) // self._columns

    def _insertRows(self, row, count):
        # XXX: test this!
        for index in range(row, row+count):
            for _ in self._columns:
                self._list.insert(index, 0)

    def _removeRows(self, row, count):
        # XXX: test this!
        for index in range(row, row+count):
            for _ in self._columns:
                del self._list[index * self._columns]


class OneTwoListModel(AbstractListModel):

    def _data(self, row, column):
        if self._is2D:
            return self._list[row][column]
        else:
            assert column == 1
            return self._list[row]

    def _setData(self, row, column, value):
        if self._is2D:
            self._list[row][column] = value
        else:
            assert column == 1
            self._list[row] = value

    def _columnCount(self):
        if self._is2D:
            return len(self._list[0])
        else:
            return 1

    def _rowCount(self):
        return len(self._list)

    def _insertRows(self, row, count):
        for index in range(row, row+count):
            elem = [0] * self._columnCount() if self._is2D else 0
            self._list.insert(index, elem)

    def _removeRows(self, row, count):
        for index in range(row, row+count):
            del self._list[index]

    def _setList(self, lst):
        self._list = lst
        if len(self._list) and isinstance(self._list[0], list):
            self._is2D = True
        else:
            self._is2D = False


class ListView(QTreeView):
    """
    A QTreeView_ widget that displays a Python list, whether 1D or 2D.

    Use *setAcceptDrops(True)* to allow reordering drag and drop.

    Emits *listChanged* when data changes inside the widget (when performing
    drag and drop, mostly).

    # TODO: listChanged emits multiple times...
    # preserve widgets on drag/drop and maybe clear on setList()
    # TODO: make it possible to up/down selected row w shortcut
    # e.g. Alt+Up/Down
    """
    listChanged = pyqtSignal()
    flatListModelClass = FlatListModel
    oneTwoListModelClass = OneTwoListModel

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setRootIsDecorated(False)
        self.header().setVisible(False)
        self._flatListInput = False
        self._triggers = None

    def setEditable(self, value):
        """
        Sets whether the list’s elements can be edited.
        """
        if value:
            if self._triggers is None:
                return
            # default actions vary depending on platform
            self.setEditTriggers(self._triggers)
        else:
            self._triggers = self.editTriggers()
            self.setEditTriggers(QAbstractItemView.NoEditTriggers)

    def headerTitles(self):
        """
        Returns this widget’s current header titles.
        """
        model = self.model()
        return model.headerTitles()

    def setHeaderTitles(self, titles):
        """
        Sets the header titles to *titles* (should be a list of strings).
        """
        model = self.model()
        model.setHeaderTitles(titles)
        self.header().setVisible(bool(titles))

    def list(self):
        """
        Returns the list as displayed by this widget, or None if no list was
        specified.
        """
        model = self.model()
        if model is None:
            return None
        return model.list()

    def setList(self, lst, **kwargs):
        """
        Sets the widget to display list *lst*.

        Additional keyword arguments may be provided and forwarded to the
        model.

        The default is None.

        # TODO: we should maybe clear indexWidgets here
        """
        # maybe clear previous signal
        currentModel = self.model()
        if currentModel is not None:
            currentModel.dataChanged.disconnect(self.listChanged)
        # now spawn the new model
        if self._flatListInput:
            modelClass = self.flatListModelClass
        else:
            modelClass = self.oneTwoListModelClass
        model = modelClass(lst, **kwargs)
        self.setModel(model)
        model.dataChanged.connect(self.listChanged)

    def flatListInput(self):
        """
        Returns whether this widget takes a flat list as input.
        """
        return self._flatListInput

    def setFlatListInput(self, value):
        """
        Sets whether :func:`setList` should consider its input list as flat,
        i.e. as a 2D structure.
        In that case, pass the *columnCount* argument to specify how many
        columns should be considered, e.g.:

        >>> from defconQt.control.listView import ListView
        >>> view = ListView()
        >>> view.setList(
        ...     [
        ...         [1, 2, 3],
        ...         [4, 5, 6]
        ...     ])

        is equivalent to:

        >>> view = ListView()
        >>> view.setFlatList(True)
        >>> view.setList([1, 2, 3, 4, 5, 6], columnCount=3)

        """
        self._flatListInput = value
