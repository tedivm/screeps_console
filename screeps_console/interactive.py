#!/usr/bin/env python

import atexit
import command
import json
import os
import outputparser
from settings import getSettings
import signal
import subprocess
import sys
from themes import themes
import urwid


class ScreepsInteractiveConsole:

    consoleWidget = False
    listWalker = False
    userInput = False

    def __init__(self):

        frame = self.getFrame()
        comp = self.getCommandProcessor()
        self.loop = urwid.MainLoop(urwid.AttrMap(frame, 'bg'), unhandled_input=comp.onInput, palette=themes['dark'])
        comp.setDisplayWidgets(self.loop, frame, self.getConsole(), self.getConsoleListWalker(), self.getEdit())
        console_monitor = ScreepsConsoleMonitor(self.consoleWidget, self.listWalker, self.loop)
        self.loop.run()


    def getFrame(self):
        urwid.AttrMap(self.getEdit(), 'input')
        frame_widget = urwid.Frame(
            header=self.getHeader(),
            body=self.getConsole(),
            footer=urwid.AttrMap(self.getEdit(), 'input'),
            focus_part='footer')
        return frame_widget



    def getHeader(self):
        return urwid.AttrMap(urwid.Text("Screeps Interactive Console", align='center'), 'header')

    def getEdit(self):
        if not self.userInput:
            self.userInput = consoleEdit("> ")
        return self.userInput

    def getConsole(self):
        if not self.consoleWidget:
            self.consoleWidget = consoleWidget(self.getConsoleListWalker())
        return self.consoleWidget

    def getConsoleListWalker(self):
        if not self.listWalker:
            self.listWalker = urwid.SimpleListWalker([self.getWelcomeMessage()])
        return self.listWalker

    def getCommandProcessor(self):
        return command.Processor()

    def getWelcomeMessage(self):
        return urwid.Text(('default', 'Welcome to the Screeps Interactive Console'))


class consoleWidget(urwid.ListBox):

    _autoscroll = True


    def setAutoscroll(self, option):
        self._autoscroll = option


    def autoscroll(self):
        if(self._autoscroll):
            self.scrollBottom()

    def scrollBottom(self):
        self._autoscroll = True
        if len(self.body) > 0:
            self.set_focus(len(self.body)-1)

    def scrollUp(self, quantity):
        self.setAutoscroll(False)
        new_pos = self.focus_position - quantity
        if new_pos < 0:
            new_pos = 0
        self.set_focus(new_pos)


    def scrollDown(self, quantity):
        self.setAutoscroll(False)
        max_pos = len(self.body)-1
        new_pos = self.focus_position + quantity
        if new_pos > max_pos:
            self.setAutoscroll(True)
            new_pos = max_pos
        self.set_focus(new_pos)


class consoleEdit(urwid.Edit):

    inputBuffer = []
    inputOffset = 0

    def bufferInput(self, text):
        self.inputBuffer.insert(0, text)

    def keypress(self, size, key):

        if key == 'enter':
            edit_text = self.get_edit_text()
            self.bufferInput(edit_text)
            self.inputOffset = 0

        if key == 'up':
            bufferLength = len(self.inputBuffer)
            if bufferLength > 0:
                self.inputOffset += 1
                if self.inputOffset > bufferLength:
                    self.inputOffset = bufferLength

                index = self.inputOffset-1
                new_text = self.inputBuffer[index]
                self.set_edit_text(new_text)
            return

        if key == 'down':
            bufferLength = len(self.inputBuffer)
            if bufferLength > 0:
                self.inputOffset -= 1
                if self.inputOffset < 0:
                    self.inputOffset = 0

                if self.inputOffset == 0:
                    new_text = ''
                else:
                    index = self.inputOffset-1
                    new_text = self.inputBuffer[index]

                self.set_edit_text(new_text)

            return


        return super(consoleEdit, self).keypress(size, key)


class ScreepsConsoleMonitor:

    proc = False

    def __init__(self, widget, walker, loop):
        self.widget = widget
        self.walker = walker
        self.loop = loop
        self.getProcess()
        atexit.register(self.__del__)

    def getProcess(self):
        if self.proc:
            return self.proc
        console_path = os.path.join(os.path.dirname(sys.argv[0]), 'console.py ')
        write_fd = self.loop.watch_pipe(self.onUpdate)
        self.proc = subprocess.Popen(
            [console_path + ' json'],
            stdout=write_fd,
            preexec_fn=os.setsid,
            close_fds=True,
            shell=True)
        return self.proc

    def onUpdate(self, data):

        # If we lose the connection to the remote system close the console.
        if data.startswith('### closed ###'):
            self.proc = False
            self.getProcess()
            lostprocess_message = 'reconnecting to server . . .'
            self.walker.append(urwid.Text(('logged_response', lostprocess_message)))
            self.widget.set_focus(len(self.walker)-1)
            return

        data_lines = data.rstrip().split('\n')
        for line_json in data_lines:
            try:
                line = json.loads(line_json.strip())
                log_type = outputparser.getType(line)

                if log_type == 'result':
                    formatting = 'logged_response'
                elif log_type == 'highlight':
                    formatting = 'highlight'
                elif log_type == 'error':
                    formatting = 'error'
                else:
                    severity = outputparser.getSeverity(line)
                    if not severity or severity > 5 or severity < 0:
                        severity = 2
                    formatting = 'severity' + str(severity)

                line = line.replace('&#09;', " ")
                line = outputparser.clearTags(line)
                self.walker.append(urwid.Text((formatting, line)))
                self.widget.autoscroll()
            except:
                ''

    def __del__(self):
        if self.proc:
            os.killpg(os.getpgid(self.proc.pid), signal.SIGTERM)


if __name__ == "__main__":
    ScreepsInteractiveConsole()
