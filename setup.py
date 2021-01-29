from setuptools import setup

with open("requirements.txt", encoding="utf-8") as f:
    REQUIRED = f.read().splitlines()

with open("README.md", "r", encoding="utf-8") as fh:
    LONG_DESCRIPTION = fh.read()

with open("VERSION", "r", encoding="utf-8") as fh:
    VERSION = fh.read()
setup(
    version=VERSION,
    name="taskcat",
    packages=[
        "taskcat",
        "taskcat._cfn",
        "taskcat._cli_modules",
        "taskcat.testing",
        "taskcat_plugin_testhook",
    ],
    description="An OpenSource Cloudformation Deployment Framework",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    author="Tony Vattathil, Jay McConnell, Andrew Glenn, Santiago Cardenas, Shivansh "
    "Singh",
    author_email="tonynv@amazon.com, jmmccon@amazon.com, andglenn@amazon.com, "
    "sshvans@amazon.com",
    url="https://aws-quickstart.github.io/taskcat/",
    license="Apache License 2.0",
    download_url="https://github.com/aws-quickstart/taskcat/tarball/master",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Topic :: Software Development :: Libraries",
        "Topic :: Software Development :: Testing",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS :: MacOS X ",
    ],
    scripts=["bin/taskcat"],
    keywords=[
        "aws",
        "cloudformation",
        "cloud",
        "cloudformation testing",
        "cloudformation deploy",
        "taskcat",
    ],
    install_requires=REQUIRED,
    test_suite="tests",
    tests_require=["mock", "boto3"],
    include_package_data=True,
)
