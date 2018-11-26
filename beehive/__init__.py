__version__ = '1.0.0'

import os.path
version_file = os.path.join(os.path.abspath(__file__).rstrip(u'__init__.py'), u'./VERSION')
if os.path.isfile(version_file):
    with open(version_file) as version_file:
        __version__ = '%s-%s' % (__version__, version_file.read().strip()[:10])
