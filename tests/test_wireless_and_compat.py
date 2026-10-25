#!/usr/bin/env python3
"""Regression tests for the Qt5/Qt6 compat shim (sparrowqt), the pyqtgraph
chart-emulation fallback (sparrowchart), and 6 GHz (WiFi 6E) support
(wirelessengine).

Run from anywhere inside a checkout:
    python3 tests/test_wireless_and_compat.py

Chart-emulation tests run when the pyqtgraph fallback backend is active and
are skipped otherwise (the real QtChart classes need a QApplication/display).
Exits non-zero on any failure.
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

fails = []
skips = 0

def check(name, cond, detail=''):
    global skips
    if cond is None:
        skips += 1
        print('[SKIP] ' + name)
        return
    if cond:
        print('[PASS] ' + name)
    else:
        fails.append(name)
        print('[FAIL] ' + name + (' -> ' + str(detail) if detail else ''))

# ---- Qt5/Qt6 compatibility shim ---------------------------------------------
import sparrowqt
print('   QT_VERSION =', sparrowqt.QT_VERSION)
check('sparrowqt shim imports cleanly', True)
for n in ('QAction', 'QRegularExpression', 'QSortFilterProxyModel', 'QDesktopWidget',
          'available_geometry', 'screen_center', 'Qt', 'QTimer', 'QSettings'):
    check('shim exports ' + n, hasattr(sparrowqt, n))

# ---- Chart backend / pyqtgraph emulation -------------------------------------
try:
    import sparrowchart
    print('   CHART_BACKEND =', sparrowchart.CHART_BACKEND)
    check('sparrowchart imports (a chart backend is required by the GUI)', True)
except ImportError as e:
    sparrowchart = None
    print('   (no chart backend installed: ' + str(e) + ')')
    check('sparrowchart imports (a chart backend is required by the GUI)', False, str(e))

if sparrowchart is not None and sparrowchart.CHART_BACKEND == 'qtchart':
    expected = 'PyQt5.QtChart' if sparrowqt.QT_VERSION == 5 else 'PyQt6.QtCharts'
    check('qtchart backend binding matches shim binding (QT_VERSION %d)' % sparrowqt.QT_VERSION,
          sparrowchart.SparrowChart.__module__ == expected,
          'SparrowChart came from %r' % sparrowchart.SparrowChart.__module__)

if sparrowchart is not None and sparrowchart.CHART_BACKEND == 'pyqtgraph':
    from sparrowqt import QPointF
    s = sparrowchart.SparrowLineSeries()
    s.append(1, 2); s.append((3, 4)); s.append(QPointF(5, 6))
    check('series append: (x,y), tuple, QPointF', [p.x() for p in s.pointsVector()] == [1, 3, 5])
    s.replace([QPointF(9, 10)])
    check('series replace(list)', s.count() == 1 and s.at(0).x() == 9)
    s.replace(0, 11, 12)
    check('series replace(index,x,y)', s.at(0).x() == 11 and s.at(0).y() == 12)
    s.replace(11, 12, 13, 14)
    check('series replace(oldx,oldy,newx,newy)', s.at(0).x() == 13 and s.at(0).y() == 14)
    s.remove(0)
    check('series remove(index)', s.count() == 0)
    s.append(1, 2); s.append(3, 4); s.remove(1, 2)
    check('series remove(x,y)', s.count() == 1 and s.at(0).x() == 3)
    s.clear()
    check('series clear()', s.count() == 0)
    ax = sparrowchart.SparrowValueAxis()
    ax.setMin(2412); ax.setMax(2484); ax.setTickCount(13); ax.setRange(5925, 7125)
    check('SparrowValueAxis range', ax.min() == 5925 and ax.max() == 7125 and ax.tickCount() == 13)
    ch_ = sparrowchart.SparrowChart()
    ser = sparrowchart.SparrowLineSeries()
    ch_.addSeries(ser); ch_.setTitle('2.4GHz')
    check('SparrowChart add/remove series', ch_.series() == [ser])
    ch_.removeSeries(ser)
    check('SparrowChart removeSeries', ch_.series() == [])
else:
    check('chart emulation API overloads (needs pyqtgraph backend)', None)
    check('SparrowValueAxis emulation (needs pyqtgraph backend)', None)
    check('SparrowChart series management (needs pyqtgraph backend)', None)

# ---- 6 GHz channel math (wirelessengine) --------------------------------------
from wirelessengine import WirelessEngine, channelToFreq, freqToChannel6GHz
for n, f in [(1, 5955), (5, 5975), (33, 6115), (37, 6135), (233, 7115), (2, 5935)]:
    got = WirelessEngine.getFrequencyForChannel(str(n), '6GHz')
    check('6GHz ch %d -> %d MHz' % (n, f), got == str(f), 'got %r' % got)
check('auto-resolve: ch233 -> 7115 (number only valid in 6GHz)', WirelessEngine.getFrequencyForChannel('233') == '7115')
check('auto-resolve: plain ch1 stays 2.4GHz', WirelessEngine.getFrequencyForChannel('1') == channelToFreq['1'])
check('explicit 6GHz miss (ch3) -> None, not 2.4GHz', WirelessEngine.getFrequencyForChannel('3', '6GHz') is None)
check('band: 6115 -> 6GHz', WirelessEngine.getBandForFrequency(6115) == '6GHz')
check('band: 2437 -> 2.4GHz', WirelessEngine.getBandForFrequency(2437) == '2.4GHz')
check('band: 5240 -> 5GHz', WirelessEngine.getBandForFrequency(5240) == '5GHz')
check('band: 4920 (4.9GHz public safety) -> 5GHz', WirelessEngine.getBandForFrequency(4920) == '5GHz')
check('gen: 6GHz + HE -> WiFi 6E', WirelessEngine.getWifiGeneration(6115, True) == 'WiFi 6E')
check('gen: 6GHz without HE -> WiFi 6E', WirelessEngine.getWifiGeneration(6115, False) == 'WiFi 6E')
check('gen: 5GHz + HE -> WiFi 6', WirelessEngine.getWifiGeneration(5240, True) == 'WiFi 6')
check('gen: 2.4GHz + HE -> WiFi 6 (11ax on 2.4GHz)', WirelessEngine.getWifiGeneration(2437, True) == 'WiFi 6')
check('reverse map 6115 -> ch33', freqToChannel6GHz.get(6115) == 33)

# ---- parseIWoutput on a synthetic 6 GHz BSS (no DS Parameter Set) -------------
sample6 = ('BSS 00:11:22:33:44:55(on wlan1)\n'
           '\tfreq: 6115\n'
           '\tsignal: -45.00 dBm\n'
           '\tSSID: Test6G\n'
           '\tHE PHY Capabilities: 0x0c010012\n')
nets = WirelessEngine.parseIWoutput(sample6)
check('parseIWoutput: one network parsed', len(nets) == 1, len(nets))
n = list(nets.values())[0]
check('parseIWoutput: SSID', n.ssid == 'Test6G', n.ssid)
check('parseIWoutput: frequency', n.frequency == 6115)
check('parseIWoutput: band derived from frequency', n.band == '6GHz', n.band)
check('parseIWoutput: 6GHz channel derived from frequency (ch33)', n.channel == 33, n.channel)
check('parseIWoutput: hasHE set from HE IE line', n.hasHE is True)
check('parseIWoutput: WiFi generation derived', n.wifiGeneration == 'WiFi 6E', n.wifiGeneration)

sample24 = ('BSS 00:11:22:33:44:66(on wlan1)\n'
            '\tfreq: 2437\n'
            '\tsignal: -60.00 dBm\n'
            '\tSSID: Test24\n'
            '\tDS Parameter set: channel 6\n')
n2 = list(WirelessEngine.parseIWoutput(sample24).values())[0]
check('2.4GHz: DS Param channel still honored', n2.channel == 6, n2.channel)
check('2.4GHz: band derived', n2.band == '2.4GHz')
check('2.4GHz: generation heuristic (WiFi 4 or blank)', n2.wifiGeneration in ('', 'WiFi 4'), n2.wifiGeneration)

print()
if fails:
    print('%d FAILURE(S):' % len(fails))
    for f in fails:
        print('  - ' + f)
    sys.exit(1)
print('ALL TESTS PASSED' + (' (%d skipped)' % skips if skips else ''))
