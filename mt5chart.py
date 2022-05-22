# coding: utf-8
import sys
from datetime import datetime as dt
import numpy as np
import pandas as pd

import MetaTrader5 as mt5
#import pyindicator as pind

from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
import pyqtgraph as pg 
import pyqtgraph.dockarea as pgda

# MetaTrader 5に接続する
if not mt5.initialize():
    print("initialize() failed")
    mt5.shutdown()
print("initialize() success")

symbol = "GOLD"
date_from = dt(2022,5,1,0)
date_to = dt(2022,5,22,0)
print(f"get data from {date_from} to {date_to}")

rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, date_from, date_to)
#print(rates)

rates_frame = pd.DataFrame(rates)
#print(rates_frame)
rates_frame['time']=pd.to_datetime(rates_frame['time'], unit='s')
#rates_frame = pd.Series(rates_frame, index=rates_frame['time'])
rates_frame.columns = rates_frame.columns.map(str.capitalize)
print(rates_frame)

class TimeAxisItem(pg.AxisItem):
    
    def __init__(self, *args, **kwargs):
        super(TimeAxisItem, self).__init__(*args, **kwargs)
    
    def tickStrings(self, values, scale, spacing):
        #print(values)
        return [dt.fromtimestamp(v).strftime('%m-%d %H:%M') for v in values]

