import sys
import platform
from distutils import log
from distutils.core import setup
from distutils.version import StrictVersion


requires = ["twisted", "cyclone", "txAMQP"]


try:
    # to avoid installation problems on centos 5
    # which has no distributions for OpenSSL 0.9.8f
    distname, version, _id = platform.linux_distribution()
    if distname == "CentOS" and StrictVersion(version) < StrictVersion('6.0'):
        requires.insert(0, "pyopenssl==0.12")
except:
    pass


# PyPy and setuptools don't get along too well, yet.
if sys.subversion[0].lower().startswith('pypy'):
    from distutils.core import setup
    extra = dict(requires=requires)
else:
    from setuptools import setup
    extra = dict(install_requires=requires)


setup(
    name="cyclone-sse",
    version="0.7.3",
    author="Alexandr Emelin",
    author_email="frvzmb@gmail.com",
    url="https://github.com/FZambia/cyclone-sse",
    license="http://www.apache.org/licenses/LICENSE-2.0",
    description="EventSource (SSE, Server-Sent-Events) broadcasting server with channel support, Last-Event-Id etc, based on top of cyclone web server",
    keywords="python non-blocking twisted cyclone sse eventsource broadcast http redis amqp rabbitmq",
    packages=["cyclone_sse", "twisted.plugins"],
    #package_data={"twisted": ["plugins/cyclonesse_plugin.py"]},
    **extra
)

# Make Twisted regenerate the dropin.cache, if possible.  This is necessary
# because in a site-wide install, dropin.cache cannot be rewritten by
# normal users.
try:
    from twisted.plugin import IPlugin, getPlugins
except ImportError:
    pass
else:
    list(getPlugins(IPlugin))
