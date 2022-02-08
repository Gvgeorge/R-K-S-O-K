import asyncio
from importlib.metadata import files
import aiofiles
import os
import sys
from typing import Optional
from utils import RequestVerb, ResponseStatus, RegulatorInfo, PROTOCOL, ENCODING, PHONEBOOKFILESPATH

test_message = '''ЗОПИШИ Путин РКСОК/1.0\r
89112345678\r\n\r\n'''

test_message_receive = '''ОТДОВАЙ Путин РКСОК/1.0\r\n\r\n'''

test_message_delete = '''УДОЛИ Путин РКСОК/1.0\r\n\r\n'''


phonebook = {'Ваня Хмурый': '8931987654',
             'Лена Веселая': '123456789'   
}

class NameIsTooLongError(Exception):
    '''Error that occurs when the name in the request to RKSOK server
     has more than 30 symbols'''

class CanNotParseRequestError(Exception):
    """Error that occurs when we can not parse some strange
    request to RKSOK server."""
    pass

class UndefinedResponseFromRegAgent(Exception):
    """Error that occurs when we can not parse response from Regulatory Agent"""
    pass

class InvalidMethodError(Exception):
    """Error that occurs when we can parse the request to RKSOK server, but the method is invalid"""
    pass


class RequestHandler:
    '''Class for managing requests sent to RKSOK server'''
    def __init__(self, raw_request: str):
        self._raw_request = raw_request
        self._body = None
        self._name = None
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
    
    def parse_request(self):
        request_lines = self.raw_request.split('\n')
        first_line = request_lines[0].split()
        if len(first_line) <= 2:
            raise CanNotParseRequestError
        self._method = first_line[0]
        self._name = ' '.join(first_line[1:-1])
        self._protocol = first_line[-1]
        
        if self.method not in [RequestVerb.GET, RequestVerb.DELETE, RequestVerb.WRITE]:
            raise InvalidMethodError
        
        if len(self._name) > 30:
            raise NameIsTooLongError
        
        if self._method == RequestVerb.WRITE:
            self._body = [line.strip() for line in request_lines if line.strip()][1:]
        
    def __str__(self):
        return f'RequestHandler object. Method: {self._method}, Name: {self._name}, Protocol: {self._protocol}, Body: {self._body}'
    
    def __repr__(self):
        return f'RequestHandler object. Method: {self._method}, Name: {self._name}, Protocol: {self._protocol}, Body: {self._body}'


class Response:  
    method_map = {RequestVerb.GET: '_make_get', RequestVerb.WRITE: '_make_write', RequestVerb.DELETE: '_make_delete'}  
    
    def __init__(self, raw_request: str):
        self._request = self.set_request(raw_request)
        self._response = ''

    def set_request(self, raw_request: str):
        try:
            self._request = RequestHandler(raw_request)
        except (InvalidMethodError, NameIsTooLongError, CanNotParseRequestError):
            self._request = None
        return self._request
    
    @staticmethod
    def prepare_request_to_reg_agent(raw_request: str, prefix: str) -> str:
        return f'{prefix}{raw_request}'

    async def ask_permission(self, message: str, host: str, port: int) -> str:
        reader, writer = await asyncio.open_connection(
            host, port)

        print(f'Send: {message!r}')
        writer.write(message.encode())
        await writer.drain()
        data = await reader.read(100)
        data = f'{data.decode()}'
        #print(f'Received: {data}')
        writer.close()
        await writer.wait_closed()
        return data

    @property    
    async def permission_granted(self):
        if self._request is not None:
            self.reg_agent_response =  await self.ask_permission(
                self.prepare_request_to_reg_agent(self._request._raw_request, RegulatorInfo.PREFIX), 
                    RegulatorInfo.HOST, RegulatorInfo.PORT)

        if self.reg_agent_response.startswith(ResponseStatus.APPROVED):
            return True
        elif self.reg_agent_response.startswith(ResponseStatus.NOT_APPROVED):
            return False
        raise UndefinedResponseFromRegAgent
       
    async def _make_get(self, storage):
        try:
            phone = await storage.get(self._request.name)
            self._response = f'{ResponseStatus.OK} {PROTOCOL}\r\n{phone}\r\n\r\n'
            
        except FileNotFoundError:
            self._response = f'{ResponseStatus.NOTFOUND} {PROTOCOL}\r\n\r\n'
        return self._response
    
    async def _make_write(self, storage):
        phone = await storage.write(self._request.name, self._request.body[0]) # добавить логику для нескольких телефонов
        self._response = f'{ResponseStatus.OK} {PROTOCOL}\r\n\r\n'            
        return self._response
    
    async def _make_delete(self, storage):
        try:
            phone = storage.delete(self._request.name)
            self._response = f'{ResponseStatus.OK} {PROTOCOL}\r\n\r\n'            
        except FileNotFoundError:
            self._response = f'{ResponseStatus.NOTFOUND} {PROTOCOL}\r\n\r\n'
        return self._response
    
    def _make_bad_request(self):
        self._response = f'{ResponseStatus.INCORRECT_REQUEST} {PROTOCOL}\r\n\r\n'
        return self._response
        
    async def make_response(self, storage):
        if self._request is None:
            return self._make_bad_request()
        if not await self.permission_granted:
            self._response = self.reg_agent_response
            return self._response
        return await getattr(self, self.method_map[self._request.method], self._make_bad_request)(storage)
            
class FilePhoneBook:
    def __init__(self, folder_path):
        self.folder_path = folder_path
        if not os.path.exists(self.folder_path):
            os.makedirs(self.folder_path)
    
    async def get(self, name):
        async with aiofiles.open(os.path.join(self.folder_path, name), mode='r') as f:
            contents = await f.read()
        return contents
    
    async def write(self, name, phone):
        '''Добавить когда уже существует телефон?'''
        async with aiofiles.open(os.path.join(self.folder_path, name), mode='w') as f:
            await f.write(phone)
            
    def delete(self, name):
        os.remove(os.path.join(self.folder_path, name))
    
    
        

class Server:
    def __init__(self, addr: str, port: int, phonebook: dict):
        self._addr = addr
        self._port = port
        self._phonebook = phonebook
    
    
    async def handle_request(self, reader, writer):
        data = await reader.read(100)
        raw_request = data.decode()
        print('RAW:', raw_request)
        addr = writer.get_extra_info('peername')

        print(f"Received {raw_request} from {addr}")
        
        response = await Response(raw_request).make_response(self._phonebook)
        print(f"Send: {response!r}")

        writer.write(response.encode())
        await writer.drain()

        print("Close the connection")
        writer.close()
        return response

    async def run(self):
        server = await asyncio.start_server(
            self.handle_request, self._addr, self._port)

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
   # print(asyncio.run(filestorage.write('Kenny', '012301023012301')))
    asyncio.run(Server('0.0.0.0', 8888, filestorage).run())

    