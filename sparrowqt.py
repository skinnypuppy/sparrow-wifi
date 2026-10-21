# SPDX-License-Identifier: MIT
"""
sparrowqt: dual Qt5/Qt6 compatibility layer for sparrow-wifi.

Strategy:
- Prefer PyQt6 when available (Gentoo, Arch, current Fedora); fall back to
  PyQt5 (Debian/Kali, RPi). This lets one codebase run everywhere during the
  Qt5 -> Qt6 transition without breaking any existing user.
- All enums use fully-qualified names (Qt.AlignmentFlag.AlignCenter) which
  are valid in PyQt5 >= 5.15 and PyQt6 alike.
- QtChart is optional: when unavailable (e.g. Gentoo has no PyQtChart /
  PyQt6-Charts package), the GUI falls back to pyqtgraph for the spectrum
  views. pyqtgraph is pure-python, installable via pip on any distro, and
  faster for real-time spectrum data anyway.

This module exposes a flat namespace that the rest of the codebase imports
from, so individual files never need to know which Qt is underneath.
"""

import sys

QT_VERSION = None

# --- Core widget imports -----------------------------------------------------
try:  # PyQt6 first
    from PyQt6.QtCore import (Qt, QTimer, QThread, QSettings, QLocale,
                              QTranslator, QEvent, QObject, QPoint, QPointF,
                              QRect, QRectF, QSize, QSizeF, QDateTime, QDate,
                              QTime, QUrl, QProcess, QSignalMapper,
                              QAbstractItemModel, QFileInfo, QStandardPaths,
                              QSysInfo, QLibraryInfo, QMetaObject, QDir)
    from PyQt6.QtGui import (QIcon, QPixmap, QColor, QBrush, QPen, QPalette, QRegion,
                             QFont, QFontMetrics, QCursor, QCloseEvent,
                             QKeySequence, QAction, QClipboard, QDesktopServices,
                             QValidator, QIntValidator, QDoubleValidator,
                             QPainter, QPdfWriter)
    from PyQt6.QtCore import QRegularExpression
    from PyQt6.QtWidgets import (QApplication, QMainWindow,
                                 QFrame, QLabel, QPushButton, QCheckBox,
                                 QComboBox, QLineEdit, QMenu, QMenuBar,
                                 QMessageBox, QFileDialog, QInputDialog,
                                 QTableWidget, QTableWidgetItem, QHeaderView,
                                 QAbstractItemView, QTabWidget, QWidget,
                                 QVBoxLayout, QHBoxLayout, QGridLayout,
                                 QSplitter, QTreeWidget, QTreeWidgetItem,
                                 QScrollArea, QGroupBox, QProgressBar,
                                 QStatusBar, QToolBar, QStyleFactory,
                                 QGraphicsView, QGraphicsScene, QGraphicsItem,
                                 QGraphicsSimpleTextItem, QGraphicsRectItem,
                                 QTextEdit, QPlainTextEdit, QSpinBox,
                                 QDoubleSpinBox, QListWidget, QListWidgetItem,
                                 QStackedWidget, QDockWidget, QSizePolicy,
                                 QSpacerItem, QRadioButton, QButtonGroup,
                                 QSlider, QDial, QScrollBar, QStyle,
                                 QStyleOptionViewItem, QStyledItemDelegate,
                                 QItemDelegate, QDialog, QDialogButtonBox)
    from PyQt6.QtCore import QSortFilterProxyModel
    from PyQt6.QtNetwork import (QUdpSocket, QTcpServer, QTcpSocket,
                                 QHostAddress, QNetworkInterface)
    QT_VERSION = 6
except ImportError:
    from PyQt5.QtCore import (Qt, QTimer, QThread, QSettings, QLocale,
                              QTranslator, QEvent, QObject, QPoint, QPointF,
                              QRect, QRectF, QSize, QSizeF, QDateTime, QDate,
                              QTime, QUrl, QProcess, QSignalMapper,
                              QAbstractItemModel, QFileInfo, QStandardPaths,
                              QSysInfo, QLibraryInfo, QMetaObject, QDir)
    from PyQt5.QtGui import (QIcon, QPixmap, QColor, QBrush, QPen, QPalette, QRegion,
                             QFont, QFontMetrics, QCursor, QCloseEvent,
                             QKeySequence, QAction, QClipboard,
                             QDesktopServices, QValidator, QIntValidator,
                             QDoubleValidator, QRegularExpression,
                             QPainter, QPdfWriter)
    from PyQt5.QtWidgets import (QApplication, QMainWindow, QDesktopWidget,
                                 QFrame, QLabel, QPushButton, QCheckBox,
                                 QComboBox, QLineEdit, QMenu, QMenuBar,
                                 QMessageBox, QFileDialog, QInputDialog,
                                 QTableWidget, QTableWidgetItem, QHeaderView,
                                 QAbstractItemView, QTabWidget, QWidget,
                                 QVBoxLayout, QHBoxLayout, QGridLayout,
                                 QSplitter, QTreeWidget, QTreeWidgetItem,
                                 QScrollArea, QGroupBox, QProgressBar,
                                 QStatusBar, QToolBar, QStyleFactory,
                                 QGraphicsView, QGraphicsScene, QGraphicsItem,
                                 QGraphicsSimpleTextItem, QGraphicsRectItem,
                                 QTextEdit, QPlainTextEdit, QSpinBox,
                                 QDoubleSpinBox, QListWidget, QListWidgetItem,
                                 QStackedWidget, QDockWidget, QSizePolicy,
                                 QSpacerItem, QRadioButton, QButtonGroup,
                                 QSlider, QDial, QScrollBar, QStyle,
                                 QStyleOptionViewItem, QStyledItemDelegate,
                                 QItemDelegate, QSortFilterProxyModel,
                                 QDialog, QDialogButtonBox)
    from PyQt5.QtNetwork import (QUdpSocket, QTcpServer, QTcpSocket,
                                 QHostAddress, QNetworkInterface)
    QT_VERSION = 5

