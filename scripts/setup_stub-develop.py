from setuptools import setup
setup(
    name='taskcat',
    packages=['taskcat'],
    description='An OpenSource Cloudformation Deployment Framework',
    author='Tony Vattathil, Santiago Cardenas, Shivansh Singh, Jay McConnell',
    author_email='tonynv@amazon.com, sancard@amazon.com, sshvans@amazon.com, jmmccon@amazon.com',
    url='https://aws-quickstart.github.io/taskcat/',
    version='VERSION_STUB',
    license='Apache License 2.0',
    download_url='https://github.com/aws-quickstart/taskcat/tarball/master',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Software Development :: Libraries',
    ],
    scripts=[
        'bin/taskcat',
        'bin/alchemist',
        'bin/taskcat-alchemist',
        'bin/beautycorn',
        'bin/taskcat-beautycorn'
    ],
    keywords=['aws', 'cloudformation', 'cloud', 'cloudformation testing', 'cloudformation deploy', 'taskcat'],
    install_requires=['boto3', 'pyfiglet', 'pyyaml', 'tabulate', 'yattag']
)
