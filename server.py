import asyncio
import sys
from storage import FilePhoneBook, Storage
from conf import logger, HOST, PORT, FOLDERPATH
from response import Response


class Server:
    def __init__(self, addr: str, port: int, phonebook: Storage):
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
        try:
            raw_request = data.decode()

            addr = writer.get_extra_info('peername')
            logger.info('Received incoming request' +
                        f'from {addr}: {raw_request!r}')

            response = await Response(raw_request).make_response(
                self._phonebook)
        except UnicodeDecodeError:
            response = await Response(raw_request)._make_bad_request(
                self._phonebook)
            logger.info('UnicodeDecodeError while parsing' +
                        f'request from {addr}: {raw_request!r}')

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
    filestorage = FilePhoneBook(FOLDERPATH)
    asyncio.run(Server(HOST, PORT, filestorage).run())
