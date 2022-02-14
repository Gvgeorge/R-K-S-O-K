class RKSOKException(Exception):
    '''Common class for RKSOK Exceptions'''
    pass


class NameIsTooLongError(RKSOKException):
    '''Error that occurs when the name in the request to RKSOK server
     has more than 30 symbols'''


class CanNotParseRequestError(RKSOKException):
    """Error that occurs when we can not parse some strange
    request to RKSOK server."""
    pass


class UndefinedResponseFromRegAgent(RKSOKException):
    """Error that occurs when we can not
    parse response from Regulatory Agent"""
    pass


class InvalidMethodError(RKSOKException):
    """Error that occurs when we can parse the request
    to RKSOK server, but the method is invalid"""
    pass


class InvalidProtocolError(RKSOKException):
    """Error that occurs when the client attempts
    to use protocol which is not supported by RKSOK server"""
    pass
