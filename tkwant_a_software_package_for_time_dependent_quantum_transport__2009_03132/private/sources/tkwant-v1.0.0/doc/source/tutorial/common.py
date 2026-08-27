# put the just-built tkwant into the path
import sys
from distutils.util import get_platform
sys.path.insert(0, "../../../build/lib.{0}-{1}.{2}"
                .format(get_platform(), *sys.version_info[:2]))
