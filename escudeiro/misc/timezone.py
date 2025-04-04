import datetime

_DEFAULT_TZ = datetime.UTC


class TimeZone:
    def __init__(self, tz: datetime.tzinfo) -> None:
        self._tz: datetime.tzinfo = tz
        self._retrieved: bool = False

    def now(self) -> datetime.datetime:
        self._retrieved = True
        return datetime.datetime.now(self._tz)

    def today(self) -> datetime.date:
        return self.now().date()

    def set_tz(self, tz: datetime.tzinfo) -> None:
        if self._retrieved:
            raise ValueError("Timezone can only be set once")
        self._tz = tz


def now(tz: datetime.tzinfo = _DEFAULT_TZ) -> datetime.datetime:
    return TimeZone(tz).now()


def today(tz: datetime.tzinfo = _DEFAULT_TZ) -> datetime.date:
    return TimeZone(tz).today()
