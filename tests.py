import asyncio
import unittest
from unittest import mock
import os
from server import FilePhoneBook, InvalidMethodError, RequestHandler, Response, NameIsTooLongError, CanNotParseRequestError, UndefinedResponseFromRegAgent
from conf import PHONEBOOKFILESPATH, RequestVerb, ResponseStatus, RegulatorInfo, PROTOCOL, ENCODING


events = []


class AsyncMock(mock.MagicMock):
    async def __call__(self, *args, **kwargs):
        return super().__call__(*args, **kwargs)

    
class TestFilePhoneBook(unittest.IsolatedAsyncioTestCase):
        
    def setUp(self):    
        self.storage = FilePhoneBook(PHONEBOOKFILESPATH)

        with open(os.path.join(PHONEBOOKFILESPATH, 'Кирилл Хмурый'), 'w') as self.f:
            self.f.write('79842342143')          
        events.append("setUp")
      
    async def test_get(self):
        self.assertEqual(await self.storage.get('Кирилл Хмурый'), '79842342143')

    async def test_write(self):
        print('-'*20)
        await self.storage.write('John', ['78124445598'])
        got = await self.storage.get('John')
        self.assertEqual(got, '78124445598')
        await self.storage.write('John', ['709931142255'])
        got =  await self.storage.get('John')
        self.assertIn(got, ['709931142255\r\n78124445598', '78124445598\r\n709931142255'])

        os.remove(os.path.join(PHONEBOOKFILESPATH, 'John'))
        
    async def test_delete(self):
        await self.storage.write('John', ['78124445598'])
        self.storage.delete('John')
        with self.assertRaises(FileNotFoundError):
            await self.storage.get('John')

    def tearDown(self):
        os.remove(os.path.join(PHONEBOOKFILESPATH, 'Кирилл Хмурый'))
        events.append("tearDown")



class TestRequestHandler(unittest.TestCase):
    def test_parse_request_get(self):
        raw_request = 'ОТДОВАЙ Иван Хмурый РКСОК/1.0\r\n\r\n'
        req = RequestHandler(raw_request)
        self.assertEqual(req.name, 'Иван Хмурый')
        self.assertEqual(req.protocol, PROTOCOL)
        self.assertEqual(req.method, RequestVerb.GET)   
        
        raw_request = 'ОТДОВАЙ РКСОК/1.0\r\n\r\n'
        self.assertRaises(CanNotParseRequestError, RequestHandler, raw_request)
        raw_request = 'ОТДОВАЙ ОЧЕНЬ ДЛИННОЕ ИМЯ КОТОРОЕ ЯВНО БОЛЬШЕ ТРИДЦАТИ СИМВОЛОВ СОВЕРШЕННО ТОЧНО БОЛЬШЕ 30 СИМВОЛОВ РКСОК/1.0\r\n\r\n'
        self.assertRaises(NameIsTooLongError, RequestHandler, raw_request)

    def test_parse_request_delete(self):
        raw_request = 'УДОЛИ Иван Хмурый РКСОК/1.0\r\n\r\n'
        req = RequestHandler(raw_request)
        self.assertEqual(req.name, 'Иван Хмурый')
        self.assertEqual(req.protocol, PROTOCOL)
        self.assertEqual(req.method, RequestVerb.DELETE)   
        
        raw_request = 'УДОЛИ РКСОК/1.0\r\n\r\n'
        self.assertRaises(CanNotParseRequestError, RequestHandler, raw_request)
        raw_request = 'ОТДОВАЙ ОЧЕНЬ ДЛИННОЕ ИМЯ КОТОРОЕ ЯВНО БОЛЬШЕ ТРИДЦАТИ СИМВОЛОВ СОВЕРШЕННО ТОЧНО БОЛЬШЕ 30 СИМВОЛОВ РКСОК/1.0\r\n\r\n'
        self.assertRaises(NameIsTooLongError, RequestHandler, raw_request)

    def test_parse_request_write(self):
        raw_request = 'ЗОПИШИ Иван Хмурый РКСОК/1.0\r\n89012345678\r\n\r\n'
        req = RequestHandler(raw_request)
        self.assertEqual(req.name, 'Иван Хмурый')
        self.assertEqual(req.protocol, PROTOCOL)
        self.assertEqual(req.method, RequestVerb.WRITE)   
        self.assertEqual(req.body, ['89012345678'])
        
        raw_request = 'ЗОПИШИ Иван Хмурый РКСОК/1.0\r\n89012345678 — мобильный\r\n02 — рабочий\r\n\r\n'
        req = RequestHandler(raw_request)
        self.assertEqual(req.name, 'Иван Хмурый')
        self.assertEqual(req.protocol, PROTOCOL)
        self.assertEqual(req.method, RequestVerb.WRITE)   
        self.assertEqual(req.body, ['89012345678 — мобильный', '02 — рабочий'])

        raw_request = 'ЗОПИШИ РКСОК/1.0\r\n\r\n'
        self.assertRaises(CanNotParseRequestError, RequestHandler, raw_request)
        raw_request = 'ОТДОВАЙ ОЧЕНЬ ДЛИННОЕ ИМЯ КОТОРОЕ ЯВНО БОЛЬШЕ ТРИДЦАТИ СИМВОЛОВ СОВЕРШЕННО ТОЧНО БОЛЬШЕ 30 СИМВОЛОВ РКСОК/1.0\r\n\r\n'
        self.assertRaises(NameIsTooLongError, RequestHandler, raw_request)
        

