#!/usr/bin/env python3

from __future__ import annotations

import pickle
import socket
import sys

from PyQt6 import QtCore, QtGui, QtWidgets, QtCharts

HOST = '127.0.0.1'
PORT = 8888

def recv_all(s: socket.socket, num_bytes: int):
    buffer = bytearray(num_bytes)
    mview = memoryview(buffer)

    bytes_received = 0

    while bytes_received < num_bytes:
        len = s.recv_into(mview[bytes_received:], num_bytes - bytes_received)
        if not len:
            return None
        bytes_received += len

    return buffer

def recv_pickle(s: socket.socket) -> object:
    len_bytes = recv_all(s, 4)
    if not len_bytes:
        return None

    len_data = int.from_bytes(len_bytes, 'big', signed=False)

    data_bytes = recv_all(s, len_data)
    if not data_bytes:
        return None

    data = pickle.loads(data_bytes)

    return data

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        s = socket.create_connection((HOST, PORT))
        s.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
        self.conn = s

        self.notif = QtCore.QSocketNotifier(s.fileno(),
                                            QtCore.QSocketNotifier.Type.Read,
                                            self)
        self.notif.activated.connect(self.socketEvent)

        print('Connected')

        layout = QtWidgets.QVBoxLayout()

        self.series = QtCharts.QLineSeries()
        self.series.setPen(QtGui.QPen(QtCore.Qt.GlobalColor.blue, 20))

        self.chart = QtCharts.QChart()
        self.chart.addSeries(self.series)
        self.chart.legend().hide()

        axisX = QtCharts.QDateTimeAxis()
        #axisX.setTickCount(1)
        axisX.setFormat('h:mm:ss')
        axisX.setTitleText('Time')
        self.chart.addAxis(axisX, QtCore.Qt.AlignmentFlag.AlignBottom)
        self.series.attachAxis(axisX)
        self.axisX = axisX

        axisY = QtCharts.QValueAxis()
        axisY.setLabelFormat('%i')
        axisY.setTitleText('HR')
        axisY.setRange(40, 200)
        self.chart.addAxis(axisY, QtCore.Qt.AlignmentFlag.AlignLeft)
        self.series.attachAxis(axisY)
        self.axisY = axisY

        self.chartView = QtCharts.QChartView(self.chart, self)
        layout.addWidget(self.chartView)

        font = self.font()
        font.setPointSize(200)

        labelLayout = QtWidgets.QHBoxLayout()
        layout.addLayout(labelLayout)

        self.hrLabel = QtWidgets.QLabel()
        self.hrLabel.setFont(font)
        labelLayout.addWidget(self.hrLabel)
        self.hrLabel.setText('0')

        self.lap = 0
        self.lapLabel = QtWidgets.QLabel()
        self.lapLabel.setFont(font)
        labelLayout.addWidget(self.lapLabel)
        self.lapLabel.setText('Laps: 0')

        widget = QtWidgets.QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

    def new_lap(self):
        self.lap += 1
        self.lapLabel.setText(f'Laps: {self.lap}')

    def keyPressEvent(self, event):
        if isinstance(event, QtGui.QKeyEvent):
            if event.key() == QtCore.Qt.Key.Key_Escape:
                self.close()
            elif event.key() == QtCore.Qt.Key.Key_Space:
                self.new_lap()

    def socketEvent(self, _):
        data = recv_pickle(self.conn)

        ts,ev = data
        heart_rate = ev[1]
        self.hrLabel.setText(f'HR: {heart_rate}')

        dt = QtCore.QDateTime.fromMSecsSinceEpoch(int(ts) * 1000)

        self.series.append(dt.toMSecsSinceEpoch(), heart_rate)

        if self.axisX.min().date().year() == 1970:
            self.axisX.setRange(dt, dt.addSecs(10))

        if dt < self.axisX.min():
            self.axisX.setMin(dt)

        if dt > self.axisX.max():
            self.axisX.setMax(dt)

def main():
    app = QtWidgets.QApplication(sys.argv)

    window = MainWindow()
    window.resize(1280, 600)
    window.showMaximized()

    app.exec()

if __name__ == '__main__':
    sys.exit(main())
