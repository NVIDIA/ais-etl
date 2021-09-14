import unittest
from ais.client.api import Client


class TestStringMethods(unittest.TestCase):
    def test_list_objects(self):
        client = Client('http://localhost:8080', 'test')
        objects = client.list_objects()
        self.assertEqual(objects, ['a', 'b', 'c'])


if __name__ == '__main__':
    unittest.main()
