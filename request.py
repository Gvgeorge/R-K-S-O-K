from exceptions import NameIsTooLongError, CanNotParseRequestError, \
    InvalidMethodError, InvalidProtocolError
from conf import RequestVerb, PROTOCOL


class Request:
    '''Class for managing requests sent to RKSOK server'''
    def __init__(self, raw_request: str) -> None:
        self._raw_request = raw_request
        self._method = None
        self._name = None
        self._protocol = None
        self._body = None
        self.parse_request()

    @property
    def raw_request(self):
        return self._raw_request

    @property
    def name(self):
        return self._name

    @property
    def protocol(self):
        return self._protocol

    @property
    def body(self):
        return self._body

    @property
    def method(self):
        return self._method

    def parse_request(self) -> None:
        '''
        Parses incoming request into:
        _method: str
        _name: str
        _protocol: str
        _body: list of strings

        If any of parsed variables do not meet the
        standarts of RKSOK protocol an appropriate exception is raised
        '''

        request = self._raw_request

        if not request.endswith('\r\n'):
            raise CanNotParseRequestError

        request_lines = request.split('\n')
        first_line_words = request_lines[0].split()
        if len(first_line_words) <= 2:
            raise CanNotParseRequestError

        self._method = first_line_words[0]
        self._name = ' '.join(first_line_words[1:-1])
        self._protocol = first_line_words[-1]

        valid_verbs = [RequestVerb.GET, RequestVerb.DELETE, RequestVerb.WRITE]
        if self.method not in valid_verbs:
            raise InvalidMethodError

        if len(self._name) > 30:
            raise NameIsTooLongError

        if self._protocol != PROTOCOL:
            raise InvalidProtocolError

        if self._method == RequestVerb.WRITE:
            self._body = [line.strip() for line in request_lines
                          if line.strip()][1:]

    def __str__(self):
        return f'Request object. Method: {self._method} \
            Name: {self._name}, Protocol: {self._protocol}, Body: {self._body}'

    def __repr__(self):
        return f'Request object. Method: {self._method}, \
            Name: {self._name}, Protocol: {self._protocol}, Body: {self._body}'
