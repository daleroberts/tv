
**tv** is a tool to quickly view high-resolution multi-band imagery directly in your terminal. It was designed for working with (very large) satellite imagery data over a low-bandwidth connection. For example, it is able to directly visualise a Himawari 8 (11K x 11K pixel) image of the Earth directly from an URL:

<img src="https://github.com/daleroberts/tv/blob/master/docs/earth.png" width="800">

It is built upon the wonderful [GDAL](http://www.gdal.org) library so it is able to handle a large variety of image formats (e.g., PNG, Jpeg, NetCDF) and subsample the image as it reads from disk so it can manage very large files. It has the ability to read filenames (or URLs) from `stdin` and load files directly from URLs without writing locally to disk. Command line options are styled after `gdal_translate` such as:

  *  `-b` to specify the bands (and ordering) to use,
  * `-srcwin xoff yoff xsize ysize` to view a subset of the image,
  * `-r` to specify the subsampling algorithm (nearest,bilinear,cubic,cubicspline,lanczos,average,mode).

## Examples

### Open directly from URL

<img src="https://github.com/daleroberts/tv/blob/master/docs/urls.png" width="750">

### Open directly from URLs on stdin

<img src="https://github.com/daleroberts/tv/blob/master/docs/urls_stdin.png" width="750">

### Different band combinations

<img src="https://github.com/daleroberts/tv/blob/master/docs/landsat_bands.png" width="750">

### Subset the data

<img src="https://github.com/daleroberts/tv/blob/master/docs/subset_obama.png" width="750">

## Comparison

### tv vs hiptext

<img src="https://github.com/daleroberts/tv/blob/master/docs/hiptext_obama.png" width="400">
<img src="https://github.com/daleroberts/tv/blob/master/docs/tv_obama.png" width="400">
