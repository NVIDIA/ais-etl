#
# Copyright (c) 2018-2020, NVIDIA CORPORATION. All rights reserved.
#

import requests, json
from braceexpand import braceexpand

TAR2TF = "tar2tf"
OBJECTS = "objects"
START = "start"


# pylint: disable=unused-variable
class AisClient:
    def __init__(self, url, bucket):
        self.url = url
        self.bucket = bucket

    def __get_base_url(self):
        return "{}/{}".format(self.url, "v1")

    def get_object(self, object_name):
        url = "{}/objects/{}/{}".format(self.__get_base_url(), self.bucket, object_name)
        return requests.get(url=url).content

    def get_cluster_info(self):
        url = "{}/daemon".format(self.__get_base_url())
        return requests.get(url, params={"what": "smap"}).json()

    def get_objects_names(self, target_url, template):
        proxy_query_url = "{}/v1/query".format(self.url, target_url)
        init_msg = {
            "query": {
                "from": {
                    "bucket": self.bucket
                },
                "fast": True,
                "outer_select": {
                    "objects_source": template
                }
            }
        }

        # TODO: start only one query for all targets
        uuid = requests.post(proxy_query_url, None, init_msg).json()
        target_query_url = "{}/v1/query/next".format(target_url)
        next_msg = {
            "handle": uuid,
            "size": 0  # all objects
        }

        resp = requests.get(url=target_query_url, json=next_msg)
        bck_list = resp.json()
        return [o["name"] for o in bck_list["entries"]]

    def start_target_job_stream(self, target_url, target_msg):
        url = "{}/v1/{}/{}/{}".format(target_url, TAR2TF, START, self.bucket)
        return requests.get(url=url, data=json.dumps(dict(target_msg)), stream=True)

    def transform_init(self, spec):
        url = "{}/transform/init".format(self.__get_base_url())
        return requests.get(url=url, data=json.dumps(spec)).content

    def transform_object(self, transform_id, object_name):
        url = "{}/objects/{}/{}?uuid={}".format(
            self.__get_base_url(),
            self.bucket,
            object_name,
            transform_id,
        )
        return requests.get(url=url).content

    def transform_objects(self, transform_id, template):
        for obj_name in braceexpand(template):
            yield self.transform_object(transform_id, obj_name)
