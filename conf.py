from enum import Enum
from loguru import logger


PROTOCOL = "РКСОК/1.0"
ENCODING = "UTF-8"
PHONEBOOKFILESPATH = 'phonebook'


logger.add('RKSOK_logs.log',
           format='{time}, {level}, {message}',
           level='INFO',
           enqueue=True, rotation='1 week', compression='zip')


class RequestVerb(str, Enum):
    """Verbs specified in RKSOK specs for requests"""
    GET = "ОТДОВАЙ"
    DELETE = "УДОЛИ"
    WRITE = "ЗОПИШИ"
    CHECK = "АМОЖНА?"


class ResponseStatus(str, Enum):
    """Response statuses specified in RKSOK specs for responses"""
    OK = "НОРМАЛДЫКС"
    NOTFOUND = "НИНАШОЛ"
    APPROVED = "МОЖНА"
    NOT_APPROVED = "НИЛЬЗЯ"
    INCORRECT_REQUEST = "НИПОНЯЛ"


'''Information about regulatory agent for RKSOK protocol'''
REG_HOST = 'vragi-vezde.to.digital'
REG_PORT = 51624
REG_PREFIX = 'АМОЖНА? РКСОК/1.0\r\n'


'''Server configuration'''
HOST = '0.0.0.0'
PORT = 8888
FOLDERPATH = 'phonebook'
