#!/usr/bin/env python3
"""
tv ("textview"): Quickly view (satellite) imagery directly in your terminal.

Dale Roberts <dale.o.roberts@gmail.com>

http://www.github.com/daleroberts/tv
"""
import numpy as np
import shutil
import sys
import os
import re

from urllib.request import urlopen, URLError
from osgeo import gdal
from uuid import uuid4

gdal.UseExceptions()

RESET = bytes('\u001b[0m', 'utf-8')
QUANT = ' ░▒▓█'
CHARS = ' ▄▁▂▃▅▆▇▊▌▎▖▗▘▚▝━┃┏┓┗┛┣┫┳┻╋╸╹╺╻╏──││╴╴╵╵╶╶╵╵⎢⎥⎺⎻⎼⎽▪▙▚▛▜▞▟'
MASKS = [np.array([b == '1' for b in bits]) for bits in
         ['00000000000000000000000000000000',
          '00000000000000001111111111111111',
          '00000000000000000000000000001111',
          '00000000000000000000000011111111',
          '00000000000000000000111111111111',
          '00000000000011111111111111111111',
          '00000000111111111111111111111111',
          '00001111111111111111111111111111',
          '11101110111011101110111011101110',
          '11001100110011001100110011001100',
          '10001000100010001000100010001000',
          '00000000000000001100110011001100',
          '00000000000000000011001100110011',
          '11001100110011000000000000000000',
          '11001100110011000011001100110011',
          '00110011001100110000000000000000',
          '00000000000011111111000000000000',
          '01100110011001100110011001100110',
          '00000000000001110111011001100110',
          '00000000000011101110011001100110',
          '01100110011001110111000000000000',
          '01100110011011101110000000000000',
          '01100110011001110111011001100110',
          '01100110011011101110011001100110',
          '00000000000011111111011001100110',
          '01100110011011111111000000000000',
          '01100110011011111111011001100110',
          '00000000000011001100000000000000',
          '00000000000001100110000000000000',
          '00000000000000110011000000000000',
          '00000000000001100110000000000000',
          '00000110011000000000011001100000',
          '00000000000011110000000000000000',
          '00000000000000001111000000000000',
          '01000100010001000100010001000100',
          '00100010001000100010001000100010',
          '00000000000011100000000000000000',
          '00000000000000001110000000000000',
          '01000100010001000000000000000000',
          '00100010001000100000000000000000',
          '00000000000000110000000000000000',
          '00000000000000000011000000000000',
          '00000000000000000100010001000100',
          '00000000000000000010001000100010',
          '01000100010001000100010001000100',
          '00100010001000100010001000100010',
          '00001111000000000000000000000000',
          '00000000111100000000000000000000',
          '00000000000000000000111100000000',
          '00000000000000000000000011110000',
          '00000000000001100110000000000000',
          '00001100110011001111111111111111',
          '00001100110011000011001100110011',
          '00001111111111111100110011001100',
          '00001111111111110011001100110011',
          '00000011001100111100110011001100',
          '00000011001100111111111111111111']]
SAMPLING = {'nearest': gdal.GRIORA_NearestNeighbour,
            'bilinear': gdal.GRIORA_Bilinear,
            'cubic': gdal.GRIORA_Cubic,
            'cubicspline': gdal.GRIORA_Cubic,
            'lanczos': gdal.GRIORA_Lanczos,
            'average': gdal.GRIORA_Average,
            'mode': gdal.GRIORA_Mode}
RE_URL = 'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
NEWLINE = bytes('\n', 'utf-8')
LVLS256 = [0x00, 0x5f, 0x87, 0xaf, 0xd7, 0xff]
SNAP256 = [(x+y)/2 for x, y in zip(LVLS256, LVLS256[1:])]

def termfg(rgb):
    r, g, b = rgb
    return bytes('\u001b[38;2;' + str(r) + ';' + str(g) + ';' + str(b) + 'm', 'utf-8')

