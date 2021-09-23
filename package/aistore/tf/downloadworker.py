#
# Copyright (c) 2018-2020, NVIDIA CORPORATION. All rights reserved.
#

from ais.client.api import Client

from queue import Empty
from threading import Thread


# NOTE: Thread is not state-of-the-art mechanism (see GIL), but
# threads aren't under global lock when waiting for I/O
# pylint: disable=unused-variable
class TarsDownloadWorker(Thread):
    def __init__(self, proxy_url, bucket, template, targets_queue,
                 results_queue):
        Thread.__init__(self)
        self.proxy_url = proxy_url
        self.bucket = bucket
        self.template = template
        self.client = Client(self.proxy_url, bucket)

        self.targets_queue = targets_queue
        self.results_queue = results_queue

    def get_object_names(self, target_meta, template):
        for o in self.client.get_objects_names(
                target_meta["intra_data_net"]["direct_url"], template).json():
            yield o

    def run(self):
        while True:
            try:
                # no wait - all targets are put into the queue before starting workers
                target_meta = self.targets_queue.get_nowait()
                for obj_name in self.get_object_names(target_meta,
                                                      self.template):
                    result = self.client.get_object(obj_name)
                    self.results_queue.put(result)  # waits if queue is full
                self.targets_queue.task_done()
            except Empty:
                break
            except Exception as e:
                print("Unexpected exception {}. Skipping".format(str(e)))
                self.targets_queue.task_done()

        self.results_queue.put(None)  # sign that the worker is done
