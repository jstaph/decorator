import sys
if sys.version >= '3':
    from setuptools import setup
else:
    from distutils.core import setup

dic = {}
exec(open('src/decorator.py').read(), dic)
VERSION = dic['__version__']


if __name__ == '__main__':
    setup(name='decorator',
          version=VERSION,
          description='Better living through Python with decorators',
          long_description=open('README.rst').read(),
          author='Michele Simionato',
          author_email='michele.simionato@gmail.com',
          url='http://pypi.python.org/pypi/decorator',
          license="BSD License",
          package_dir={'': 'src'},
          py_modules=['decorator'],
          keywords="decorators generic utility",
          platforms=["All"],
          classifiers=['Development Status :: 5 - Production/Stable',
                       'Intended Audience :: Developers',
                       'License :: OSI Approved :: BSD License',
                       'Natural Language :: English',
                       'Operating System :: OS Independent',
                       'Programming Language :: Python',
                       'Programming Language :: Python :: 3',
                       'Topic :: Software Development :: Libraries',
                       'Topic :: Utilities'],
          zip_safe=False)