"""
Candle Stick Chartを描画するクラス
"""
class TestCandle(pg.GraphicsObject):
    
    def __init__(self, df):
        super(TestCandle, self).__init__()
        self.data = np.c_[df.index.view(np.int64)//10**9, df.values]
        self.picture = QPicture()
        self.generatePicture(self.data)
    
    def generatePicture(self, data):
        # 陽線、陰線の色の指定
        clr_up, clr_down, clr_line = (0,128,0), (128,0,0), (128,128,128)
        """
        pg.plot(xdata, ydata, pen='r')
        pg.plot(xdata, ydata, pen=pg.mkPen('r'))
        pg.plot(xdata, ydata, pen=QPen(QColor(255, 0, 0)))
        塗りつぶしの設定は「setBrush」、線の設定は「setPen」で行い、「drawRect」を使うことで指定した範囲を塗りつぶすことができる
        """
        lp = pg.mkPen(clr_line)
        up = pg.mkPen(clr_up)
        dp = pg.mkPen(clr_down)
        brush_up = pg.mkBrush(clr_up) # mkBrushの引数はmkPenと一緒
        brush_dn = pg.mkBrush(clr_down)
        self.p = QPainter(self.picture) # この時点ではinitでのQPictureオブジェクトが入ってるだけ？
        self.p.setPen(lp)
        w = (data[-1][0]-data[-2][0]) / 3 # 最新とひとつ前の差分を3で割る？
        for (t, o, h, l, c) in data: # o(pen), h(igh), l(ow), c(lose)
            self.p.setPen(lp)
            if h!=l:
                self.p.drawLine(QPointF(t, l), QPointF(t, h)) # line
            """
            **pythonの3項演算子**
            条件式が真のときに評価される式 if 条件式 else 条件式が偽のときに評価される式
            """
            self.p.setPen(up if c>o else dp) # コメントアウトすればふちが有るかんじのローソクになる -> close > open : true -> up, false -> dp
            self.p.setBrush(brush_up if c>o else brush_dn) #                                     -> close > open : true -> brush_up, false -> brush_dn
            self.p.drawRect(QRectF(t-w, o, w*2, c-o)) # candle body -> 塗りつぶし実行 QRectF(left, top, width, height)
        self.p.end()
    
    def paint(self, p, *args):
        p.drawPicture(0, 0, self.picture) # 0, 0でのQPictureの呼び出し？
    
    def boundingRect(self):
        return QRectF(self.picture.boundingRect()) # QPictureのbounding rectangulerを返す関数らしい

"""
テスト用のチャートを作成するクラス
"""
class TestChart(QMainWindow):
    """
    DockAreaにPlotWidgetを表示する
    """
    def __init__(self, df):
        super(TestChart, self).__init__()
        
        self.dt = df.index.view(np.int64)//10**9 # //は整数除算(ex.5/2=2), **はべき乗10**9:=10^9
        self.close = df['Close'].values
        
        dockarea = pgda.DockArea()
        self.setCentralWidget(dockarea)
        
        setprop = lambda x: (
            x.showGrid(x=True, y=True, alpha=0.75),
            x.showAxis('right'),
            x.hideAxis('left'),
            x.setAutoVisible(y=True)
        )
        
        plt_chart = pg.PlotWidget(axisItems={'bottom': TimeAxisItem(orientation='bottom')})
        setprop(plt_chart)
        plt_chart.getPlotItem().getAxis('bottom').setHeight(0) # hideAxis('bottom')だと縦のグリッドが消えてしまう
        plt_chart.addItem(TestCandle(df[['Open', 'High', 'Low', 'Close']]))
        dockarea.addDock(pgda.Dock('chart', widget=plt_chart, size=(20,20)))
        self.plt_chart = plt_chart
        
        """
        # ma & hl bands
        plt_chart.addItem(pg.PlotDataItem(self.dt, df['ma'], pen='w'))
        plt_chart.addItem(pg.PlotDataItem(self.dt, df['Hband'], pen='r'))
        plt_chart.addItem(pg.PlotDataItem(self.dt, df['Lband'], pen='#08F'))
        
        # stc K
        plt_k = pg.PlotWidget(axisItems={'bottom': TimeAxisItem(orientation='bottom')})
        setprop(plt_k)
        plt_k.getPlotItem().getAxis('bottom').setHeight(0)
        plt_k.addItem(pg.PlotDataItem(self.dt, df['stochastic_K'], pen='#FF0'))
        plt_k.setXLink(self.plt_chart)
        dockarea.addDock(pgda.Dock('stochastic_K', widget=plt_k))
        
        # macd
        plt_macd = pg.PlotWidget(axisItems={'bottom': TimeAxisItem(orientation='bottom')})
        setprop(plt_macd)
        plt_macd.addItem(pg.BarGraphItem(x=self.dt, height=df['macd_hist'], width=self.dt[-1]-self.dt[-2], brush='#080'))
        plt_macd.addItem(pg.PlotDataItem(self.dt, df['macd'], pen='w'))
        plt_macd.addItem(pg.PlotDataItem(self.dt, df['macd_sig'], pen='r'))
        plt_macd.setXLink(self.plt_chart)
        dockarea.addDock(pgda.Dock('macd', widget=plt_macd))
        """

        # region
        region = pg.LinearRegionItem() # http://www.pyqtgraph.org/documentation/graphicsItems/linearregionitem.html
        plt_region = pg.PlotWidget(axisItems={'bottom': TimeAxisItem(orientation='bottom')})
        plt_region.showAxis('right')
        plt_region.hideAxis('left')
        plt_region.addItem(region, ignoreBounds=True)
        plt_region.plot(self.dt, self.close, pen=(96,96,96))
        dockarea.addDock(pgda.Dock('region', size=(1,1), widget=plt_region))
        self.region = region

        self.plt_chart.sigRangeChanged.connect(self.update_region)
        self.region.sigRegionChanged.connect(self.update_region_change)
        self.region.setRegion([self.dt[-100], self.dt[-1]+(self.dt[-1]-self.dt[-2])*10])

    def update_region_change(self, region):
        region.setZValue(10)
        minx, maxx = region.getRegion()
        self.plt_chart.setXRange(minx, maxx, padding=0)
        idx = (self.dt>=minx) & (self.dt<=maxx)
        if idx.sum()<2:
            return
        miny = self.close[idx].min()
        maxy = self.close[idx].max()
        self.plt_chart.setYRange(miny, maxy)
        # plt_chart.setAutoVisible(y=True) しても縦のスケールが
        # 自動調整されないのでとりあえずここでsetYRangeした  よくわからない
    
    def update_region(self, window, viewRange):
        self.region.setRegion(viewRange[0])


class TestMainWindow(QMainWindow):
    """
    QMainWindowにチャートを表示する
    """
    def __init__(self):
        super(TestMainWindow, self).__init__()
        self.setWindowTitle('test chart !!!')
        self.init_ui()
        #self.chart = TestChart(self.create_df())
        df_reset=rates_frame.set_index('Time')
        self.chart = TestChart(df_reset)
        #print(df_reset)
        #print(type(df_reset))
        self.setCentralWidget(self.chart)
        self.show()
    
    def init_ui(self):
        self.setGeometry(200, 200, 800, 600)
        
        # 特に何もしないけどメニューバーとツールバーとステータスバーをつくる
        menubar = self.menuBar()
        menu = menubar.addMenu('test_menu')
        menu.addAction('menu_item1')
        menu.addAction('menu_item2')
        menu.triggered[QAction].connect(self.menubar_action)
        
        toolbar = self.addToolBar('tool')
        toolbar.addAction('&Exit', QApplication.instance().quit)
        toolbar.addAction('A', self.toolbar_action)
        toolbar.addAction('B', self.toolbar_action)
        
        satusbar = self.statusBar()
        satusbar.showMessage('statusbar')
    
    def menubar_action(self, a):
        txt = a.text()
        print('menubar_action', txt)
        self.statusBar().showMessage(txt)
    
    def toolbar_action(self):
        txt = self.sender().text()
        print('toolbar_action', txt)
        self.statusBar().showMessage(txt)
    
    def create_df(self):
        # 適当な四本値をつくる
        n = 100000
        index = pd.date_range(start='20170101', periods=n, freq='T') # Time Indexの作成 : 2017/01/01~ 100,000期間分 毎分(T=min)
        s = pd.Series(np.random.randn(n).cumsum(), index=index) # pandasのseriiesオブジェクト : サイズnの一様分布の乱数, .cumcum:=配列要素の累積和, indexにTime indexを代入
        s += abs(s.min())*2 # 配列全体の下駄上げ
        df = s.resample('H').ohlc() # pandasでohlcを抜き出す方法らしい
        print(df)
        print(type(df))
        """
        >>> df
                                open        high         low       close
        2017-01-01 00:00:00    0.360185    6.339496   -2.910862   -1.918326
        2017-01-01 01:00:00   -0.796221   15.663193   -0.796221   15.245592
        2017-01-01 02:00:00   14.163447   18.555766   10.679940   15.517082
        2017-01-01 03:00:00   15.293488   17.786829    5.677697    7.534678
        2017-01-01 04:00:00    8.771571    8.771571   -4.486176    1.586693
        ...                         ...         ...         ...         ...
        2017-03-11 06:00:00  282.884043  289.235124  282.086737  286.869939
        2017-03-11 07:00:00  286.346827  287.596127  278.132718  287.454956
        2017-03-11 08:00:00  286.733843  298.351307  285.517687  292.140418
        2017-03-11 09:00:00  290.796996  296.200800  290.240405  290.875974
        2017-03-11 10:00:00  290.616523  295.269098  288.670178  293.210765

        [1667 rows x 4 columns]
        <class 'pandas.core.frame.DataFrame'>

                            Time     Open     High      Low    Close  Tick_volume  Spread  Real_volume
        0    2021-09-30 15:00:00  1725.97  1728.13  1725.18  1725.27         1124      35            0
        1    2021-09-30 15:15:00  1725.32  1728.70  1725.09  1728.49         1321      35            0
        2    2021-09-30 15:30:00  1728.52  1732.37  1728.25  1731.97         1819      35            0
        3    2021-09-30 15:45:00  1732.07  1737.59  1730.26  1736.88         1558      35            0
        4    2021-09-30 16:00:00  1736.99  1738.58  1734.82  1737.18         1860      35            0
        ...                  ...      ...      ...      ...      ...          ...     ...          ...
        5521 2021-12-23 22:45:00  1807.98  1809.17  1807.85  1808.78          830      35            0
        5522 2021-12-23 23:00:00  1808.82  1809.06  1808.44  1809.01          297      35            0
        5523 2021-12-23 23:15:00  1809.05  1809.05  1808.74  1808.74          168      35            0
        5524 2021-12-23 23:30:00  1808.78  1808.80  1807.72  1807.72          215      35            0
        5525 2021-12-23 23:45:00  1807.86  1808.40  1807.04  1808.27          283      35            0
        """
        df.columns = df.columns.map(str.capitalize) # columns.map : 全てのカラム(列)にstr.capitalizeを適用する, str.capitalize : 先頭の一文字を大文字、他を小文字に変換
        # dockarea描画用に適当にインジケータを用意
        df['ma'] = df['Close'].rolling(10).mean() # Closeの10個のデータの平均
        df['Hband'] = df['High'].rolling(25).max()
        df['Lband'] = df['Low'].rolling(25).min()
        h, l = df['High'].rolling(10).max(), df['Low'].rolling(10).min()
        df['stochastic_K'] = (df['Close']-l) / (h-l) * 100
        df['macd'] = df['Close'].rolling(12).mean()-df['Close'].rolling(26).mean() # sma版
        df['macd_sig'] = df['macd'].rolling(9).mean()
        df['macd_hist'] = df['macd']-df['macd_sig']
        return df


def main():
    
    # Dockのタイトルバーみたいなやつの色を変える
    # pyqtgraph.dockarea.Dock.DockLabelのupdateStyleを上書き
    from pyqtgraph.dockarea.Dock import DockLabel
    def updateStyle(self):
        self.setStyleSheet("DockLabel { color: #AAC; background-color: #444; }")
    setattr(DockLabel, 'updateStyle', updateStyle)
    
    style = """
        QWidget { color: #AAA; background-color: #333; border: 0px; padding: 0px; }
        QWidget:item:selected { background-color: #666; }
        QMenuBar::item { background: transparent; }
        QMenuBar::item:selected { background: transparent; border: 1px solid #666; }
    """
    
    #app = QApplication(sys.argv)
    app = pg.mkQApp()
    app.setStyleSheet(style) # StyleSheetで属性制御ができるらしい…HTMLのCSSのよう？
    test = TestMainWindow()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()

