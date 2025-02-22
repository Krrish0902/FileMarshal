import unittest
from src.services.file_service import FileService

class TestFileService(unittest.TestCase):

    def setUp(self):
        self.file_service = FileService()

    def test_monitor_directory(self):
        # Test the directory monitoring functionality
        result = self.file_service.monitor_directory('/path/to/directory')
        self.assertIsNotNone(result)

    def test_sort_files(self):
        # Test the file sorting functionality
        files = ['file3.txt', 'file1.txt', 'file2.txt']
        sorted_files = self.file_service.sort_files(files)
        self.assertEqual(sorted_files, ['file1.txt', 'file2.txt', 'file3.txt'])

    def test_manage_file_state(self):
        # Test managing file states
        file_path = '/path/to/file.txt'
        self.file_service.manage_file_state(file_path, 'processed')
        state = self.file_service.get_file_state(file_path)
        self.assertEqual(state, 'processed')

if __name__ == '__main__':
    unittest.main()