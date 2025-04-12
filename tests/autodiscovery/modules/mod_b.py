from tests.autodiscovery.modules.mod_a import Test


class Other(Test):
    abstract = False


class EvenOther:
    pass


other_instance = Other()
even_other = EvenOther()