def termbg(rgb):
    r, g, b = rgb
    return bytes('\u001b[48;2;' + str(r) + ';' + str(g) + ';' + str(b) + 'm', 'utf-8')

def termfg256(rgb):
    r, g, b = [len([s for s in SNAP256 if s<x]) for x in rgb]
    c = r*36 + g*6 + b + 16
    return bytes('\033[38;5;' + str(c) + 'm', 'utf-8')

def termbg256(rgb):
    r, g, b = [len([s for s in SNAP256 if s<x]) for x in rgb]
    c = r*36 + g*6 + b + 16
    return bytes('\033[48;5;' + str(c) + 'm', 'utf-8')

def typescale(data, dtype=np.uint8):
    if data.dtype == dtype:
        return data
    typeinfo = np.iinfo(dtype)
    low, high = typeinfo.min, typeinfo.max
    cmin, cmax = data.min(), data.max()
    cscale = cmax - cmin
    scale = float(high - low) / cscale
    typedata = (data * 1.0 - cmin) * scale + 0.4999
    typedata[typedata < low] = low
    typedata[typedata > high] = high
    return typedata.astype(dtype) + np.cast[dtype](low)


def approx(block):
    mins = np.min(block, axis=(0, 1))
    maxs = np.max(block, axis=(0, 1))
    best = np.argmax(maxs - mins)
    split = mins[best] + (maxs[best] - mins[best]) // 2

    mask = block[:, :, best] > split
    fgcount = np.count_nonzero(mask)
    bgcount = 32 - fgcount

    if fgcount > 0:
        fgcolor = np.median(block[mask].reshape((-1, 3)),
                            axis=0).astype(np.uint8)
    else:
        fgcolor = np.array([0, 0, 0], dtype=np.uint8)

    if bgcount > 0:
        bgcolor = np.median(block[~mask].reshape((-1, 3)),
                            axis=0).astype(np.uint8)
    else:
        bgcolor = np.array([0, 0, 0], dtype=np.uint8)

    mask = mask.ravel()
    diff = [np.count_nonzero(mask ^ k) for k in MASKS]
    ndiff = [np.count_nonzero(~mask ^ k) for k in MASKS]
    min_ndiff = np.min(ndiff)
    min_diff = np.min(diff)

    if min_ndiff < min_diff:
        invert = True
        c = CHARS[np.argmin(ndiff)]
        bestdiff = min_ndiff
    else:
        invert = False
        c = CHARS[np.argmin(diff)]
        bestdiff = min_diff

    if bestdiff > 16:
        invert = False
        c = QUANT[min(4, np.count_nonzero(mask) * 5 // 32)]

    if invert:
        return (termfg(bgcolor), termbg(fgcolor), bytes(c, 'utf-8'))
    else:
        return (termfg(fgcolor), termbg(bgcolor), bytes(c, 'utf-8'))


def show(rbs, xoff, yoff, ow, oh, w, h, r, slowout):
    try:
        img = np.empty((h, w, len(rbs)), dtype=np.uint8)
        for i, b in enumerate(rbs):
            bnd = b.ReadAsArray(xoff, yoff, ow, oh, buf_xsize=w,
                                buf_ysize=h, resample_alg=SAMPLING[r])
            img[:, :, i] = typescale(bnd, np.uint8)

    except AttributeError:
        print('incorrect srcwin')
        sys.exit(1)

    hs, ws = 8, 4
    out = bytearray((img.shape[0] + 1) * (img.shape[1] + 1))
    for si in range(0, img.shape[0], hs):
        lastfg, lastbg = '', ''
        for sj in range(0, img.shape[1], ws):
            block = img[si:(si + hs), sj:(sj + ws)]
            fg, bg, char = approx(block)
            if fg != lastfg:
                out.extend(fg)
                lastfg = fg
            if bg != lastbg:
                out.extend(bg)
                lastbg = bg
            out.extend(char)
        out.extend(RESET)
        out.extend(NEWLINE)
    #out.extend(NEWLINE)

    if slowout:
        print(out.decode('utf-8'))
    else:
        os.write(1, out)  # faster


def show_stacked(imgs, w=80, b=None, r='average', srcwin=None, slowout=False):
    fds = [gdal.Open(fd) for fd in imgs[:3]]
    rbs = [fd.GetRasterBand(1) for fd in fds]

    if srcwin is not None:
        xoff, yoff, ow, oh = srcwin
    else:
        xoff, yoff, ow, oh = 0, 0, fds[0].RasterXSize, fds[0].RasterYSize

    hs, ws = 8, 4
    w, h = w * ws, round((oh / ow) * (w * ws) / hs) * hs

    show(rbs, xoff, yoff, ow, oh, w, h, r, slowout)


def show_fd(fd, w=80, b=None, r='average', srcwin=None, slowout=False):
    if b is None:
        b = [1, 2, 3]

    rc = fd.RasterCount

    if rc == 1:
        rbs = [fd.GetRasterBand(1) for i in range(3)]
    else:
        rbs = [fd.GetRasterBand(i) for i in b]

    if srcwin is not None:
        xoff, yoff, ow, oh = srcwin
    else:
        xoff, yoff, ow, oh = 0, 0, fd.RasterXSize, fd.RasterYSize

    hs, ws = 8, 4
    w, h = w * ws, round((oh / ow) * (w * ws) / hs) * hs

    show(rbs, xoff, yoff, ow, oh, w, h, r, slowout)


def show_fn(fn, *args, **kwargs):
    try:
        show_fd(gdal.Open(fn), *args, **kwargs)
    except RuntimeError as e:
        print(e)
        sys.exit(1)


def show_url(url, *args, **kwargs):
    try:
        urlfd = urlopen(url, timeout=15)
        mmapfn = "/vsimem/" + uuid4().hex
        gdal.FileFromMemBuffer(mmapfn, urlfd.read())
        show_fd(gdal.Open(mmapfn), *args, **kwargs)
    except URLError as e:
        print(e)
    finally:
        gdal.Unlink(mmapfn)


def main():
    global RESET, QUANT, CHARS, MASKS, SAMPLING, RE_URL, NEWLINE, LVLS256, SNAP256
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-w', type=int, default=shutil.get_terminal_size()[0])
    parser.add_argument('-b', action='append', type=int)
    parser.add_argument('-r', choices=SAMPLING.keys(), default='average')
    parser.add_argument('-stack', action='store_true')
    parser.add_argument('-urls', action='store_true')
    parser.add_argument('-nofn', action='store_true')
    parser.add_argument('-256', action='store_true')
    parser.add_argument('-slowout', action='store_true')
    parser.add_argument('img', nargs='+')
    parser.add_argument('-unicodes', type=int, default=len(CHARS))
    parser.add_argument('-srcwin', nargs=4,
                        metavar=('xoff', 'yoff', 'xsize', 'ysize'), type=int)
    kwargs = vars(parser.parse_args())

    imgs = kwargs.pop('img')
    urls = kwargs.pop('urls')
    nofn = kwargs.pop('nofn') or (imgs[0] != '-' and len(imgs) == 1)
    stack = kwargs.pop('stack')

    maxc = max(1, min(kwargs.pop('unicodes'), len(CHARS)))
    CHARS = CHARS[:maxc]
    MASKS = MASKS[:maxc]

    if kwargs.pop('256', False):
        termfg = termfg256
        termbg = termbg256

    try:
        if not sys.stdin.isatty() or imgs[0] == '-':
            imgs = [line.strip() for line in sys.stdin.readlines()]

        if stack:
            show_stacked(imgs, **kwargs)
            sys.exit(0)

        for img in imgs:
            if urls:
                for url in re.findall(RE_URL, img):
                    if not nofn:
                        print(url)
                    show_url(url, **kwargs)
            else:
                if not nofn:
                    print(img)
                show_fn(img, **kwargs)

    except KeyboardInterrupt:
        print(RESET.decode('utf-8'))


if __name__ == '__main__':
    main()
