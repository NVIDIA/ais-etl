#
# Copyright (c) 2018-2020, NVIDIA CORPORATION. All rights reserved.
#

import json
from urllib.parse import urlencode
import requests
from braceexpand import braceexpand

from .const import (
    ACT_ETL_BCK,
    START,
    TAR2TF,
    URL_PARAM_ARCHPATH,
    URL_PARAM_PROVIDER,
)
from .msg import ActionMsg, Bck, Bck2BckMsg, BuildETL


# pylint: disable=unused-variable
class Client:
    def __init__(self, url):
        self.url = url
        self._base_url = "{}/{}".format(self.url, "v1")

    @property
    def base_url(self):
        return self._base_url

    def list_objects(self, bck, prefix="", sort=False):
        url = "{}/buckets/{}".format(self.base_url, bck.name)

        params = {"action": "list", "value": {}}
        if prefix != "":
            params["value"]["prefix"] = prefix

        resp = requests.get(
            url=url,
            json=params,
            headers={"Accept": "application/json"},
        )
        if resp.status_code == 200:
            entries = resp.json()["entries"]
            return entries

        return resp.json()

    def get_object(self, bck, object_name, transform_id="", archpath=""):
        url = "{}/objects/{}/{}".format(self.base_url, bck.name, object_name)
        params = {}
        if bck.provider != "":
            params[URL_PARAM_PROVIDER] = bck.provider
        if archpath != "":
            params[URL_PARAM_ARCHPATH] = archpath
        if transform_id != "":
            params["uuid"] = transform_id
        return requests.get(url=url, params=params).content

    def get_cluster_info(self):
        url = "{}/daemon".format(self.base_url)
        return requests.get(url, params={"what": "smap"}).json()

    def get_objects_names(self, bck, target_url, template):
        proxy_query_url = "{}/v1/query/init".format(target_url)
        init_msg = {
            "query": {
                "from": {
                    "bucket": {
                        "name": bck.name,
                        "provider": bck.provider,
                    }
                },
                "fast": True,
                "outer_select": {"objects_source": template},
            }
        }

        # TODO: start only one query for all targets
        uuid = requests.post(proxy_query_url, json=init_msg).content
        target_query_url = "{}/v1/query/next".format(target_url)
        next_msg = {
            "handle": str(uuid, "utf-8"),
            "size": 0,  # all objects
            "worker_id": 0,
        }

        resp = requests.get(url=target_query_url, json=next_msg)
        bck_list = resp.json()
        if bck_list["entries"] is None:
            return []

        return [o["name"] for o in bck_list["entries"]]

    def start_target_job_stream(self, bck, target_url, target_msg):
        url = "{}/v1/{}/{}/{}".format(target_url, TAR2TF, START, bck.name)
        return requests.get(
            url=url, data=json.dumps(dict(target_msg)), stream=True
        )

    def etl_init(self, spec):
        url = "{}/etl/init".format(self.base_url)
        return str(requests.post(url=url, data=spec).content, "utf-8")

    def etl_build(self, build_msg: BuildETL):
        url = "{}/etl/init_code".format(self.base_url)
        resp = requests.post(url, json=build_msg.json())
        return str(resp.content, "utf-8")

    def etl_stop(self, uuid):
        url = "{}/etl/stop/{}".format(self.base_url, uuid)
        return requests.delete(url=url)

    def transform_object(self, bck, transform_id, object_name):
        return self.get_object(bck, object_name, transform_id=transform_id)

    def transform_objects(self, bck, transform_id, template):
        for obj_name in braceexpand(template):
            yield self.transform_object(bck, transform_id, obj_name)

    def object_url(self, bck: Bck, obj: str, transform_id="") -> str:
        params = {}
        if bck.provider:
            params["provider"] = bck.provider
        if transform_id:
            params["uuid"] = transform_id
        return f"{self.base_url}/objects/{bck.name}/{obj}?{urlencode(params)}"

    def expand_object_urls(self, bck: Bck, template: str, transform_id=""):
        return [
            self.object_url(bck, obj_name, transform_id=transform_id)
            for obj_name in braceexpand(template)
        ]

    def transform_bucket(
        self, from_bck: Bck, to_bck: Bck, transform_id
    ) -> str:
        # TODO: implement something similar to go client
        params = {"provider": "ais", "bck_to": f"ais//{to_bck.name}/"}
        bck_msg = Bck2BckMsg(transform_id)
        act_msg = ActionMsg(ACT_ETL_BCK, "", bck_msg).json()
        url = "{}/buckets/{}".format(self.base_url, from_bck.name)
        return str(
            requests.post(url, json=act_msg, params=params).content, "utf-8"
        )
