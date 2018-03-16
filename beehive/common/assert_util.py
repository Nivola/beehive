from beehive.common.apimanager import ApiManagerError, ApiManagerWarning

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
        return result[:AssertUtil.MAX_LENGTH] + ' [truncated]...'
    
    @staticmethod
    def _formatMessage( msg, standardMsg):
        """Honour the longMessage attribute when generating failure messages.
        If longMessage is False this means:
        * Use only an explicit message if it is provided
        * Otherwise use the standard message for the assert

        If longMessage is True:
        * Use the standard message
        * If an explicit message is provided, plus ' : ' and the explicit message
        """
        
        if msg is None:
            return standardMsg
        try:
            # don't switch to '{}' formatting in Python 2.X
            # it changes the way unicode input is handled
            return '%s : %s' % (standardMsg, msg)
        except UnicodeDecodeError:
            return  '%s : %s' % (AssertUtil.safe_repr(standardMsg), AssertUtil.safe_repr(msg))
    
    @staticmethod
    def fail(msg=None):
        """Fail immediately, with the given message."""
        raise ApiManagerError(msg)
    
    @staticmethod
    def assertIsNone(obj, msg=None):
        """Same as self.assertTrue(obj is None), with a nicer default message."""
        if obj is not None:
            standardMsg = '%s is not None' % (AssertUtil.safe_repr(obj),)
            AssertUtil.fail(AssertUtil._formatMessage(msg, standardMsg))
    
    @staticmethod
    def assertIsNotNone(obj, msg=None):
        """Included for symmetry with assertIsNone."""
        if obj is None:
            standardMsg = 'unexpectedly None'
            AssertUtil.fail(AssertUtil._formatMessage(msg, standardMsg))
    
