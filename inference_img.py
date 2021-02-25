import os
import cv2
import torch
import argparse
from torch.nn import functional as F
from model.RIFE_HDv2 import Model
import warnings
warnings.filterwarnings("ignore")

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
torch.set_grad_enabled(False)
if torch.cuda.is_available():
    torch.backends.cudnn.enabled = True
    torch.backends.cudnn.benchmark = True


model = Model()
model.load_model(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'train_log'), -1)
model.eval()
model.device()

#enter the images as arguments for us to fill
def return_fill_frames(input_img1,input_img2,ratio=0,rthreshold=0.02,rmaxcycles=8,exp=4):
    if input_img1.endswith('.exr') and input_img2.endswith('.exr'):
        img0 = cv2.imread(input_img1, cv2.IMREAD_COLOR | cv2.IMREAD_ANYDEPTH)
        img1 = cv2.imread(input_img2, cv2.IMREAD_COLOR | cv2.IMREAD_ANYDEPTH)
        img0 = (torch.tensor(img0.transpose(2, 0, 1)).to(device)).unsqueeze(0)
        img1 = (torch.tensor(img1.transpose(2, 0, 1)).to(device)).unsqueeze(0)
    else:
        img0 = cv2.imread(input_img1)
        img1 = cv2.imread(input_img2)
        img0 = (torch.tensor(img0.transpose(2, 0, 1)).to(device) / 255.).unsqueeze(0)
        img1 = (torch.tensor(img1.transpose(2, 0, 1)).to(device) / 255.).unsqueeze(0)

    print("read_shape")
    n, c, h, w = img0.shape
    ph = ((h - 1) // 32 + 1) * 32
    pw = ((w - 1) // 32 + 1) * 32
    padding = (0, pw - w, 0, ph - h)
    img0 = F.pad(img0, padding)
    img1 = F.pad(img1, padding)


    if ratio:
        img_list = [img0]
        img0_ratio = 0.0
        img1_ratio = 1.0
        if ratio <= img0_ratio + rthreshold / 2:
            middle = img0
        elif ratio >= img1_ratio - rthreshold / 2:
            middle = img1
        else:
            tmp_img0 = img0
            tmp_img1 = img1
            for inference_cycle in range(rmaxcycles):
                middle = model.inference(tmp_img0, tmp_img1)
                middle_ratio = ( img0_ratio + img1_ratio ) / 2
                if ratio - (rthreshold / 2) <= middle_ratio <= ratio + (rthreshold / 2):
                    break
                if ratio > middle_ratio:
                    tmp_img0 = middle
                    img0_ratio = middle_ratio
                else:
                    tmp_img1 = middle
                    img1_ratio = middle_ratio
        img_list.append(middle)
        img_list.append(img1)
    else:
        img_list = [img0, img1]
        for i in range(exp):
            tmp = []
            for j in range(len(img_list) - 1):
                mid = model.inference(img_list[j], img_list[j + 1])
                tmp.append(img_list[j])
                tmp.append(mid)
            tmp.append(img1)
            img_list = tmp

    if not os.path.exists('output'):
        os.mkdir('output')
    for i in range(len(img_list)):
        if input_img1.endswith('.exr') and input_img2.endswith('.exr'):
            cv2.imwrite('output/img{}.exr'.format(i), (img_list[i][0]).cpu().numpy().transpose(1, 2, 0)[:h, :w], [cv2.IMWRITE_EXR_TYPE, cv2.IMWRITE_EXR_TYPE_HALF])
        else:
            cv2.imwrite('output/img{}.png'.format(i), (img_list[i][0] * 255).byte().cpu().numpy().transpose(1, 2, 0)[:h, :w])
