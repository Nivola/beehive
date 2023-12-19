# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

# """Running tests"""

import sys
import time
import warnings

import unittest
from unittest.signals import registerResult

__unittest = True


class _WritelnDecorator(object):
    """Used to decorate file-like objects with a handy 'writeln' method"""

    def __init__(self, stream):
        self.stream = stream

    def __getattr__(self, attr):
        if attr in ("stream", "__getstate__"):
            raise AttributeError(attr)
        return getattr(self.stream, attr)

    def writeln(self, arg=None):
        if arg:
            self.write(arg)
        self.write("\n")  # text-mode streams translate to \r\n if needed


class TestInfo(object):
    desc = None
    esito = None

    def __init__(self):
        pass


class CustomTestResult(unittest.result.TestResult):
    """A test result class that can print formatted text results to a stream.

    Used by CustomTestRunner.
    """

    separator1 = "=" * 70
    separator2 = "-" * 70

    def __init__(
        self,
        stream,
        descriptions: bool,
        verbosity: int,
        report_file: str,
        test_group: str,
        test_filename: str,
    ):
        super(CustomTestResult, self).__init__(stream, descriptions, verbosity)
        self.stream = stream
        self.showAll = verbosity > 1
        self.dots = verbosity == 1
        self.descriptions = descriptions
        self.report_file = report_file
        self.test_group = test_group
        self.test_filename = test_filename
        self.testInfo: TestInfo = TestInfo

    def writeLineToFile(self):
        if self.test_group is None:
            line = "%s - %s - %s" % (
                self.test_filename,
                self.testInfo.desc,
                self.testInfo.esito,
            )
        else:
            line = "%s - %s - %s - %s" % (
                self.test_filename,
                self.test_group,
                self.testInfo.desc,
                self.testInfo.esito,
            )
        # a = append, w = write
        with open(self.report_file, "a") as f:
            f.write(line)
            f.write("\n")

    def getDescription(self, test):
        doc_first_line = test.shortDescription()
        if self.descriptions and doc_first_line:
            return "\n".join((str(test), doc_first_line))
        else:
            return str(test)

    def startTest(self, test):
        super(CustomTestResult, self).startTest(test)
        if self.showAll:
            self.stream.write(self.getDescription(test))
            self.stream.write(" ... ")
            self.stream.flush()

        # get test method name
        test_desc = "%s" % test
        split_test = test_desc.split(" ")
        test_method_name = split_test[0]
        self.testInfo.desc = test_method_name

    def addSuccess(self, test):
        super(CustomTestResult, self).addSuccess(test)
        if self.showAll:
            self.stream.writeln("ok NIVOLA")
        elif self.dots:
            self.stream.write(".")
            self.stream.flush()
        self.testInfo.esito = "ok"
        self.writeLineToFile()

    def addError(self, test, err):
        super(CustomTestResult, self).addError(test, err)
        if self.showAll:
            self.stream.writeln("ERROR")
        elif self.dots:
            self.stream.write("E")
            self.stream.flush()
        self.testInfo.esito = "ERROR"
        self.writeLineToFile()

    def addFailure(self, test, err):
        super(CustomTestResult, self).addFailure(test, err)
        if self.showAll:
            self.stream.writeln("FAIL")
        elif self.dots:
            self.stream.write("F")
            self.stream.flush()
        self.testInfo.esito = "FAIL"
        self.writeLineToFile()

    def addSkip(self, test, reason):
        super(CustomTestResult, self).addSkip(test, reason)
        if self.showAll:
            self.stream.writeln("skipped {0!r}".format(reason))
        elif self.dots:
            self.stream.write("s")
            self.stream.flush()
        self.testInfo.esito = "skip"
        self.writeLineToFile()

    def addExpectedFailure(self, test, err):
        super(CustomTestResult, self).addExpectedFailure(test, err)
        if self.showAll:
            self.stream.writeln("expected failure")
        elif self.dots:
            self.stream.write("x")
            self.stream.flush()
        self.testInfo.esito = "expected failure"
        self.writeLineToFile()

    def addUnexpectedSuccess(self, test):
        super(CustomTestResult, self).addUnexpectedSuccess(test)
        if self.showAll:
            self.stream.writeln("unexpected success")
        elif self.dots:
            self.stream.write("u")
            self.stream.flush()
        self.testInfo.esito = "unexpected success"
        self.writeLineToFile()

    def printErrors(self):
        if self.dots or self.showAll:
            self.stream.writeln()
        self.printErrorList("ERROR", self.errors)
        self.printErrorList("FAIL", self.failures)

    def printErrorList(self, flavour, errors):
        for test, err in errors:
            self.stream.writeln(self.separator1)
            self.stream.writeln("%s: %s" % (flavour, self.getDescription(test)))
            self.stream.writeln(self.separator2)
            self.stream.writeln("%s" % err)

            with open(self.report_file, "a") as f:
                f.write("\n")
                f.write(self.separator1)
                f.write("\n")
                f.write("%s: %s" % (flavour, self.getDescription(test)))
                f.write("\n")
                f.write(self.separator2)
                f.write("\n")
                f.write("%s" % err)
                f.write("\n")


