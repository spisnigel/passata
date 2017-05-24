#!/usr/bin/env python

# Copyright 2017 Morel Bodin

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#   http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import math
from PySide import QtUiTools
from PySide.QtGui import *
from PySide.QtCore import QTimer
from PySide.phonon import Phonon
from subprocess import call

class PomodoroApp(QMainWindow):
    def __init__(self, parent=None):
        # 'stopped' 'pomodoro' 'long rest' 'short rest' 'interrupted'
        self.state = 'stopped'
        self.invertProgress = False
        self.soundOutput = 'subprocess'
        self.alertSoundPath = 'sounds/ping.wav'

        self.app = QApplication(sys.argv)
        self.app.setApplicationName('Passata')

        self.window = QtUiTools.QUiLoader().load('passata.ui')

        self.pomodoroDurationShow = \
            self.window.findChild(QLabel, 'pomodoroDurationShow')
        self.pomodoroDurationSlider = \
            self.window.findChild(QSlider, 'pomodoroDurationSlider')
        self.pomodoroDurationSlider.valueChanged \
            .connect(self.updatePomodoroDuration)
        self.updatePomodoroDuration()

        self.shortRestDurationShow = \
            self.window.findChild(QLabel, 'shortRestDurationShow')
        self.shortRestDurationSlider = \
            self.window.findChild(QSlider, 'shortRestDurationSlider')
        self.shortRestDurationSlider.valueChanged \
            .connect(self.updateShortRestDuration)
        self.updateShortRestDuration()

        self.longRestDurationShow = \
            self.window.findChild(QLabel, 'longRestDurationShow')
        self.longRestDurationSlider = \
            self.window.findChild(QSlider, 'longRestDurationSlider')
        self.longRestDurationSlider.valueChanged \
            .connect(self.updateLongRestDuration)
        self.updateLongRestDuration()

        self.pomodoroCountShow = \
            self.window.findChild(QLabel, 'pomodoroCountShow')
        self.pomodoroCountSlider = \
            self.window.findChild(QSlider, 'pomodoroCountSlider')
        self.pomodoroCountSlider.valueChanged \
            .connect(self.updatePomodoroCount)
        self.updatePomodoroCount()

        self.progressLabel = \
            self.window.findChild(QLabel, 'progressLabel')
        self.progressLabelRepeater = \
            self.window.findChild(QLabel, 'progressLabelRepeater')

        if self.soundOutput == 'phonon':
            self.mediaObject = Phonon.MediaObject(self.app)
            self.mediaObject \
                .setCurrentSource(Phonon.MediaSource(self.alertSoundPath))
            self.audioOutput \
                = Phonon.AudioOutput(Phonon.NotificationCategory, self.app)
            Phonon.createPath(self.mediaObject, self.audioOutput)

            volumeSliderReceptacle = \
                self.window.findChild(QWidget, 'volumeSliderReceptacle')
            volumeSliderZone = \
                volumeSliderReceptacle.findChild(QLayout, 'volumeSliderZone')
            self.volumeSlider = Phonon.VolumeSlider(self.audioOutput)
            volumeSliderZone.addWidget(self.volumeSlider)

        self.pomoImageStack = \
            self.window.findChild(QStackedWidget, 'pomoImageStack')
        self.stackIndex = {}
        widget = self.pomoImageStack.findChild(QWidget, 'pomoRedPage')
        self.stackIndex['red'] = self.pomoImageStack.indexOf(widget)
        widget = self.pomoImageStack.findChild(QWidget, 'pomoGreenPage')
        self.stackIndex['green'] = self.pomoImageStack.indexOf(widget)
        widget = self.pomoImageStack.findChild(QWidget, 'pomoYellowPage')
        self.stackIndex['yellow'] = self.pomoImageStack.indexOf(widget)

        self.startInterruptButton = \
            self.window.findChild(QPushButton, 'startInterruptButton')
        self.startInterruptButton.clicked \
            .connect(self.startInterruptClicked)
        
        self.configureQuitButton = \
            self.window.findChild(QPushButton, 'configureQuitButton')
        self.configureQuitButton.clicked \
            .connect(self.configureQuitClicked)

        self.okButton = \
            self.window.findChild(QPushButton, 'okButton')
        self.okButton.clicked.connect(self.okClicked)

        self.resetCountersButton = \
            self.window.findChild(QPushButton, 'resetCountersButton')
        self.resetCountersButton.clicked.connect(self.resetCountersClicked)

        self.quitButton = \
            self.window.findChild(QPushButton, 'quitButton')
        self.quitButton.clicked.connect(self.window.close)

        self.progressBar = \
            self.window.findChild(QProgressBar, 'progressBar')

        self.mainStack = \
            self.window.findChild(QStackedWidget, 'mainStack')
        widget = self.mainStack.findChild(QWidget, 'pomodoroPage')
        self.stackIndex['main'] = self.mainStack.indexOf(widget)
        widget = self.mainStack.findChild(QWidget, 'configurePage')
        self.stackIndex['configure'] = self.mainStack.indexOf(widget)
        self.mainStack.setCurrentIndex(self.stackIndex['main'])

        self.timer = QTimer()
        self.timer.timeout.connect(self.handleTimeout)

        self.reset()

    def playAlert(self):
        if self.soundOutput == None:
            pass
        elif self.soundOutput == 'phonon':
            self.mediaObject.play()
        elif self.soundOutput == 'subprocess':
            call(["mplayer", self.alertSoundPath])
        else:
            raise RuntimeError( \
                    'Unknown soundOutput: "' + self.soundOutput + '"')

    def handleTimeout(self):
        self.elapsedSeconds = self.elapsedSeconds + 1

        if self.elapsedSeconds < self.targetSeconds:
            self.updateProgressBar()
            self.updateProgressLabel()
            return

        # Timer has overflowed: Reset.
        self.elapsedSeconds = 0
        self.resetCountersButton.setEnabled(True)
        self.playAlert()

        if self.invertProgress:
            self.progressBar.setValue(0)
        else:
            self.progressBar.setValue(100)

        if self.state == 'pomodoro':
            self.completedPomodoroCount = 1 + self.completedPomodoroCount
        elif self.state == 'short rest':
            self.completedShortRestCount = 1 + self.completedShortRestCount
        elif self.state == 'long rest':
            self.completedLongRestCount = 1 + self.completedLongRestCount
        else:
            raise RuntimeError( \
                'Timer was running while in "' + self.state + '" state.')

        if self.state == 'pomodoro':
            self.pomoImageStack.setCurrentIndex(self.stackIndex['green'])
            pomodoros_per_period = self.pomodoroCountSlider.value()
            if (self.completedPomodoroCount % pomodoros_per_period) == 0:
                self.state = 'long rest'
                self.targetSeconds = self.longRestDurationSlider.value() * 60
            else:
                self.state = 'short rest'
                self.targetSeconds = self.shortRestDurationSlider.value() * 60
        else:
            self.state = 'pomodoro'
            self.pomoImageStack.setCurrentIndex(self.stackIndex['red'])
            self.targetSeconds = self.pomodoroDurationSlider.value() * 60

        if self.invertProgress:
            self.progressBar.setValue(100)
        else:
            self.progressBar.setValue(0)

    def reset(self):
        self.completedPomodoroCount = 0
        self.completedShortRestCount = 0
        self.completedLongRestCount = 0
        self.interruptionCount = 0
        self.resetCountersButton.setEnabled(False)
        self.applyConfig()

    def applyConfig(self):
        self.state = 'stopped'
        self.pomoImageStack.setCurrentIndex(self.stackIndex['green'])

        if self.invertProgress:
            self.progressBar.setValue(100)
        else:
            self.progressBar.setValue(0)

        self.targetSeconds = self.pomodoroDurationSlider.value() * 60
        self.elapsedSeconds = 0

        self.startInterruptButton.setEnabled(True)
        self.startInterruptButton.setText('Start')

        self.configureQuitButton.setEnabled(True)
        self.configureQuitButton.setText('Configure / Quit')

        self.updateProgressBar()
        self.updateProgressLabel()

    def updateProgressBar(self):
        seconds = self.targetSeconds - self.elapsedSeconds
        minutes = int(seconds / 60)
        percent = int(math.ceil(100.0*seconds)/self.targetSeconds)
        seconds = seconds % 60
        self.progressBar.setFormat('{minutes:d}:{seconds:02d}' \
            .format(minutes=minutes, seconds=seconds))

        if self.invertProgress:
            self.progressBar.setValue(percent)
        else:
            self.progressBar.setValue(100 - percent)


    def updateProgressLabel(self):
        if self.completedPomodoroCount == 1:
            pomoText = '1 full pomodoro, '
        else:
            pomoText = '{count} full pomodoros, ' \
                .format(count = self.completedPomodoroCount)

        if self.completedShortRestCount == 1:
            shortText = '1 short pause, '
        else:
            shortText = '{count} short pauses, ' \
                .format(count = self.completedShortRestCount)

        if self.completedLongRestCount == 1:
            longText = '1 long break '
        else:
            longText = '{count} long breaks ' \
                .format(count = self.completedLongRestCount)

        if self.interruptionCount == 1:
            interruptionText = 'and 1 interruption. '
        else:
            interruptionText = 'and {count} interruptions.' \
                .format(count = self.interruptionCount)

        self.progressLabel.setText( \
            pomoText + shortText + longText + interruptionText)
        self.progressLabelRepeater.setText( \
            pomoText + shortText + longText + interruptionText)

    def updatePomodoroDuration(self):
        count = self.pomodoroDurationSlider.value()

        if count == 1:
            text = "1 minute."
        else:
            text = "{count} minutes.".format(count=count)

        self.pomodoroDurationShow.setText(text)

    def updateShortRestDuration(self):
        count = self.shortRestDurationSlider.value()

        if count == 1:
            text = "1 minute."
        else:
            text = "{count} minutes.".format(count=count)

        self.shortRestDurationShow.setText(text)

    def updateLongRestDuration(self):
        count = self.longRestDurationSlider.value()

        if count == 1:
            text = "1 minute."
        else:
            text = "{count} minutes.".format(count=count)

        self.longRestDurationShow.setText(text)

    def updatePomodoroCount(self):
        count = self.pomodoroCountSlider.value()

        if count == 1:
            text = "1 pomodoro."
        else:
            text = "{count} pomodoros.".format(count=count)

        self.pomodoroCountShow.setText(text)

    def configureQuitClicked(self):
        self.mainStack.setCurrentIndex(self.stackIndex['configure'])

    def okClicked(self):
        self.applyConfig()
        self.mainStack.setCurrentIndex(self.stackIndex['main'])

    def resetCountersClicked(self):
        self.reset()

    def startInterruptClicked(self):
        if (self.state == 'stopped') or (self.state == 'interrupted'):
            self.state = 'pomodoro'
            self.pomoImageStack.setCurrentIndex(self.stackIndex['red'])
            self.elapsedSeconds = 0
            self.targetSeconds = self.pomodoroDurationSlider.value() * 60
            self.startInterruptButton.setText('Interrupt')
            self.configureQuitButton.setEnabled(False)
            self.timer.start(1000) # milliseconds

            if self.invertProgress:
                self.progressBar.setValue(100)
            else:
                self.progressBar.setValue(0)

            self.updateProgressBar()
        elif self.state == 'pomodoro':
            self.state = 'interrupted'
            self.interruptionCount = self.interruptionCount + 1
            self.resetCountersButton.setEnabled(True)
            self.updateProgressBar()
            self.updateProgressLabel()
            self.pomoImageStack.setCurrentIndex(self.stackIndex['yellow'])
            self.startInterruptButton.setText('Resume')
            self.configureQuitButton.setEnabled(True)
            self.timer.stop()
        elif (self.state == 'short rest') or (self.state == 'long rest'):
            self.state = 'stopped'
            self.pomoImageStack.setCurrentIndex(self.stackIndex['green'])
            self.startInterruptButton.setText('Start')
            self.configureQuitButton.setEnabled(True)
            self.timer.stop()
        else:
            raise RuntimeError('Unknown state: "' + self.state + '"')

    def run(self):
        self.window.show()
        sys.exit(self.app.exec_())

if __name__ == '__main__':
    pomodoro = PomodoroApp()
    pomodoro.run()

