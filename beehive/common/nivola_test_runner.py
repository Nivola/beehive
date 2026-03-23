# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte


from datetime import datetime
from threading import Thread
from time import sleep
from unittest import TextTestResult, TextTestRunner

from beehive3_cli.core.util import rotating_bar


class NivolaTestResult(TextTestResult):
    time_start = None
    thread_progress = None
    stop_threads = False

    def diff_datetime(self):
        end = datetime.now()
        if self.time_start is None:
            self.time_start= datetime.now()
        delta = end - self.time_start
        sec = delta.total_seconds()
        return round(sec, 2)
    
    def print_time_elapsed(self):
        if self.thread_progress:
            self.stop_threads = True
            self.thread_progress.join()

        sec = self.diff_datetime()
        if sec < 60:
            diff = f"{sec:.2f}"
            diff = diff.rjust(7, " ")
            str_time = "(%s sec) " % diff
        else:
            sec = int(sec)
            min = sec / 60
            min = int(min)
            sec = sec % 60
            diff = f"{min}:{sec:02}"
            diff = diff.rjust(7, " ")
            str_time = "(%s min) " % diff
        
        str_time = str_time.ljust(13)
        self.stream.write(str_time)

    def getDescription(self, test):
        from unittest import TestCase
        restCase: TestCase = test
        # return str(test.).ljust(120, ".")
        if hasattr(test, "_testMethodName"):
            descr = "%s" % test._testMethodName
        else:
            descr = str(test)
        return descr.ljust(55, " ")
    
    def progress(self):
        # out = args[0]
        self.stop_threads = False
        bar = rotating_bar()
        while True:
            from sys import stdout
            stdout.write(next(bar))
            stdout.flush()
            sleep(0.09)

            if self.stop_threads:
                # self.stream.write("aaa stop")
                break

    def startTest(self, test):
        self.time_start = datetime.now()
        super(TextTestResult, self).startTest(test)
        if self.showAll:
            self.stream.write(self.getDescription(test))
            # self.stream.write(" ... ")
            self.stream.flush()

            self.thread_progress = Thread(target = self.progress)
            self.thread_progress.start()

    def addSuccess(self, test):
        self.print_time_elapsed()
        super().addSuccess(test)

    def addError(self, test, err):
        self.print_time_elapsed()
        super().addError(test, err)

    def addFailure(self, test, err):
        self.print_time_elapsed()
        super().addFailure(test, err)

    def addSkip(self, test, reason):
        self.print_time_elapsed()
        super().addSkip(test, reason)

    def addExpectedFailure(self, test, err):
        self.print_time_elapsed()
        super().addExpectedFailure(test, err)

    def addUnexpectedSuccess(self, test):
        self.print_time_elapsed()
        super().addUnexpectedSuccess(test)


class NivolaTestRunner(TextTestRunner):
    resultclass = NivolaTestResult


