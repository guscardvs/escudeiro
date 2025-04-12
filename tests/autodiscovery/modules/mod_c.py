from tests.autodiscovery.modules.mod_a import Test
from tests.autodiscovery.modules.mod_b import EvenOther, Other


class Another(Test, EvenOther):
    pass


class Second(Other):
    name = "other"


class Strange:
    pass


another = Another()
second = Second()


a, b, c = Strange(), Second(), Another()
