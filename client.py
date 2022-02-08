from utils import RequestVerb, ResponseStatus, PROTOCOL, ENCODING
import socket
import sys
from typing import Optional


class NotSpecifiedIPOrPortError(Exception):
    """Error that occurs when there is not Server or Port
    specified in command-line arguments."""
    pass


class CanNotParseResponseError(Exception):
    """Error that occurs when we can not parse some strange
    response from RKSOK server."""
    pass



HUMAN_READABLE_ANSWERS = {
    RequestVerb.GET: {
        ResponseStatus.OK: "Телефон человека {name} найден: {payload}",
        ResponseStatus.NOTFOUND: "Телефон человека {name} не найден "
            "на сервере РКСОК",
        ResponseStatus.NOT_APPROVED: "Органы проверки запретили тебе искать "
            "телефон человека {name} {payload}",
        ResponseStatus.INCORRECT_REQUEST: "Сервер не смог понять запрос на "
            "получение данных, который мы отправили."
    },
    RequestVerb.WRITE: {
        ResponseStatus.OK: "Телефон человека {name} записан",
        ResponseStatus.NOT_APPROVED: "Органы проверки запретили тебе "
            "сохранять телефон человека {name} {payload}",
        ResponseStatus.INCORRECT_REQUEST: "Сервер не смог понять запрос "
            "на запись данных, который мы отправили"
    },
    RequestVerb.DELETE: {
        ResponseStatus.OK: "Телефон человека {name} удалён",
        ResponseStatus.NOTFOUND: "Телефон человека {name} не найден на "
            "сервере РКСОК",
        ResponseStatus.NOT_APPROVED: "Органы проверки запретили тебе удалять "
            "телефон человека {name} {payload}",
        ResponseStatus.INCORRECT_REQUEST: "Сервер не смог понять запрос "
            "на удаление данных, который мы отправили"
    }
}


MODE_TO_VERB = {
    1: RequestVerb.GET,
    2: RequestVerb.WRITE,
    3: RequestVerb.DELETE
}


class RKSOKPhoneBook:
    """Phonebook working with RKSOK server."""

    def __init__(self, server: str, port: int):
        self._server, self._port = server, port
        self._conn = None
        self._name, self._phone, self._verb = None, None, None
        self._raw_request, self._raw_response = None, None

    def set_name(self, name: str) -> None:
        self._name = name

    def set_phone(self, phone: str) -> None:
        self._phone = phone

    def set_verb(self, verb: RequestVerb) -> None:
        self._verb = verb

    def process(self):
        """Processes communication with RKSOK server — sends request,
        parses response"""
        raw_response = self._send_request()
        human_response = self._parse_response(raw_response)
        return human_response

    def get_raw_request(self) -> Optional[str]:
        """Returns last request in raw string format"""
        return self._raw_request

    def get_raw_response(self) -> Optional[str]:
        """Returns last response in raw string format"""
        return self._raw_response

    def _send_request(self) -> str:
        """Sends request to RKSOK server and return response as string."""
        request_body = self._get_request_body()
        self._raw_request = request_body.decode(ENCODING)
        if not self._conn:
            self._conn = socket.create_connection((self._server, self._port))
        self._conn.sendall(request_body)
        self._raw_response = self._receive_response_body()
        return self._raw_response

    def _get_request_body(self) -> bytes:
        """Composes RKSOK request, returns it as bytes"""
        request = f"{self._verb.value} {self._name.strip()} {PROTOCOL}\r\n"
        if self._phone: request += f"{self._phone.strip()}\r\n"
        request += "\r\n"
        return request.encode(ENCODING)

    def _parse_response(self, raw_response: str) -> str:
        """Parses response from RKSOK server and returns parsed data"""
        for response_status in ResponseStatus:
            if raw_response.startswith(f"{response_status.value} "):
                break
        else:
            raise CanNotParseResponseError()
        response_payload = "".join(raw_response.split("\r\n")[1:])
        if response_status == ResponseStatus.NOT_APPROVED:
            response_payload = f"\nКомментарий органов: {response_payload}"
        return HUMAN_READABLE_ANSWERS.get(self._verb).get(response_status) \
            .format(name=self._name, payload=response_payload)

    def _receive_response_body(self) -> str:
        """Receives data from socket connection and returns it as string,
        decoded using ENCODING"""
        response = b""
        while True:
            data = self._conn.recv(1024)
            if not data: break
            response += data
        return response.decode(ENCODING)


def get_server_and_port() -> tuple[str, int]:
    """Returns Server and Port from command-line arguments."""
    try:
        return sys.argv[1], int(sys.argv[2])
    except (IndexError, ValueError):
        raise NotSpecifiedIPOrPortError()


def get_mode() -> int:
    """Asks user for the required mode and returns it.
    There is three modes in this RKSOK client:
        1) get person's phone,
        2) save person's phone
        3) delete person's phone."""
    while True:
        mode = input(
            "Ооо, привет!\n"
            "\n"
            "Это клиент для инновационного протокола РКСОК. "
            "Данный клиент умеет работать с сервером РКСОК, который умеет "
            "сохранять телефоны. Что ты хочешь сделать?\n"
            "\n"
            "1 — получить телефон по имени\n"
            "2 — записать телефон по имени\n"
            "3 — удалить информацию по имени\n"
            "\n"
            "Введи цифру того варианта, который тебе нужен: ")
        try:
            mode = int(mode)
            if not 0 < mode < 4:
                raise ValueError()
            break
        except ValueError:
            print("Упс, что-то ты ввёл не то, выбери один из вариантов\n")
            continue
    return mode


def process_critical_exception(message: str):
    """Prints message, describing critical situation, and exit"""
    print(message)
    exit(1)


def run_client() -> None:
    """Asks all needed data from client and process his query."""
    try:
        server, port = get_server_and_port()
    except NotSpecifiedIPOrPortError:
        process_critical_exception(
            "Упс! Меня запускать надо так:\n\n"
            "python3.9 rksok_client.py SERVER PORT\n\n"
            "где SERVER и PORT — это домен и порт РКСОР сервера, "
            "к которому мы будем подключаться. Например:\n\n"
            "python3.9 rksok_client.py my-rksok-server.ru 5555\n")

    try:
        client = RKSOKPhoneBook(server, port)
    except ConnectionRefusedError:
        process_critical_exception("Не могу подключиться к указанному "
                "серверу и порту")

    verb = MODE_TO_VERB.get(get_mode())
    client.set_verb(verb)
    client.set_name(input("Введи имя: "))
    if verb == RequestVerb.WRITE:
        client.set_phone(input("Введи телефон: "))

    try:
        human_readable_response = client.process()
    except CanNotParseResponseError:
        process_critical_exception(
            "Не смог разобрать ответ от сервера РКСОК:("
        )
    print(f"\nЗапрос: {client.get_raw_request()!r}\n"
          f"Ответ:{client.get_raw_response()!r}\n")
    print(human_readable_response)


if __name__ == "__main__":
    run_client()
