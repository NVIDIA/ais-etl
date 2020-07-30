#
# Copyright (c) 2018-2020, NVIDIA CORPORATION. All rights reserved.
#


# pylint: disable=unused-variable
class TargetMsg:
    def __init__(self, conversions, selections):
        self.conversions = conversions
        self.selections = selections
        # shuffle etc in the future

    def __iter__(self):
        d_conv = []
        for c in self.conversions:
            d_conv.append(dict(c))
        d_selections = []
        for s in self.selections:
            d_selections.append(dict(s))
        yield "conversions", d_conv
        yield "selections", d_selections
