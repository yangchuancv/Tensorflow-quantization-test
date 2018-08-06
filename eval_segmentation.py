from models import unet
import numpy as np
from tqdm import tqdm
from utils.load_weights import weight_loader
from utils.segdata_generator import generator
import argparse
import tensorflow as tf


weights = {'unet_seg': 'vgg16_weights_tf_dim_ordering_tf_kernels.h5',
           'unet_parse': 'resnet50_weights_tf_dim_ordering_tf_kernels.h5'
           }


def compute_iou(gt, pt):
    intersection = 0
    union = 0
    for i, j in zip(gt, pt):
        if i == 1 or j == 1:
            union += 1
        if i == 1 and j == 1:
            intersection += 1

    return intersection / union


if __name__ == '__main__':
    parse = argparse.ArgumentParser(description='command for training segmentation models with keras')
    parse.add_argument('--model', type=str, default='unet', help='support unet, segnet')
    parse.add_argument('--nClasses', type=int, default=2)
    args = parse.parse_args()

    n_classes = args.nClasses
    images_path = '../../datasets/segmentation/'
    val_file = './data/seg_test.txt' if n_classes == 2 else './data/parse_test.txt'
    weights_file = './weights/{}_seg_weights.h5'.format(args.model) if n_classes == 2 \
        else './weights/{}_parse_weights.h5'.format(args.model)
    input_height = 256
    input_width = 256

    weights = weight_loader(weights_file)

    X = tf.placeholder(tf.float32, [None, 256, 256, 3])
    Y = tf.placeholder(tf.float32, [None, 1000, args.nClasses])
    with tf.device('/cpu:0'):
        if args.model == 'unet':
            logits = unet.Unet(X, weights, n_classes, input_height=input_height, input_width=input_width)
        else:
            raise ValueError('Do not support {}'.format(args.model))
        prediction = tf.nn.softmax(logits)

    print('Start evaluating..')
    pbdr = tqdm(total=5000)
    iou = [0. for _ in range(1, n_classes)]
    count = [0. for _ in range(1, n_classes)]
    with tf.Session() as sess:
        for x, y in generator(images_path, val_file, 1, n_classes, input_height, input_width, train=False):
            pbdr.update(1)
            pr = sess.run(prediction, feed_dict={X: x})
            pr = pr.reshape((input_height, input_width, n_classes)).argmax(axis=2)
            y = y[:, :, 1]
            pt = pr.reshape((input_height * input_width))
            gt = y.reshape((input_height * input_width))
            for c in range(1, n_classes):
                gt_img = np.zeros_like(y)
                pt_img = np.zeros_like(y)
                gt_img[:] += (gt[:] == c).astype('uint8')
                pt_img[:] += (gt[:] == c).astype('uint8')
                if (pt_img == gt_img).all():
                    iou[c - 1] += compute_iou(pt_img[0], gt_img[0])
                    count[c - 1] += 1
        miou = 0.
        for c in range(1, n_classes):
            m = iou[c - 1] / count[c - 1]
            miou += m
            print('mIoU: class {0}: {1}'.format(c, m))
        print('mIoU:{}'.format(miou / (n_classes - 1)))
        pbdr.close()
