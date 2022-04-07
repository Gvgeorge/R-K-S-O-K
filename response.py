from conf import logger, RequestVerb, ResponseStatus, PROTOCOL
from regagent import ask_permission, process_permission
from request import Request
from exceptions import RKSOKException
from storage import FilePhoneBook, Storage


class Response:
    '''
    Class for creating a response to the RKSOK request
    Also handles communication with regulatory agency.
    method_map consists of valid RKSOK methods
    Every response object matches a certain request
    '''
    method_map = {RequestVerb.GET: '_make_get',
                  RequestVerb.WRITE: '_make_write',
                  RequestVerb.DELETE: '_make_delete'}

    def __init__(self, raw_request: str) -> None:
        self._request = self.set_request(raw_request)
        self._response = ''

    def set_request(self, raw_request: str) -> Request | None:
        try:
            self._request = Request(raw_request)
        except (RKSOKException):
            logger.exception('An exception was raised \
                             during the parsing of the request',
                             backtrace=False, diagnose=False)
            self._request = None
        return self._request

    async def _make_get(self, storage: Storage) -> str:
        '''
        Prepares a response to a GET ('ОТДОВАЙ') request from RKSOK client
        '''
        try:
            phone = await storage.get(self._request.name)
            self._response = f'{ResponseStatus.OK} ' + \
                f'{PROTOCOL}\r\n{phone.strip()}\r\n\r\n'

        except FileNotFoundError:
            self._response = f'{ResponseStatus.NOTFOUND} {PROTOCOL}\r\n\r\n'
        return self._response

    async def _make_write(self, storage: Storage) -> str:
        '''
        Prepares a response to a WRITE ('ЗОПИШИ') request from RKSOK client
        '''
        await storage.write(self._request.name, self._request.body)
        self._response = f'{ResponseStatus.OK} {PROTOCOL}\r\n\r\n'
        return self._response

    async def _make_delete(self, storage: Storage) -> str:
        '''
        Prepares a response to a DELETE ('УДОЛИ') request from RKSOK client
        '''
        try:
            storage.delete(self._request.name)
            self._response = f'{ResponseStatus.OK} {PROTOCOL}\r\n\r\n'
        except FileNotFoundError:
            self._response = f'{ResponseStatus.NOTFOUND} {PROTOCOL}\r\n\r\n'
        return self._response

    def _make_bad_request(self) -> str:
        '''
        Prepares a response for the RKSOK request we could not handle
        '''
        self._response = f'{ResponseStatus.INCORRECT_REQUEST} ' + \
            f'{PROTOCOL}\r\n\r\n'
        return self._response

    async def make_response(self, storage: FilePhoneBook) -> str:
        '''
        Matches RKSOK request to the appropriate handling method
        '''
        
        if self._request is None:
            return self._make_bad_request()

        reg_agent_response = await ask_permission(self._request.raw_request)

        permission_granted = await process_permission(reg_agent_response)

        if not permission_granted:
            self._response = reg_agent_response
            return self._response
        return await getattr(self, self.method_map[self._request.method],
                             self._make_bad_request)(storage)
