#!/usr/bin/python2
# -*- coding: utf-8 -*-

# mentalcalculation - version 0.3.4.4
# Copyright (C) 2008-2010, solsTiCe d'Hiver <solstice.dhiver@gmail.com>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
# In addition, as a special exception, the copyright holders give
# permission to link the code of portions of this program with the
# OpenSSL library under certain conditions as described in each
# individual source file, and distribute linked combinations
# including the two.
#
# You must obey the GNU General Public License in all respects for
# all of the code used other than OpenSSL.  If you modify file(s)
# with this exception, you may extend this exception to your version
# of the file(s), but you are not obligated to do so.  If you do not
# wish to do so, delete this exception statement from your version.
# If you delete this exception statement from all source files in the
# program, then also delete it here.
#

import sys
from optparse import OptionParser
from platform import system
from tempfile import mkstemp, NamedTemporaryFile
from os import remove, sep
from os.path import isfile, abspath
try:
    from random import SystemRandom
    IS_SYSTEMRANDOM_AVAILABLE = True
except ImportError:
    from random import randint

try:
    from PyQt4 import QtGui,QtCore
except ImportError:
    print 'Error: you need PyQt4 to run this software'
    sys.exit(1)
try:
    from PyQt4.phonon import Phonon
except ImportError:
    print 'Error: you need phonon support in PyQt4 to run this software'
    sys.exit(1)
import settings, main

DIGIT = dict([(i,(int('1'+'0'*(i-1)), int('9'*i))) for i in range(1,10)])

appName = 'mentalcalculation'
appVersion = '0.3.4.4'

BELL = 'sound/bell.mp3'
BELL_DURATION = 600
THREEBELLS = 'sound/3bells.mp3'
THREEBELLS_DURATION = 1000
ANNOYING_SOUND = 'sound/annoying-sound.mp3'
ANNOYING_SOUND_DURATION = 150
GOOD = 'sound/good.mp3'
BAD = 'sound/bad.mp3'
WELCOME = 'img/soroban.png'
SMILE = 'img/face-smile.png'
SAD = 'img/face-sad.png'
RESTART = 'img/restart.png'

class Settings(QtGui.QDialog):
    def __init__(self, mysettings, parent=None):
        QtGui.QDialog.__init__(self, parent)
        self.ui = settings.Ui_Dialog()
        self.ui.setupUi(self)
        self.importSettings(mysettings)
        self.ui.sb_flash.setEnabled(not self.ui.cb_speech.isChecked())
        self.ui.cb_onedigit.setEnabled(self.ui.cb_speech.isChecked())
        self.connect(self, QtCore.SIGNAL('accepted()'), self.exportSettings)
        self.connect(self.ui.cb_speech, QtCore.SIGNAL('clicked()'), self.updateSound)
        if IS_ESPEAK_INSTALLED:
            self.ui.cb_speech.setEnabled(True)
            self.ui.pm_warning.hide()
        self.adjustSize()

    def importSettings(self, mysettings):
        self.ui.sb_flash.setValue(mysettings['flash'])
        self.ui.sb_timeout.setValue(mysettings['timeout'])
        self.ui.sb_digits.setValue(mysettings['digits'])
        self.ui.sb_rows.setValue(mysettings['rows'])
        self.ui.cb_speech.setChecked(mysettings['speech'])
        self.ui.cb_onedigit.setChecked(mysettings['one_digit'])
        self.ui.cb_fullscreen.setChecked(mysettings['fullscreen'])
        self.ui.cb_handsfree.setChecked(mysettings['hands_free'])
        if not IS_ESPEAK_INSTALLED:
            self.ui.cb_speech.setChecked(False)
        self.ui.cb_neg.setChecked(mysettings['neg'])
        self.mysettings = mysettings

    def exportSettings(self):
        mysettings = {}
        mysettings['flash'] = self.ui.sb_flash.value()
        mysettings['timeout'] = self.ui.sb_timeout.value()
        mysettings['digits'] = self.ui.sb_digits.value()
        mysettings['rows'] = self.ui.sb_rows.value()
        mysettings['speech'] = self.ui.cb_speech.isChecked()
        mysettings['fullscreen'] = self.ui.cb_fullscreen.isChecked()
        mysettings['hands_free'] = self.ui.cb_handsfree.isChecked()
        mysettings['one_digit'] = self.ui.cb_onedigit.isChecked()
        mysettings['neg'] = self.ui.cb_neg.isChecked()
        self.mysettings = mysettings

    def updateSound(self):
        sound = self.ui.sb_flash.isEnabled()
        self.ui.sb_flash.setEnabled(not sound)
        self.ui.cb_onedigit.setEnabled(sound)

    def exec_(self):
        ok = QtGui.QDialog.exec_(self)
        return (ok, self.mysettings)

