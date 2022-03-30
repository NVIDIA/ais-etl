import unittest
import os
from aistore.client.api import Client
from aistore.client.msg import Bck
from aistore.client.const import PROVIDER_AIS

class TestBasicOps(unittest.TestCase):
    def test_bucket(self):
        client = Client('http://localhost:8080')

        res = client.list_buckets(provider=PROVIDER_AIS)
        count = len(res)
        bck = Bck('test', PROVIDER_AIS)
        res = client.create_bucket(bck)
        self.assertEqual(res.status_code, 200)
        res = client.list_buckets(provider=PROVIDER_AIS)
        count_new = len(res)
        self.assertEqual(count+1, count_new)

        res = client.destroy_bucket(bck)
        self.assertEqual(res.status_code, 200)

    def test_put_get(self):
        client = Client('http://localhost:8080')

        res = client.list_buckets(provider=PROVIDER_AIS)
        bck = Bck('test', PROVIDER_AIS)
        res = client.create_bucket(bck)
        self.assertEqual(res.status_code, 200)

        tmpfile = "/tmp/py-sdk-test"
        orig_cont = "test string"
        with open(tmpfile, "w") as fdata:
            fdata.write(orig_cont)

        res = client.put_object(bck, "obj1", tmpfile)
        os.remove(tmpfile)
        self.assertEqual(res.status_code, 200)
        res.close()

        objects = client.list_objects(bck)
        self.assertFalse(objects is None)

        res = client.get_object(bck, "obj1")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.content.decode("utf-8"), orig_cont)
        res.close()

        res = client.destroy_bucket(bck)
        self.assertEqual(res.status_code, 200)

if __name__ == '__main__':
    unittest.main()
