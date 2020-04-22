"""Datetime subclass with functionality for writing and reading from dict"""

from datetime import datetime


class JsonDateTime(datetime):
    @property
    def dict_(self):
        """Return self translated to dictionary"""

        return {
            'year': self.year,
            'month': self.month,
            'day': self.day,
            'hour': self.hour,
            'minute': self.minute,
            'second': self.second,
            'microsecond': self.microsecond,
            'tzinfo': self.tzinfo
        }

    @classmethod
    def from_dict(cls, dict_):
        """Alternate constructor that takes dictionary as arg"""

        return cls(
            dict_['year'],
            dict_['month'],
            dict_['day'],
            dict_['hour'],
            dict_['minute'],
            dict_['second'],
            dict_['microsecond'],
            dict_['tzinfo']
        )