class Main(QtGui.QMainWindow):
    def __init__(self, parent=None, flag=QtCore.Qt.Widget):
        QtGui.QMainWindow.__init__(self, parent, flag)
        self.ui = main.Ui_MainWindow()
        self.ui.setupUi(self)
        self.score = (0,0)
        self.started = False
        # default settings
        self.digits = 1
        self.rows = 5
        self.flash = 500
        self.timeout = 1500
        self.neg = False
        self.speech = False
        self.one_digit = False
        self.fullscreen = False
        self.hands_free = False
        self.tmpwav= None
        self.replay = False
        self.noscore = False
        self.history = []
        self.font_color = None
        self.background_color = None
        self.annoying_sound = False
        self.no_plus_sign = False
        self.oldPointSize = 72

        self.isLabelClearable = True
        self.geometryLabel = None

        self.timerUpdateLabel = QtCore.QTimer()
        self.timerUpdateLabel.setSingleShot(True)
        self.connect(self.timerUpdateLabel, QtCore.SIGNAL('timeout()'), self.updateLabel)
        self.timerShowAnswer = QtCore.QTimer()
        self.timerShowAnswer.setSingleShot(True)
        self.connect(self.timerShowAnswer, QtCore.SIGNAL('timeout()'), self.showAnswer)
        self.timerRestartPlay = QtCore.QTimer()
        self.timerRestartPlay.setSingleShot(True)
        self.connect(self.timerRestartPlay, QtCore.SIGNAL('timeout()'), self.restartPlay)

        if IS_SYSTEMRANDOM_AVAILABLE:
            self.randint = SystemRandom().randint
        else:
            self.randint = randint

        self.ui.label.clear()
        self.ui.le_answer.setInputMask('000009')
        self.ui.l_total.hide()

        self.shortcut_bigger_font = QtGui.QShortcut(QtGui.QKeySequence('CTRL++'), self)
        self.connect(self.shortcut_bigger_font, QtCore.SIGNAL('activated()'), self.increaseFontSize)
        self.shortcut_smaller_font = QtGui.QShortcut(QtGui.QKeySequence('CTRL+-'), self)
        self.connect(self.shortcut_smaller_font, QtCore.SIGNAL('activated()'), self.decreaseFontSize)
        self.shortcut_F11 = QtGui.QShortcut(QtGui.QKeySequence('F11'), self)
        self.connect(self.shortcut_F11, QtCore.SIGNAL('activated()'), self.updateFullScreen)
        self.shortcut_Enter = QtGui.QShortcut(QtGui.QKeySequence('Enter'), self)
        self.connect(self.shortcut_Enter, QtCore.SIGNAL('activated()'), self.ui.pb_start.click)

        self.connect(self.ui.pb_check, QtCore.SIGNAL('clicked()'), self.updateAnswer)
        self.connect(self.ui.pb_settings, QtCore.SIGNAL('clicked()'), self.changeSettings)
        self.connect(self.ui.pb_exit, QtCore.SIGNAL('clicked()'), self.close)
        self.connect(self.ui.pb_start, QtCore.SIGNAL('clicked()'), self.startPlay)
        self.connect(self.ui.pb_replay, QtCore.SIGNAL('clicked()'), self.redisplaySequence)

        # TODO: add a welcome message; this would be more explicit that this
        self.ui.label.setPixmap(QtGui.QPixmap(WELCOME))

        self.player = Phonon.createPlayer(Phonon.AccessibilityCategory, Phonon.MediaSource(''))
        self.connect(self.player, QtCore.SIGNAL('stateChanged(Phonon::State, Phonon::State)'), self.cleanup)

        self.importSettings()
        # change background and foreground color if needed
        stylesheet = []
        if self.background_color is not None:
            stylesheet.append('background-color: %s' % self.background_color)
        if self.font_color is not None:
            stylesheet.append('color: %s' % self.font_color)
        if stylesheet != []:
            self.ui.label.setStyleSheet(';'.join(stylesheet))

        self.displayWindow()

    def importSettings(self):
        # restore settings from the settings file if the settings exist
        settings = QtCore.QSettings(QtCore.QSettings.IniFormat,
                QtCore.QSettings.UserScope, '%s' % appName, '%s' % appName)

        if settings.contains('digits'):
            # these value have been written by the program, so then should be ok
            self.digits = settings.value('digits').toInt()[0]
            self.rows = settings.value('rows').toInt()[0]
            self.timeout = settings.value('timeout').toInt()[0]
            self.flash = settings.value('flash').toInt()[0]
            self.hands_free = settings.value('hands_free').toBool()
            self.neg = settings.value('neg').toBool()
            if settings.contains('no_plus_sign'):
                self.no_plus_sign = settings.value('no_plus_sign').toBool()
        if 'Espeak' in settings.childGroups():
            global ESPEAK_CMD, ESPEAK_LANG, ESPEAK_SPEED, IS_ESPEAK_INSTALLED
            # test for every option
            if settings.contains('Espeak/cmd'):
                ESPEAK_CMD = str(settings.value('Espeak/cmd').toString()).strip('"')
                IS_ESPEAK_INSTALLED = isfile(ESPEAK_CMD)
            if settings.contains('Espeak/lang'):
                ESPEAK_LANG = str(settings.value('Espeak/lang').toString())
                if ESPEAK_LANG.find('_') > 0:
                    ESPEAK_LANG = ESPEAK_LANG[:ESPEAK_LANG.index('_')]
            if settings.contains('Espeak/speed'):
                a,b = settings.value('Espeak/speed').toInt()
                # check if it's good
                if b:
                    ESPEAK_SPEED = a

        # GUI settings
        self.fullscreen = settings.value('GUI/fullscreen').toBool()
        if settings.contains('GUI/font'):
            font = str(settings.value('GUI/font').toString())
            self.ui.label.setFont(QtGui.QFont(font, 72, QtGui.QFont.Bold))
        if settings.contains('GUI/font_color'):
            self.font_color = str(settings.value('GUI/font_color').toString())
        if settings.contains('GUI/background_color'):
            self.background_color = str(settings.value('GUI/background_color').toString())

        # Sound settings
        self.speech = settings.value('Sound/speech').toBool()
        self.one_digit = settings.value('Sound/one_digit').toBool()
        if settings.contains('Sound/annoying_sound'):
            self.annoying_sound = settings.value('Sound/annoying_sound').toBool()

    def updateFullScreen(self):
        self.fullscreen = not self.fullscreen
        self.displayWindow()

    def displayWindow(self):
        font = self.ui.label.font()
        if self.fullscreen:
            self.oldPointSize = font.pointSize()
            self.showFullScreen()
            # width is the size of of '+9999' in the current font
            width = QtGui.QFontMetrics(font).width('+'+'9'*(self.digits+2))
            # the factor to multiply by to use the max. space
            factor = float(self.ui.gb_number.width()-10)/width
            newPointSize = min(int(font.pointSize()*factor), self.ui.gb_number.height()-10)
        else:
            newPointSize = self.oldPointSize
            self.showNormal()
        font.setPointSize(newPointSize)
        self.ui.label.setFont(font)

        settings = QtCore.QSettings(QtCore.QSettings.IniFormat, QtCore.QSettings.UserScope, '%s' % appName, '%s' % appName)
        settings.setValue('GUI/fullscreen', QtCore.QVariant(self.fullscreen))

    def increaseFontSize(self):
        font = self.ui.label.font()
        font.setPointSize(font.pointSize()+10)
        width = QtGui.QFontMetrics(font).width('+'+'9'*(self.digits+2))
        if width < self.ui.gb_number.width():
            if self.ui.label.text() == '':
                self.ui.label.setText('9'*self.digits)
            self.ui.label.setFont(font)
            QtCore.QTimer.singleShot(250, self.ui.label.clear)

    def decreaseFontSize(self):
        font = self.ui.label.font()
        if font.pointSize()-10 >= 32:
            font.setPointSize(font.pointSize()-10)
            if self.ui.label.text() == '':
                self.ui.label.setText('9'*self.digits)
            self.ui.label.setFont(font)
            QtCore.QTimer.singleShot(250, self.ui.label.clear)

    def clearLabel(self):
        if self.isLabelClearable:
            self.ui.label.clear()
            # display the next number after timeout
            self.timerUpdateLabel.setInterval(self.timeout)
            self.timerUpdateLabel.start()

    def changeSettings(self):
        if not self.started:
            mysettings = {}
            mysettings['flash'] = self.flash
            mysettings['timeout'] = self.timeout
            mysettings['digits'] = self.digits
            mysettings['rows'] = self.rows
            mysettings['speech'] = self.speech
            mysettings['fullscreen'] = self.fullscreen
            mysettings['hands_free'] = self.hands_free
            mysettings['one_digit'] = self.one_digit
            mysettings['neg'] = self.neg
            s = Settings(mysettings, parent=self)
            s.connect(s.ui.cb_fullscreen, QtCore.SIGNAL('stateChanged(int)'), self.updateFullScreen)
            ok, mysettings = s.exec_()
            if ok:
                self.flash = mysettings['flash']
                self.timeout = mysettings['timeout']
                self.digits = mysettings['digits']
                self.rows = mysettings['rows']
                self.speech = mysettings['speech']
                self.one_digit = mysettings['one_digit']
                self.hands_free = mysettings['hands_free']
                self.neg = mysettings['neg']
                # always save settings when closing the settings dialog
                settings = QtCore.QSettings(QtCore.QSettings.IniFormat,
                        QtCore.QSettings.UserScope, '%s' % appName, '%s' % appName)
                settings.setValue('digits', QtCore.QVariant(self.digits))
                settings.setValue('rows', QtCore.QVariant(self.rows))
                settings.setValue('timeout', QtCore.QVariant(self.timeout))
                settings.setValue('flash', QtCore.QVariant(self.flash))
                settings.setValue('hands_free', QtCore.QVariant(self.hands_free))
                settings.setValue('neg', QtCore.QVariant(self.neg))
                settings.setValue('no_plus_sign', QtCore.QVariant(self.no_plus_sign))

                settings.setValue('GUI/font_color', QtCore.QVariant(self.font_color if self.font_color is not None else '#000000'))
                settings.setValue('GUI/background_color', QtCore.QVariant(self.background_color \
                        if self.background_color is not None else 'transparent'))

                settings.setValue('Espeak/cmd', QtCore.QVariant(ESPEAK_CMD))
                settings.setValue('Espeak/lang', QtCore.QVariant(ESPEAK_LANG))
                settings.setValue('Espeak/speed', QtCore.QVariant(ESPEAK_SPEED))

                settings.setValue('Sound/one_digit', QtCore.QVariant(self.one_digit))
                settings.setValue('Sound/speech', QtCore.QVariant(self.speech))
                settings.setValue('Sound/annoying_sound', QtCore.QVariant(self.annoying_sound))

                # disable replay button
                self.ui.pb_replay.setEnabled(False)
                # go to full screen if needed

    def restartPlay(self):
        if self.started:
            duration = self.timeout
            if self.speech and IS_ESPEAK_INSTALLED:
                self.disconnect(self.player, QtCore.SIGNAL('finished()'), self.restartPlay)
                self.connect(self.player, QtCore.SIGNAL('finished()'), self.clearLabel)
                self.player.setCurrentSource(Phonon.MediaSource(THREEBELLS))
                duration = THREEBELLS_DURATION
                self.player.play()
            self.isLabelClearable = False
            self.started = False
            self.ui.label.clear()
            self.ui.l_total.hide()
            self.ui.pb_replay.setEnabled(False)
            self.ui.label.setPixmap(QtGui.QPixmap(RESTART))
            QtCore.QTimer.singleShot(duration, self.startPlay)

    def redisplaySequence(self):
        self.isLabelClearable = False
        self.started = False
        self.replay = True
        self.ui.pb_replay.setEnabled(False)
        self.timerUpdateLabel.stop()
        if self.hands_free:
            self.disconnect(self.player, QtCore.SIGNAL('finished()'), self.restartPlay)
            self.connect(self.player, QtCore.SIGNAL('finished()'), self.clearLabel)
            self.timerShowAnswer.stop()
            self.timerRestartPlay.stop()
            self.ui.l_total.hide()
        self.startPlay()

    def startPlay(self):
        if not self.started:
            self.started = True
            self.isLabelClearable = True
            self.ui.label.clear()
            self.ui.l_total.hide()
            #self.ui.l_answer.setText('Your answer')
            self.ui.le_answer.clear()
            self.ui.le_answer.setEnabled(False)
            self.ui.pb_check.setEnabled(False)
            self.ui.pb_settings.setEnabled(False)
            self.count = 0
            # generate sequence
            if self.replay:
                self.replay = False
            else:
                self.makeHistory()
                self.noscore = False
                self.ui.pb_replay.setEnabled(False)
            # change pb_start to 'Stop' when starting display
            self.ui.pb_start.setText(self.tr('&Stop'))
            self.ui.pb_start.setToolTip(self.tr('Stop the sequence'))
            if self.speech and IS_ESPEAK_INSTALLED:
                self.player.stop()
                self.connect(self.player, QtCore.SIGNAL('finished()'), self.clearLabel)
            elif self.annoying_sound:
                self.disconnect(self.player, QtCore.SIGNAL('finished()'), self.clearLabel)
                self.player.setCurrentSource(Phonon.MediaSource(ANNOYING_SOUND))
            if self.hands_free:
                self.ui.l_answer.setEnabled(False)
            # wait 1s before starting the display
            self.timerUpdateLabel.setInterval(1000)
            self.timerUpdateLabel.start()
        else:
            # then stop it
            self.started = False
            self.isLabelClearable = False
            self.timerUpdateLabel.stop()
            if self.hands_free:
                self.disconnect(self.player, QtCore.SIGNAL('finished()'), self.restartPlay)
                self.connect(self.player, QtCore.SIGNAL('finished()'), self.clearLabel)
                self.timerShowAnswer.stop()
                self.timerRestartPlay.stop()
                self.ui.l_answer.setEnabled(True)
                self.ui.l_total.hide()
            self.ui.pb_settings.setEnabled(True)
            self.ui.gb_number.setTitle('#')
            self.ui.pb_start.setText(self.tr('&Start'))
            self.ui.pb_start.setToolTip(self.tr('Start a sequence'))
            self.ui.label.clear()
            if options.verbose:
                print
            if self.speech and IS_ESPEAK_INSTALLED:
                self.player.stop()
            if not self.hands_free:
                # reset history
                self.history = []

    def cleanup(self, newstate, oldstate):
        if (newstate == Phonon.PausedState or newstate == Phonon.StoppedState) and oldstate == Phonon.PlayingState:
            if self.tmpwav is not None:
                self.tmpwav.close()
                remove(self.tmpwav.name)
                self.tmpwav = None

    def pronounceit(self, s):
        p = QtCore.QProcess(self)
        # Create a tmp wav file that it is later played by Phonon back end
        self.tmpwav = NamedTemporaryFile(suffix='.wav', prefix='mentalcalculation_', delete=False)
        p.start(ESPEAK_CMD, ['-v', ESPEAK_LANG, '-s',  '%d' % ESPEAK_SPEED,'-w', self.tmpwav.name, "'%s'" % s])
        p.waitForFinished()
        # so that it works also on Windows ! wtf !
        self.tmpwav.close()
        self.player.stop()
        # make sure to use the tmp wav
        self.player.setCurrentSource(Phonon.MediaSource(self.tmpwav.name))
        self.player.play()

    def updateAnswer(self):
        if self.ui.le_answer.isEnabled():
            try:
                a = int(self.ui.le_answer.text())
            except ValueError:
                a = -100
            u,v = self.score
            if  a == self.answer:
                img = SMILE
                sound = GOOD
                msg = ':-)'
                u += 1
            else:
                msg = ':-('
                img = SAD
                sound = BAD
            # Don't score twice if replay
            if not self.noscore:
                self.score = u,v+1
            if msg == ':-)':
                self.noscore = True
            self.ui.l_total.show()
            self.ui.l_total.setText(self.tr('The correct answer is %1').arg(self.answer))
            self.ui.le_answer.setDisabled(True)
            self.ui.pb_check.setDisabled(True)
            self.ui.pb_start.setFocus(QtCore.Qt.OtherFocusReason)
            self.ui.label.setPixmap(QtGui.QPixmap(img))
            if self.speech and IS_ESPEAK_INSTALLED:
                self.player.setCurrentSource(Phonon.MediaSource(sound))
                self.player.play()
            self.setWindowTitle(self.tr('Mental Calculation %1/%2').arg(self.score[0]).arg(self.score[1]))
            self.disconnect(self.shortcut_Enter, QtCore.SIGNAL('activated()'), self.ui.pb_check.click)
            self.connect(self.shortcut_Enter, QtCore.SIGNAL('activated()'), self.ui.pb_start.click)

            if options.verbose:
                sys.stdout.flush()

    def makeHistory(self):
        answer = 0
        self.history = []
        for i in range(self.rows):
            a,b = DIGIT[self.digits]
            neg = False
            if self.neg:
                neg = bool(self.randint(0,1))
            if neg:
                if answer > a:
                    b = min(b, answer)
                else:
                    neg = False
            n = self.randint(a, b)
            # avoid a n - n situation
            while neg and n == self.history[-1]:
                n = self.randint(a, b)
            if neg and answer - n >= 0:
                n = -n
            answer += n
            self.history.append(n)
        self.answer = answer

    def showAnswer(self):
        if self.started:
            self.ui.l_total.show()
            self.ui.l_total.setText(self.tr('The correct answer is %1').arg(self.answer))
            self.ui.label.setText('=%d' % self.answer)
            if self.speech and IS_ESPEAK_INSTALLED:
                # pronounce one digit at a time
                t = '= %d' % self.answer
                if self.one_digit:
                    t = ' '.join(list(t)).replace('- ', '-')
                if ESPEAK_LANG.startswith('fr'):
                    t = t.replace('=', u'égal ')
                print t
                self.disconnect(self.player, QtCore.SIGNAL('finished()'), self.clearLabel)
                self.connect(self.player, QtCore.SIGNAL('finished()'), self.restartPlay)
                self.pronounceit(t)
            else:
                QtCore.QTimer.singleShot(2*self.flash, self.ui.label.clear)
                QtCore.QTimer.singleShot(2*self.flash, self.ui.l_total.hide)
                self.timerRestartPlay.setInterval(2*self.flash+self.timeout)
                self.timerRestartPlay.start()

    def updateLabel(self):
        if self.started:
            if self.count == self.rows:
                self.isLabelClearable = False
                if not self.hands_free:
                    self.started = False
                duration = self.timeout
                if self.speech and IS_ESPEAK_INSTALLED:
                    self.player.stop()
                    self.player.setCurrentSource(Phonon.MediaSource(BELL))
                    self.player.play()
                    duration += BELL_DURATION

                self.ui.label.setText('?')
                self.ui.gb_number.setTitle('#')
                self.ui.pb_replay.setEnabled(True)
                if self.hands_free:
                    self.timerShowAnswer.setInterval(duration)
                    self.timerShowAnswer.start()
                else:
                    self.ui.pb_start.setText(self.tr('&Start'))
                    self.ui.pb_start.setToolTip(self.tr('Start a sequence'))
                    self.ui.le_answer.setEnabled(True)
                    self.ui.pb_check.setEnabled(True)
                    self.ui.pb_settings.setEnabled(True)
                    self.ui.le_answer.setFocus(QtCore.Qt.OtherFocusReason)
                    self.disconnect(self.shortcut_Enter, QtCore.SIGNAL('activated()'), self.ui.pb_start.click)
                    self.connect(self.shortcut_Enter, QtCore.SIGNAL('activated()'), self.ui.pb_check.click)
                if options.verbose:
                    print
            else:
                self.count += 1
                self.ui.gb_number.setTitle('#%d / %s' % (self.count, self.rows))
                n = self.history[self.count-1]
                t = '%d' % n
                if self.neg and self.count > 1:
                    t = '%+d' % n
                if self.no_plus_sign and t.startswith('+'):
                    t = t[1:]
                self.ui.label.setText(t)
                # print the sequence in the console
                if options.verbose:
                    print t,
                # say it aloud
                if self.speech and IS_ESPEAK_INSTALLED:
                    # pronounce one digit at a time
                    if self.one_digit:
                        t = ' '.join(list(t)).replace('- ', '-')
                    # fix a bug with french not pronouncing the negative sign
                    if ESPEAK_LANG.startswith('fr'):
                        t = t.replace('-', 'moins ')
                    self.pronounceit(t)
                else:
                    if self.annoying_sound:
                        self.player.seek(0)
                        self.player.play()
                    # clear the label after self.flash time
                    QtCore.QTimer.singleShot(self.flash, self.clearLabel)

    def closeEvent(self, event):
        # stop the player
        if self.player:
            self.player.stop()
            self.player = None
        QtGui.QMainWindow.closeEvent(self, event)

