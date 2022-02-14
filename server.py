import aiofiles
import asyncio
import os
import sys
from conf import logger, RequestVerb, ResponseStatus, RegulatorInfo, \
    PROTOCOL, PHONEBOOKFILESPATH
from exceptions import RKSOKException, NameIsTooLongError, \
    CanNotParseRequestError, UndefinedResponseFromRegAgent, \
    InvalidMethodError, InvalidProtocolError


class FilePhoneBook:
    def __init__(self, folder_path):
        self.folder_path = folder_path
        if not os.path.exists(self.folder_path):
            os.makedirs(self.folder_path)

    async def get(self, name):
        file_path = os.path.join(self.folder_path, name)
        async with aiofiles.open(file_path, mode='r') as f:
            contents = await f.readlines()
        return '\r\n'.join(line.strip() for line in contents)

    async def write(self, name, phones):
        file_path = os.path.join(self.folder_path, name)
        async with aiofiles.open(file_path, mode='w') as f:
            phones = [phone.strip() for phone in phones if phone.strip()]
            await f.writelines([f'{phone}\r\n' for phone in phones])

    def delete(self, name):
        os.remove(os.path.join(self.folder_path, name))


class RequestHandler:
    '''Class for managing requests sent to RKSOK server'''
    def __init__(self, raw_request: str) -> None:
        self._raw_request = raw_request
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

    def parse_request(self, request: str = None) -> None:
        '''
        Parses incoming request into:
        _method: str
        _name: str
        _protocol: str
        _body: list of strings

        If any of parsed variables do not meet the
        standarts of RKSOK protocol an appropriate exception is raised
        '''
        if request is None:
            request = self._raw_request

        if not request.endswith('\r\n'):
            raise CanNotParseRequestError

        request_lines = request.split('\n')
        first_line = request_lines[0].split()
        if len(first_line) <= 2:
            raise CanNotParseRequestError

        self._method = first_line[0]
        self._name = ' '.join(first_line[1:-1])
        self._protocol = first_line[-1]

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
        return f'RequestHandler object. Method: {self._method} \
            Name: {self._name}, Protocol: {self._protocol}, Body: {self._body}'

    def __repr__(self):
        return f'RequestHandler object. Method: {self._method}, \
            Name: {self._name}, Protocol: {self._protocol}, Body: {self._body}'


class Response:
    '''
    Class for creating a response to the RKSOK request
    Also handles communication with regulatory agency.
    method_map consists of valid RKSOK methods
    Evert response object matches a certain request
    '''
    method_map = {RequestVerb.GET: '_make_get',
                  RequestVerb.WRITE: '_make_write',
                  RequestVerb.DELETE: '_make_delete'}

    def __init__(self, raw_request: str) -> None:
        self._request = self.set_request(raw_request)
        self._response = ''

    def set_request(self, raw_request: str) -> RequestHandler | None:
        try:
            self._request = RequestHandler(raw_request)
        except (RKSOKException):
            logger.exception('An exception was raised \
                             during the parsing of the request',
                             backtrace=False, diagnose=False)
            self._request = None
        return self._request

    @staticmethod
    def prepare_request_to_reg_agent(raw_request: str, prefix: str) -> str:
        return f'{prefix}{raw_request}'

    async def ask_permission(self, reg_request: str,
                             host: str, port: int) -> str:
        '''
        Creates a connection to the regulatory agency
        sends a request and saves a response
        '''
        reader, writer = await asyncio.open_connection(
            host, port, limit=float('inf'))

        logger.info(f'Asked for permission from regulatory \
            agency ({host}, {port}): {reg_request!r}')

        writer.write(reg_request.encode())
        await writer.drain()
        reg_response = await reader.readuntil(separator=b'\r\n\r\n')
        reg_response = f'{reg_response.decode()}'
        logger.info(f'Got response from regulatory agent: \
            ({host}, {port}): {reg_response!r}')
        writer.close()
        await writer.wait_closed()
        return reg_response

    async def permission_granted(self,
                                 prefix: str = RegulatorInfo.PREFIX,
                                 reg_host: str = RegulatorInfo.HOST,
                                 reg_port: int = RegulatorInfo.PORT,
                                 msg_approved: str = ResponseStatus.APPROVED,
                                 msg_denied: str = ResponseStatus.NOT_APPROVED
                                 ) -> bool:
        '''
        Processes the response from regulatory agency
        '''
        self.reg_agent_response = await self.ask_permission(
            self.prepare_request_to_reg_agent(self._request._raw_request,
                                              prefix), reg_host, reg_port)

        if self.reg_agent_response.startswith(msg_approved):
            return True
        elif self.reg_agent_response.startswith(msg_denied):
            return False
        raise UndefinedResponseFromRegAgent

    async def _make_get(self, storage: FilePhoneBook) -> str:
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

    async def _make_write(self, storage: FilePhoneBook) -> str:
        '''
        Prepares a response to a WRITE ('ЗОПИШИ') request from RKSOK client
        '''
        await storage.write(self._request.name, self._request.body)
        self._response = f'{ResponseStatus.OK} {PROTOCOL}\r\n\r\n'
        return self._response

    async def _make_delete(self, storage: FilePhoneBook) -> str:
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

    async def make_response(self, storage: FilePhoneBook,
                            request: RequestHandler = None) -> str:
        '''
        Matches RKSOK request to the appropriate handling method
        '''
        if request is None:
            request = self._request

        if request is None:
            return self._make_bad_request()

        if not await self.permission_granted():
            self._response = self.reg_agent_response
            return self._response
        return await getattr(self, self.method_map[self._request.method],
                             self._make_bad_request)(storage)


class Server:
    def __init__(self, addr: str, port: int, phonebook: FilePhoneBook):
        self._addr = addr
        self._port = port
        self._phonebook = phonebook

    async def handle_request(self,
                             reader: asyncio.StreamReader,
                             writer: asyncio.StreamWriter) -> str:
        '''
        Handles the connection from the client.
        Receives request and sends the response.
        '''
        logger.info('connection opened')
        data = await reader.readuntil(separator=b'\r\n\r\n')
        raw_request = data.decode()
        addr = writer.get_extra_info('peername')
        logger.info(f'Received incoming request from {addr}: {raw_request!r}')

        response = await Response(raw_request).make_response(self._phonebook)
        logger.info(f'Sent the following response to {addr}: {response!r}')

        writer.write(response.encode())
        await writer.drain()
        writer.close()
        logger.info('connection closed')
        return response

    @logger.catch
    async def run(self) -> None:
        '''
        Runs the server!
        '''
        server = await asyncio.start_server(
            self.handle_request, self._addr, self._port, limit=float('inf'))

        addrs = ', '.join(str(sock.getsockname()) for sock in server.sockets)
        print(f'Serving on {addrs}')

        async with server:
            try:
                await server.serve_forever()
            except KeyboardInterrupt:
                print('interrupted')
                sys.exit()


if __name__ == '__main__':
    filestorage = FilePhoneBook(PHONEBOOKFILESPATH)
    asyncio.run(Server('0.0.0.0', 8888, filestorage).run())
