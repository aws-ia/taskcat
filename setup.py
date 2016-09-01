from setuptools import setup
setup(
  name = 'taskcat',
  packages = ['taskcat'],
  description = 'An OpenSource Cloudformation Deployment Framework',
  author = 'Tony Vattathil',
  author_email = 'avattathil@gmail.com',
  url = 'https://github.com/avattathil/taskcat.io',
  version = '0.1.dev6',
  download_url = 'https://github.com/avattathil/taskcat.io/archive/master.zip',
  classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
  ],

  keywords = ['aws', 'cloudformation', 'cloud', 'cloudformation testing', 'cloudformation deploy', 'taskcat'],

  #packages=find_packages(exclude=['contrib', 'docs', 'tests']),

  install_requires=['uuid', 'pyfiglet', 'argparse', 'boto3', 'pyyaml'],

  #data_files=[('config', ['ci/config.yml`'])],

  # To provide executable scripts, use entry points in preference to the
  # "scripts" keyword. Entry points provide cross-platform support and allow
  # pip to create the appropriate form of executable for the target platform.
  #entry_points={
  #    'console_scripts': [
  #        'sample=sample:main',
  #    ],
  #},
)