class CustomTestRunner(object):
    """A test runner class that displays results in textual form.

    It prints out the names of tests as they are run, errors as they
    occur, and a summary of the results at the end of the test run.
    """

    resultclass = CustomTestResult
    stream: _WritelnDecorator
    report_file = None
    test_group = None

    def __init__(
        self,
        report_file,
        test_filename,
        stream=None,
        descriptions=True,
        verbosity=1,
        failfast=False,
        buffer=False,
        resultclass=None,
        warnings=None,
        *,
        tb_locals=False,
    ):
        """Construct a CustomTestRunner.

        Subclasses should accept **kwargs to ensure compatibility as the
        interface changes.
        """
        self.report_file = report_file
        self.test_filename = test_filename

        if stream is None:
            stream = sys.stderr
        self.stream: _WritelnDecorator = _WritelnDecorator(stream)

        self.descriptions = descriptions
        self.verbosity = verbosity
        self.failfast = failfast
        self.buffer = buffer
        self.tb_locals = tb_locals
        self.warnings = warnings
        if resultclass is not None:
            self.resultclass = resultclass

    def _makeResult(self):
        return self.resultclass(
            self.stream,
            self.descriptions,
            self.verbosity,
            self.report_file,
            self.test_group,
            self.test_filename,
        )

    def run(self, test):
        "Run the given test case or test suite."
        # result: unittest.result.TestResult = self._makeResult()
        result: CustomTestResult = self._makeResult()
        registerResult(result)

        result.failfast = self.failfast
        result.buffer = self.buffer
        result.tb_locals = self.tb_locals

        with warnings.catch_warnings():
            if self.warnings:
                # if self.warnings is set, use it to filter all the warnings
                warnings.simplefilter(self.warnings)
                # if the filter is 'default' or 'always', special-case the
                # warnings from the deprecated unittest methods to show them
                # no more than once per module, because they can be fairly
                # noisy.  The -Wd and -Wa flags can be used to bypass this
                # only when self.warnings is None.
                if self.warnings in ["default", "always"]:
                    warnings.filterwarnings(
                        "module",
                        category=DeprecationWarning,
                        message=r"Please use assert\w+ instead.",
                    )
            startTime = time.perf_counter()
            startTestRun = getattr(result, "startTestRun", None)
            if startTestRun is not None:
                startTestRun()
            try:
                test(result)
            finally:
                stopTestRun = getattr(result, "stopTestRun", None)
                if stopTestRun is not None:
                    stopTestRun()
            stopTime = time.perf_counter()

        timeTaken = stopTime - startTime
        result.printErrors()
        if hasattr(result, "separator2"):
            self.stream.writeln(result.separator2)

        run = result.testsRun
        self.stream.writeln("Ran %d test%s in %.3fs" % (run, run != 1 and "s" or "", timeTaken))
        self.stream.writeln()

        expectedFails = unexpectedSuccesses = skipped = 0
        try:
            results = map(
                len,
                (result.expectedFailures, result.unexpectedSuccesses, result.skipped),
            )
        except AttributeError:
            pass
        else:
            expectedFails, unexpectedSuccesses, skipped = results

        infos = []
        line = ""
        if not result.wasSuccessful():
            self.stream.write("<<< FAILED >>>")
            failed, errored = len(result.failures), len(result.errors)
            if failed:
                infos.append("failures=%d" % failed)
            if errored:
                infos.append("errors=%d" % errored)
            line = "FAILED - failures: %s - errors: %s" % (failed, errored)
        else:
            self.stream.write("OK")
            line = "OK"

        with open(self.report_file, "a") as f:
            f.write(line)
            f.write("\n")

            separator = "+" * 70
            f.write(separator)
            f.write("\n")

        if skipped:
            infos.append("skipped=%d" % skipped)
        if expectedFails:
            infos.append("expected failures=%d" % expectedFails)
        if unexpectedSuccesses:
            infos.append("unexpected successes=%d" % unexpectedSuccesses)
        if infos:
            self.stream.writeln(" (%s)" % (", ".join(infos),))
        else:
            self.stream.write("\n")
        return result
