import sys

requires = ["twisted", "cyclone"]

from distutils import log
from distutils.core import setup

# PyPy and setuptools don't get along too well, yet.
if sys.subversion[0].lower().startswith('pypy'):
    from distutils.core import setup
    extra = dict(requires=requires)
else:
    from setuptools import setup
    extra = dict(install_requires=requires)


setup(
    name="cyclone_sse",
    version="0.3",
    author="Alexandr Emelin",
    author_email="frvzmb@gmail.com",
    url=None,
    license="http://www.apache.org/licenses/LICENSE-2.0",
    description="EventSource (SSE, Server-Sent-Events) broadcasting server with channel support, last-event-id etc, based on top of cyclone web server",
    keywords="python non-blocking twisted cyclone sse eventsource broadcast http redis amqp rabbitmq",
    packages=["cyclone_sse", "twisted.plugins"],
    package_data={"twisted": ["plugins/sse_plugin.py"]},
    **extra
)


try:
    from twisted.plugin import IPlugin, getPlugins
    list(getPlugins(IPlugin))
except:
    log.warn("*** Failed to update Twisted plugin cache. ***")