# --- Module-object exports -----------------------------------------------------
# Some files do "from sparrowqt import QtCore" / "... QtWidgets"; bind the
# submodule objects themselves, not just their classes.
if QT_VERSION == 6:
    from PyQt6 import QtCore, QtGui, QtWidgets
else:
    from PyQt5 import QtCore, QtGui, QtWidgets

# --- Qt6 enum flattening -------------------------------------------------------
# PyQt5 exposes enum members directly on their classes (Qt.white, QMessageBox.Ok).
# PyQt6 scopes them (Qt.GlobalColor.white, QMessageBox.StandardButton.Ok).
# PyQt5 >= 5.15 also accepts the scoped form, but sparrow-wifi's codebase (and
# every plugin in the wild) uses the legacy flat form. Rather than churn
# hundreds of call sites, hoist the members of the enum classes sparrow-wifi
# uses back up to their legacy names when running under Qt6. This mirrors what
# pyqtgraph does internally for its own Qt6 compatibility layer.
if QT_VERSION == 6:
    def _hoist_enum_members(container, enum_class_names):
        for enum_name in enum_class_names:
            enum_cls = getattr(container, enum_name, None)
            if enum_cls is None:
                continue
            for member in dir(enum_cls):
                if member.startswith('_') or member in ('name', 'value'):
                    continue
                if not hasattr(container, member):
                    try:
                        setattr(container, member, getattr(enum_cls, member))
                    except (AttributeError, TypeError):
                        # Read-only wrapper: member stays scoped. Call sites
                        # that need it will surface in testing.
                        pass

    _hoist_enum_members(Qt, (
        'GlobalColor', 'AlignmentFlag', 'Orientation', 'SortOrder',
        'ItemDataRole', 'ContextMenuPolicy', 'CursorShape', 'MouseButton',
        'CheckState', 'ItemFlag', 'PenStyle', 'BrushStyle', 'WindowType',
        'WindowModality', 'TextInteractionFlag', 'Key', 'CaseSensitivity',
        'ConnectionType', 'TransformationMode', 'AspectRatioMode',
        'WidgetAttribute', 'ScreenOrientation', 'MatchFlag',
        'DockWidgetArea', 'FindChildOption', 'TextFormat', 'DropAction',
        'FillRule', 'KeyboardModifier', 'ImageConversionFlag'))
    _hoist_enum_members(QMessageBox, ('StandardButton',))
    _hoist_enum_members(QDialogButtonBox, ('StandardButton',))
    _hoist_enum_members(QHeaderView, ('ResizeMode',))
    _hoist_enum_members(QFileDialog, ('Option',))
    _hoist_enum_members(QLineEdit, ('EchoMode',))
    _hoist_enum_members(QAbstractItemView, ('SelectionMode', 'SelectionBehavior',
                                            'EditTrigger', 'ScrollMode', 'ScrollHint'))
    _hoist_enum_members(QGraphicsView, ('ViewportUpdateMode',))
    _hoist_enum_members(QFrame, ('Shape', 'Shadow'))
    _hoist_enum_members(QSizePolicy, ('Policy',))
    _hoist_enum_members(QPainter, ('RenderHint',))
    _hoist_enum_members(QRegion, ('RegionType',))

# --- Optional QtChart ---------------------------------------------------------
# PyQt5.QtChart lives in a separate PyQtChart package on most distros.
# PyQt6 puts charts in PyQt6.QtCharts (if the distro ships it).
# If neither is present, callers should use pyqtgraph instead.
try:
    if QT_VERSION == 6:
        from PyQt6.QtCharts import (QChart, QChartView, QLineSeries,
                                    QValueAxis, QBarSeries, QBarSet,
                                    QBarCategoryAxis, QSplineSeries)
    else:
        from PyQt5.QtChart import (QChart, QChartView, QLineSeries,
                                   QValueAxis, QBarSeries, QBarSet,
                                   QBarCategoryAxis, QSplineSeries)
    HAS_QTCHART = True
