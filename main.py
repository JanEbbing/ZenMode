#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import psutil
import sys
import time
from threading import Thread, Lock
from PyQt5.QtCore import QTime
from PyQt5.QtWidgets import *

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
BREAK_TIME = 5 # Execute every x seconds
lock = Lock()

def schedule_from_widget(checkboxes, starting_times, ending_times):
    result = Schedule()
    for i, checkbox in enumerate(checkboxes):
        if checkbox.checkState():
            result.days.append(checkbox.text())
            result.starting_times.append(starting_times[i])
            result.ending_times.append(ending_times[i])
    return result

class Schedule:
    def __init__(self):
        self.days = []
        self.starting_times = []
        self.ending_times = []

    def is_active(self):
        now = datetime.datetime.now()
        cur_weekday = DAYS[now.weekday()]
        now = QTime(now.hour, now.minute)
        index = 0
        for day in self.days:
            if day == cur_weekday:
                break
            index += 1
        starting_time = self.starting_times[index].time()
        ending_time = self.ending_times[index].time()
        if cur_weekday in self.days and starting_time.secsTo(now) >= 0 >= ending_time.secsTo(now):
            return True
        return False


class ProcessKillerThread(Thread):
    def __init__(self, schedule = Schedule(), blocked_apps = set()):
        Thread.__init__(self)
        self.schedule = schedule
        self.blocked_apps = blocked_apps
        self.finish = False

    def run(self):
        while not self.finish:
            lock.acquire()
            if not self.schedule.is_active():
                lock.release()
                time.sleep(BREAK_TIME)
            else:
                for proc in psutil.process_iter():
                    try:
                        pinfo = proc.as_dict(attrs=['cmdline', 'name'])
                        print("Checking process with name %s and cmdline %s" % (pinfo['name'], pinfo['cmdline']))
                    except psutil.NoSuchProcess:
                        pass
                    else:
                        for forbidden_app in self.blocked_apps:
                            if forbidden_app in pinfo['cmdline']:
                                proc.kill()
                                break
                lock.release()
                time.sleep(BREAK_TIME)

class App(QWidget):

    def __init__(self):
        super().__init__()
        self.title = 'Zen Mode'
        self.left = 10
        self.top = 10
        self.width = 640
        self.height = 480
        self.blocked_apps = set()
        self.layout = QVBoxLayout()
        self.list_widget = QListWidget()
        self.list_widget.show()
        self.layout.addWidget(QLabel("Blocked Applications:"))
        self.layout.addWidget(self.list_widget)
        self.schedule = Schedule()
        self.pkill_thread = None
        self.set_active_button = None
        self.initUI()

    def initUI(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        add_app_button = QPushButton('Add application...')
        self.layout.addWidget(add_app_button)
        add_app_button.clicked.connect(self.select_file)

        select_schedule_button = QPushButton('Select block schedule...')
        self.layout.addWidget(select_schedule_button)
        select_schedule_button.clicked.connect(self.select_dates)

        self.set_active_button = QPushButton('Zen mode is currently INACTIVE.')
        self.layout.addWidget(self.set_active_button)
        self.set_active_button.clicked.connect(self.change_active)

        self.setLayout(self.layout)
        self.show()

    def change_active(self):
        if not self.pkill_thread:
            # Make it active
            self.set_active_button.setText('Zen mode is currently ACTIVE.')
            self.pkill_thread = ProcessKillerThread(self.schedule, self.blocked_apps)
            self.pkill_thread.start()
        else:
            # Make it inactive
            self.set_active_button.setText('Zen mode is currently INACTIVE.')
            self.pkill_thread.finish = True
            self.pkill_thread.join()
            self.pkill_thread = None

    def select_file(self):
        app_to_block, _ = QFileDialog.getOpenFileName()
        self.blocked_apps.add(app_to_block)
        self.list_widget.addItem(QListWidgetItem(app_to_block))
        if self.pkill_thread:
            lock.acquire()
            self.pkill_thread.blocked_apps = self.blocked_apps
            lock.release()

    def select_dates(self):
        schedule_widget = QDialog()
        schedule_layout = QVBoxLayout()
        schedule_layout.addWidget(QLabel("Select block schedule..."))
        schedule_layout.addStretch()
        OK_button = QPushButton("OK", schedule_widget)
        cancel_button = QPushButton("Cancel", schedule_widget)
        checkboxes = []
        starting_times = []
        ending_times = []
        for day in DAYS:
            day_layout = QHBoxLayout()
            cur_checkbox = QCheckBox(day)
            day_layout.addWidget(cur_checkbox)
            checkboxes.append(cur_checkbox)
            day_layout.addStretch()

            cur_time_editor = QTimeEdit(QTime(9,0))
            starting_times.append(cur_time_editor)
            day_layout.addWidget(QLabel("From:"))
            day_layout.addWidget(cur_time_editor)

            cur_time_editor = QTimeEdit(QTime(17,0))
            ending_times.append(cur_time_editor)
            day_layout.addWidget(QLabel("To:"))
            day_layout.addWidget(cur_time_editor)
            day_layout.addStretch()
            schedule_layout.addLayout(day_layout)

        def ok():
            schedule = schedule_from_widget(checkboxes, starting_times, ending_times)
            self.schedule = schedule
            if self.pkill_thread:
                lock.acquire()
                self.pkill_thread.schedule = schedule
                lock.release()
            schedule_widget.accept()
        def cancel():
            schedule_widget.reject()
        OK_button.clicked.connect(ok)
        cancel_button.clicked.connect(cancel)

        schedule_layout.addStretch()
        schedule_layout.addWidget(OK_button)
        schedule_layout.addWidget(cancel_button)
        schedule_widget.setLayout(schedule_layout)
        schedule_widget.setModal(True)
        schedule_widget.setWindowTitle("Please select the times at which you want the applications blocked.")
        schedule_widget.show()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App()
    sys.exit(app.exec_())
