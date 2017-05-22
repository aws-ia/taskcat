from setuptools import setup
import re
import requests

master_version_file = 'taskcat/master_version'
develop_version_file = 'taskcat/develop_version'

def get_pip_version(pkginfo_url):
    pkginfo = requests.get(pkginfo_url).text
    for record in pkginfo.split('\n'):
        if record.startswith('Version'):
            current_version = str(record).split(':', 1)
            return (current_version[1]).strip()


current_develop_version = get_pip_version('https://testpypi.python.org/pypi?name=taskcat&:action=display_pkginfo')
print("PyPi Develop Version is [{}]".format(current_develop_version))

development_version =re.sub('\d$', lambda version: str(int(version.group(0)) + 1), current_develop_version)

print("[new] PyPi Develop Version is [{}]".format(development_version))

current_develop_version = get_pip_version('https://testpypi.python.org/pypi?name=taskcat&:action=display_pkginfo')

setup(
    name='taskcat',
    packages=['taskcat'],
    description='An OpenSource Cloudformation Deployment Framework',
    author='Tony Vattathil, Santiago Cardenas, Shivansh Singh',
    author_email='tonynv@amazon.com, sancard@amazon.com, sshvans@amazon.com',
    url='https://aws-quickstart.github.io/taskcat/',
    version=development_version,
    license='Apache License 2.0',
    download_url='https://github.com/aws-quickstart/taskcat/tarball/master',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Software Development :: Libraries',

    ],

    keywords=['aws', 'cloudformation', 'cloud', 'cloudformation testing', 'cloudformation deploy', 'taskcat'],

    install_requires=['boto3', 'pyfiglet', 'pyyaml', 'tabulate', 'yattag'],

)