except ImportError:
    HAS_QTCHART = False

# --- Optional pyqtgraph fallback ----------------------------------------------
try:
    import pyqtgraph as pg
    HAS_PYQTGRAPH = True
except ImportError:
    HAS_PYQTGRAPH = False


def has_charting():
    """True if any spectrum-charting backend is available."""
    return HAS_QTCHART or HAS_PYQTGRAPH


def charting_backend():
    """'qtchart' or 'pyqtgraph' - or None if neither is importable."""
    if HAS_QTCHART:
        return 'qtchart'
    if HAS_PYQTGRAPH:
        return 'pyqtgraph'
    return None


# --- Qt5/Qt6 divergences ------------------------------------------------------

def available_geometry(widget_or_app=None):
    """Screen geometry in a version-agnostic way.

    QDesktopWidget was removed in Qt6; QScreen is the replacement.
    On Qt5 we use QDesktopWidget().availableGeometry() for parity
    with the original sparrow-wifi code.
    """
    if QT_VERSION >= 6:
        app = widget_or_app
        if app is None:
            app = QApplication.instance()
        if hasattr(app, 'screen'):
            return app.screen().availableGeometry()
        return QApplication.primaryScreen().availableGeometry()
    else:
        return QDesktopWidget().availableGeometry()


def screen_center(widget):
    """Move a widget to the screen center, version-agnostic."""
    if QT_VERSION >= 6:
        geo = widget.frameGeometry()
        center = widget.screen().availableGeometry().center()
        geo.moveCenter(center)
        widget.move(geo.topLeft())
    else:
        geo = widget.frameGeometry()
        center = QDesktopWidget().availableGeometry().center()
        geo.moveCenter(center)
        widget.move(geo.topLeft())


# --- 6GHz band definitions ----------------------------------------------------
# Channel numbers in 6GHz restart at 1, colliding with 2.4GHz channels 1-14.
# All lookups therefore need a band qualifier. 'auto' resolves by frequency
# range, which is how iw reports scan results anyway.

BAND_24GHZ = '2.4GHz'
BAND_5GHZ = '5GHz'
BAND_6GHZ = '6GHz'

# (channel, freq_MHz) for 6GHz - 20MHz channels numbered 1-233 stepping by 4,
# plus special guard-band ch2. F = 5955 + (N-1)*5 for the standard set.
SIX_GHZ_CHANNELS = {2: 5935}  # guard band channel
for _ch in range(1, 234, 4):
    SIX_GHZ_CHANNELS[_ch] = 5955 + ((_ch - 1) * 5)


def resolve_frequency(channel, band=None):
    """Resolve a channel number to frequency in MHz.

    Args:
        channel: integer channel number (1-233)
        band: '2.4GHz', '5GHz', '6GHz', or None for auto.

    Returns:
        Frequency in MHz (int), or None if unresolvable.

    When band is None, ambiguity exists for channels 1-14 (2.4 vs 6GHz).
    For those, 2.4GHz wins unless band='6GHz' is explicit.
    """
    ch = int(channel)
    if band == BAND_6GHZ:
        return SIX_GHZ_CHANNELS.get(ch)
    if band == BAND_5GHZ:
        from wirelessengine import channelToFreq
        return int(channelToFreq[str(ch)]) if str(ch) in channelToFreq else None
    if band == BAND_24GHZ or ch <= 14:
        from wirelessengine import channelToFreq
        if str(ch) in channelToFreq and int(channelToFreq[str(ch)]) < 5000:
            return int(channelToFreq[str(ch)])
    # fall through: maybe a 5GHz channel
    from wirelessengine import channelToFreq
    if str(ch) in channelToFreq:
        return int(channelToFreq[str(ch)])
    # or a 6GHz channel >= 15
    if ch >= 15:
        return SIX_GHZ_CHANNELS.get(ch)
    return None


def resolve_band(frequency_mhz):
    """Determine which band a frequency belongs to."""
    f = int(frequency_mhz)
    if 2412 <= f <= 2484:
        return BAND_24GHZ
    if 4915 <= f <= 4980:
        return BAND_24GHZ  # legacy 4.9GHz treated as 5GHz-adjacent
    if 5080 <= f <= 5865:
        return BAND_5GHZ
    if 5955 <= f <= 7115:
        return BAND_6GHZ
    return None


def wifi_generation(frequency_mhz, has_he=False):
    """Human-readable WiFi generation for a network.

    Args:
        frequency_mhz: center frequency
        has_he: True if HE (High Efficiency / 802.11ax) IEs were seen.
    """
    band = resolve_band(frequency_mhz)
    if has_he:
        if band == BAND_6GHZ:
            return 'WiFi 6E'
        return 'WiFi 6'
    if band == BAND_6GHZ:
        return 'WiFi 6E'
    # without HE we can't be sure of ax; report band
    if band == BAND_24GHZ:
        return '2.4GHz'
    if band == BAND_5GHZ:
        return '5GHz'
    return 'Unknown'