if __name__ == '__main__':
    parser = OptionParser(usage='usage: %prog [-v]')
    parser.add_option('-v', '--verbose', action='store_true', dest='verbose',
            default=False, help='be verbose: print in console each number displayed')
    (options,args) = parser.parse_args(sys.argv)

    WINDOWS = system() == 'Windows'
    if WINDOWS:
        ESPEAK_CMD_LIST = ['C:\Program Files\eSpeak\command_line\espeak.exe', 'C:\Program Files (x86)\eSpeak\command_line\espeak.exe']
    else:
        ESPEAK_CMD_LIST = ['/usr/bin/espeak']

    # check espeak in the default location
    ESPEAK_CMD = ESPEAK_CMD_LIST[0]
    IS_ESPEAK_INSTALLED = False
    i = 0
    while not IS_ESPEAK_INSTALLED and i < len(ESPEAK_CMD_LIST):
        if isfile(ESPEAK_CMD_LIST[i]):
            IS_ESPEAK_INSTALLED = True
            ESPEAK_CMD = ESPEAK_CMD_LIST[i]
            break
        i += 1

    app = QtGui.QApplication(sys.argv)
    app.setApplicationName('Mental Calculation')

    # initialize locale and load translation files if available
    locale = QtCore.QLocale()
    LOCALENAME = str(locale.system().name())
    translator = QtCore.QTranslator()
    translator.load('mentalcalculation_%s' % LOCALENAME, '.')
    app.installTranslator(translator)

    if LOCALENAME.find('_') > 0:
        ESPEAK_LANG = LOCALENAME[:LOCALENAME.index('_')]
    else:
        ESPEAK_LANG = LOCALENAME
    ESPEAK_SPEED = 170 # the default of espeak

    # create main gui and display settings dialog
    f = Main()
    f.show()
    f.raise_() # for Mac Os X
    f.changeSettings()

    sys.exit(app.exec_())

