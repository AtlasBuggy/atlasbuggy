from setuptools import setup, find_packages

setup(
    name='atlasbuggy',
    version='0.1dev',
    packages=find_packages(),
    license='Creative Commons Attribution-Noncommercial-Share Alike license',
    long_description=open('README.md').read(),
    install_requires=[
      'pyserial',
      # opencv installation not required but needs to be done separately
  ]
)
