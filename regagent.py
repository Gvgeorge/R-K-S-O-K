import asyncio
from conf import logger, REG_PORT, REG_HOST, REG_PREFIX, ResponseStatus
from exceptions import UndefinedResponseFromRegAgent


def prepare_request_to_reg_agent(raw_request: str, prefix: str) -> str:
    return f'{prefix}{raw_request}'


async def ask_permission(raw_request: str,
                         reg_host: str = REG_HOST,
                         reg_port: int = REG_PORT,
                         reg_prefix: str = REG_PREFIX
                         ) -> str:
    '''
    Creates a connection to the regulatory agency
    sends a request and saves a response
    '''
    reg_request = prepare_request_to_reg_agent(
        raw_request, reg_prefix)

    reader, writer = await asyncio.open_connection(
        reg_host, reg_port, limit=float('inf'))

    logger.info(f'Asked for permission from regulatory \
        agency ({reg_host}, {reg_port}): {reg_request!r}')

    writer.write(reg_request.encode())
    await writer.drain()
    reg_response = await reader.readuntil(separator=b'\r\n\r\n')
    reg_response = f'{reg_response.decode()}'
    logger.info(f'Got response from regulatory agent: \
        ({reg_host}, {reg_port}): {reg_request!r}')
    writer.close()
    await writer.wait_closed()
    return reg_response


async def process_permission(reg_agent_response: str,
                             msg_approved: str = ResponseStatus.APPROVED,
                             msg_denied: str = ResponseStatus.NOT_APPROVED
                             ) -> bool:
    '''
    Processes the response from regulatory agency
    '''
    if reg_agent_response.startswith(msg_approved):
        return True
    elif reg_agent_response.startswith(msg_denied):
        return False
    raise UndefinedResponseFromRegAgent
