''' MobilenetV2 in PyTorch; 
    (ref) https://github.com/pytorch/vision/blob/main/torchvision/models/mobilenetv2.py

For more detail, see the paper " MobileNetV2: Inverted Residuals and Linear Bottlenecks".

This code file follows the code format from: 
    - https://github.com/roeiherz/MobileUNET/blob/master/nets/MobileNetV2.py  ; 2D Conv example 
    - https://github.com/wei-tim/YOWO/blob/master/backbones_3d/mobilenetv2.py ; 3D Conv example 
    - https://gaussian37.github.io/dl-concept-mobilenet_v2/
'''
import math 
import os.path as osp
from turtle import forward 

import torch
import torch.nn as nn 



# Set operation tools 
# -------------------------
def conv_bn(inp, oup, stride): 
    return nn.Sequential(
        nn.Conv2d(inp, oup, kernel_size=3, stride=stride, padding=1, bias=False), 
        nn.BatchNorm2d(oup),
        nn.ReLU6(inplace=True),
    )

def conv_1x1x1_bn(inp, oup): 
    return nn.Sequential(
        nn.Conv2d(inp, oup, 1, 1, 0, bias=False),
        nn.ReLU6(inplace=True),
    )

class InvertedResidual(nn.Module): 
    def __init__(self, inp, oup, stride, expand_ratio): 
        super(InvertedResidual, self).__init__()
        self.stride = stride 
        assert stride in [1, 2], f"InvertedResidual in {osp.basename(__file__)}: 'stride' should be in [1, 2]"

        hidden_dim = round(inp * expand_ratio)
        self.use_res_connect = (self.stride == 1 and inp == oup) # True / False 

        if expand_ratio == 1: 
            self.conv = nn.Sequential(
                # dw 
                nn.Conv2d(hidden_dim, hidden_dim, 3, stride, 1, groups=hidden_dim, bias=False), 
                nn.BatchNorm2d(hidden_dim), 
                nn.ReLU6(inplace=True), 
                # pw-linear 
                nn.Conv2d(hidden_dim, oup, 1, 1, 0, bias=False),
                nn.BatchNorm2d(oup),
            )
        else: 
            self.conv = nn.Sequential(
                # pw 
                nn.Conv2d(inp, hidden_dim, 1, 1, 0, bias=False), 
                nn.BatchNorm2d(hidden_dim), 
                nn.ReLU6(inplace=True),
                # dw 
                nn.Conv2d(hidden_dim, hidden_dim, 3, stride, 1, groups=hidden_dim, bias=False), 
                nn.BatchNorm2d(hidden_dim), 
                nn.ReLU6(inplace=True), 
                # pw-linear 
                nn.Conv2d(hidden_dim, oup, 1, 1, 0, bias=False), 
                nn.BatchNorm2d(oup), 
            )

    def forward(self, x:torch.Tensor): 
        assert x.ndimension() == 4 , f"Tensor should be 4D, but get {x.ndimension()}D"

        if self.use_res_connect: 
            return x + self.conv(x)
        else: 
            return self.conv(x)


# Design MobileNetV2 
# -------------------------
class MobileNetV2(nn.Module): 
    def __init__(self, n_class=1000, input_size=224, width_mult=1. ):
        super(MobileNetV2, self).__init__()

        block = InvertedResidual
        input_channel, last_channel = 32, 1280 
        interverted_residual_setting = [
            # t, c, n, s
            [1, 16, 1, 1],
            [6, 24, 2, 2], 
            [6, 32, 3, 2],
            [6, 64, 4, 2],
            [6, 96, 3, 1],
            [6, 160, 3, 2],
            [6, 320, 1, 1],
        ]

        # building first layer 
        # -----------------------
        assert input_size % 32 == 0, f"MobileNetV2 in {osp.basename(__file__)}: should be 'input_size % 32 == 0'"
        