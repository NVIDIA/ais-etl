#
# Copyright (c) 2018-2020, NVIDIA CORPORATION. All rights reserved.
#

import requests, json
from braceexpand import braceexpand

TAR2TF = "tar2tf"
OBJECTS = "objects"
START = "start"


# pylint: disable=unused-variable
class Client:
    def __init__(self, url, bucket):
        self.url = url
        self.bucket = bucket

    def __get_base_url(self):
        return "{}/{}".format(self.url, "v1")

    def list_objects(self, prefix="", sort=False):
        url = "{}/buckets/{}".format(self.__get_base_url(), self.bucket)

        params = {"action": "list", "value": {}}
        if prefix != "":
            params["value"]["prefix"] = prefix

        resp = requests.get(
            url=url, json=params, headers={'Accept': 'application/json'},
        )
        if resp.status_code == 200:
            entries = resp.json()['entries']
            return entries

        return resp.json()

    def get_object(self, object_name, transform_id=""):
        url = "{}/objects/{}/{}".format(self.__get_base_url(), self.bucket,
                                        object_name)
        params = {}
        if transform_id != "":
            params["uuid"] = transform_id

        return requests.get(url=url, params=params).content

    def get_cluster_info(self):
        url = "{}/daemon".format(self.__get_base_url())
        return requests.get(url, params={"what": "smap"}).json()

    def get_objects_names(self, target_url, template):
        proxy_query_url = "{}/v1/query/init".format(self.url, target_url)
        init_msg = {
            "query": {
                "from": {
                    "bucket": {
                        "name": self.bucket,
                        "provider": "ais",
                    }
                },
                "fast": True,
                "outer_select": {
                    "objects_source": template
                }
            }
        }

        # TODO: start only one query for all targets
        uuid = requests.post(proxy_query_url, json=init_msg).content
        target_query_url = "{}/v1/query/next".format(target_url)
        next_msg = {
            "handle": str(uuid, 'utf-8'),
            "size": 0,  # all objects
            "worker_id": 0,
        }

        resp = requests.get(url=target_query_url, json=next_msg)
        bck_list = resp.json()
        if bck_list["entries"] is None:
            return []

        return [o["name"] for o in bck_list["entries"]]

    def start_target_job_stream(self, target_url, target_msg):
        url = "{}/v1/{}/{}/{}".format(target_url, TAR2TF, START, self.bucket)
        return requests.get(url=url,
                            data=json.dumps(dict(target_msg)),
                            stream=True)

    def etl_init(self, spec):
        url = "{}/etl/init".format(self.__get_base_url())
        return str(requests.post(url=url, data=spec).content, "utf-8")

    def etl_stop(self, uuid):
        url = "{}/etl/stop/{}".format(self.__get_base_url(), uuid)
        return requests.delete(url=url)

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
