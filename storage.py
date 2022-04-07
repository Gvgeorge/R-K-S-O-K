import aiofiles
import os


class Storage:
    async def get(self, name: str) -> str:
        raise NotImplementedError

    async def write(self, name: str, phones: list) -> None:
        raise NotImplementedError

    def delete(self, name: str) -> None:
        raise NotImplementedError


class FilePhoneBook(Storage):
    '''
    Class for storing phones in the file system
    Creates a separate file for each recorded name
    '''
    def __init__(self, folder_path: str) -> None:
        self._folder_path = folder_path
        if not os.path.exists(self._folder_path):
            os.makedirs(self._folder_path)

    def _get_file_path(self, folder_name, file_name):
        file_path = os.path.join(folder_name, file_name)
        return file_path

    async def get(self, name: str) -> str:
        '''
        Returns the contents of the file of a given name
        '''
        file_path = self._get_file_path(self._folder_path, name)
        async with aiofiles.open(file_path, mode='r') as f:
            contents = await f.readlines()
        return '\r\n'.join(line.strip() for line in contents)

    async def write(self, name: str, phones: list) -> None:
        '''
        Writes phones from to the file of a given name
        Each call of this function rewrites the file
        '''
        file_path = self._get_file_path(self._folder_path, name)
        async with aiofiles.open(file_path, mode='w') as f:
            phones = [phone.strip() for phone in phones if phone.strip()]
            await f.writelines([f'{phone}\r\n' for phone in phones])

    def delete(self, name: str) -> None:
        '''
        Deletes the file of a given name from the filesystem
        '''
        os.remove(self._get_file_path(self._folder_path, name))
