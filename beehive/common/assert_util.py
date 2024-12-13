# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from beehive.common.apimanager import ApiManagerError


class AssertUtil(object):
    MAX_LENGTH = 80

    @staticmethod
    def safe_repr(obj, short=False):
        try:
            result = repr(obj)
        except Exception:
            result = object.__repr__(obj)
        if not short or len(result) < AssertUtil.MAX_LENGTH:
            return result
        return result[: AssertUtil.MAX_LENGTH] + " [truncated]..."

    @staticmethod
    def _format_message(msg, standard_msg):
        """Format message

        :param msg: error message
        :param standard_msg: standard error message
        :return:
        """
        if msg is None:
            return standard_msg
        try:
            # don't switch to '{}' formatting in Python 2.X
            # it changes the way unicode input is handled
            return "%s : %s" % (standard_msg, msg)
        except UnicodeDecodeError:
            return "%s : %s" % (
                AssertUtil.safe_repr(standard_msg),
                AssertUtil.safe_repr(msg),
            )

    @staticmethod
    def fail(msg=None):
        """Fail immediately, with the given message

        :param msg: error message
        :return:
        """
        raise ApiManagerError(msg)

    @staticmethod
    def assert_is_none(obj, msg=None):
        """Same as self.assertTrue(obj is None), with a nicer default message

        :param obj: obj to check
        :param msg: error message
        :return:
        """
        if obj is not None:
            standard_msg = "%s is not None" % (AssertUtil.safe_repr(obj),)
            AssertUtil.fail(AssertUtil._format_message(msg, standard_msg))

    @staticmethod
    def assert_is_not_none(obj, msg=None):
        """Included for symmetry with assert_is_none

        :param obj: obj to check
        :param msg: error message
        :return:
        """
        if obj is None:
            standard_msg = "unexpectedly None"
            AssertUtil.fail(AssertUtil._format_message(msg, standard_msg))
