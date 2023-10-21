from ... import *
from . import RadioSX1276Applet


class RadioSX1276AppletTestCase(GlasgowAppletTestCase, applet=RadioSX1276Applet):
    @synthesis_test
    def test_build(self):
        self.assertBuilds()
