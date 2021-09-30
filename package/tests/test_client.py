import unittest
from aistore.client.api import Client


class TestStringMethods(unittest.TestCase):
    def test_list_objects(self):
        client = Client('http://localhost:8080')
        objects = client.list_objects('test')
        self.assertEqual(objects, ['a', 'b', 'c'])


if __name__ == '__main__':
    unittest.main()