class TestResponse(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.storage = FilePhoneBook(PHONEBOOKFILESPATH)
        await self.storage.write('Petr', ['79842342143'])
        events.append("asyncSetUp")
        
    async def test_make_get(self):
        raw_request = 'ОТДОВАЙ Petr РКСОК/1.0\r\n\r\n'
        resp = Response(raw_request)
        self.assertEqual(await resp.permission_granted, True)
        self.assertEqual(await resp._make_get(self.storage), 'НОРМАЛДЫКС РКСОК/1.0\r\n79842342143\r\n\r\n')
        
        raw_request = 'ОТДОВАЙ Vitya Ivanov РКСОК/1.0\r\n\r\n'
        resp = Response(raw_request)
        self.assertEqual(await resp.permission_granted, True)
        self.assertEqual(await resp._make_get(self.storage), 'НИНАШОЛ РКСОК/1.0\r\n\r\n')


    async def test_make_write(self):
        raw_request = 'ЗОПИШИ Витя РКСОК/1.0\r\n79846543210\r\n\r\n'
        resp = Response(raw_request)
        self.assertEqual(await resp.permission_granted, True)
        self.assertEqual(await resp._make_write(self.storage), 'НОРМАЛДЫКС РКСОК/1.0\r\n\r\n')
        self.assertEqual(await self.storage.get('Витя'), '79846543210')


    async def test_make_delete(self):
        raw_request = 'УДОЛИ Petr РКСОК/1.0\r\n\r\n'
        resp = Response(raw_request)
        self.assertEqual(await resp.permission_granted, True)
        self.assertEqual(await resp._make_delete(self.storage), 'НОРМАЛДЫКС РКСОК/1.0\r\n\r\n')
        with self.assertRaises(FileNotFoundError):
            await self.storage.get('Petr')

        raw_request = 'УДОЛИ Никита Пирожков РКСОК/1.0\r\n\r\n'
        resp = Response(raw_request)
        self.assertEqual(await resp.permission_granted, True)
        self.assertEqual(await resp._make_delete(self.storage), 'НИНАШОЛ РКСОК/1.0\r\n\r\n')
       
       
    def test_make_bad_request(self):
        raw_request = 'НЕ БЫЛО НИ ЕДИНОГО РАЗРЫВА\r\n\r\n'
        resp = Response(raw_request)
        self.assertEqual(resp._make_bad_request(), 'НИПОНЯЛ РКСОК/1.0\r\n\r\n')
 
    
    async def test_make_response(self):
        get_request = 'ОТДОВАЙ Petr РКСОК/1.0\r\n\r\n'
        resp = Response(get_request)
        resp._make_get = AsyncMock(name='_make_get')
        resp._make_delete = AsyncMock(name='_make_delete')
        resp._make_write = AsyncMock(name='_make_write')
        resp._make_bad_request = mock.Mock(name='_make_bad_request')

        
        await resp.make_response(self.storage)
        
        write_request = 'ЗОПИШИ Витя РКСОК/1.0\r\n79846543210\r\n\r\n'
        resp.set_request(write_request)
        await resp.make_response(self.storage)
        
        del_request = 'УДОЛИ Petr РКСОК/1.0\r\n\r\n'
        resp.set_request(del_request)
        await resp.make_response(self.storage)
        
        bad_request = 'НЕ БЫЛО НИ ЕДИНОГО РАЗРЫВА\r\n\r\n'
        resp.set_request(bad_request)
        await resp.make_response(self.storage)

        self.assertTrue(resp._make_get.assert_called_once)
        self.assertTrue(resp._make_write.assert_called_once)
        self.assertTrue(resp._make_delete.assert_called_once)
        self.assertTrue(resp._make_bad_request.assert_called_once)

    async def test_make_response_permission_not_granted(self):

        raw_request = 'ОТДОВАЙ Владимир Путин РКСОК/1.0\r\n\r\n'
        resp = Response(raw_request)
        self.assertEqual(await resp.permission_granted, False)
        self.assertEqual(await resp.make_response(self.storage), resp.reg_agent_response)
        
        raw_request = 'ЗОПИШИ Владимир Путин РКСОК/1.0\r\n79846543210\r\n\r\n'
        resp = Response(raw_request)
        self.assertEqual(await resp.permission_granted, False)
        self.assertEqual(await resp.make_response(self.storage), resp.reg_agent_response)
        with self.assertRaises(FileNotFoundError):
            await self.storage.get('Владимир Путин')
        # self.assertRaises(FileNotFoundError, await self.storage.get, 'Владимир Путин')

        raw_request = 'УДОЛИ Владимир Путин РКСОК/1.0\r\n\r\n'
        resp = Response(raw_request)
        self.assertEqual(await resp.permission_granted, False)
        self.assertEqual(await resp.make_response(self.storage), resp.reg_agent_response)
        with self.assertRaises(FileNotFoundError):
            await self.storage.get('Владимир Путин')

        # self.assertRaises(FileNotFoundError, await self.storage.get, 'Владимир Путин')


if __name__ == '__main__':
    unittest.main()
