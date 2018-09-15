from setuptools import setup
import datetime
import unittest
import os

def get_version():
    _version_file = 'taskcat/.version'

    if os.path.exists(_version_file) and os.path.getsize(_version_file) > 0:
        _version = open(_version_file, 'r').read()
    else:
        _version = datetime.datetime.now().strftime("%Y.%-m%-d.%-H%-M%-s")
        print("Creating new version {}".format(_version))
        update_version = open(_version_file, "w")
        update_version.write(''.join(_version.splitlines()))
        update_version.close()

    return _version

def test_suite():
    test_loader = unittest.TestLoader()
    test_suite = test_loader.discover('tests/unittest', pattern='test_*.py')
    return test_suite

setup(
    name='taskcat',
    packages=['taskcat'],
    description='An OpenSource Cloudformation Deployment Framework',
    author='Tony Vattathil, Santiago Cardenas, Shivansh Singh, Jay McConnell, Andrew Glenn' ,
    author_email='tonynv@amazon.com, sancard@amazon.com, sshvans@amazon.com, jmmccon@amazon.com, andglenn@amazon.com',
    url='https://aws-quickstart.github.io/taskcat/',
    version=get_version(),
    license='Apache License 2.0',
    download_url='https://github.com/aws-quickstart/taskcat/tarball/master',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: Software Development :: Libraries',
    ],
    scripts=[
        'bin/taskcat',
        'bin/alchemist'
    ],
    keywords=['aws', 'cloudformation', 'cloud', 'cloudformation testing', 'cloudformation deploy', 'taskcat'],
    install_requires=['boto3', 'pyfiglet', 'pyyaml', 'tabulate', 'yattag', 'cfn-lint'],
    test_suite='setup.test_suite'

)

