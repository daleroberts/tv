from setuptools import setup, find_packages

setup(name='tv',
      packages=find_packages(),
      install_requires=[
        'gdal',
        'numpy'
      ],
      entry_points = {
        'console_scripts': ['tv=tv.cli:main'],
      },
      version='0.1',
      description='tv: text view images in your console using true color and unicode 9.0 characters',
      url='http://github.com/daleroberts/tv',
      author='Dale Roberts',
      author_email='dale.o.roberts@gmail.com',
      license='MIT',
      zip_safe=False)
