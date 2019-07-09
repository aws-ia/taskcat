from setuptools import setup

with open("requirements.txt") as f:
    REQUIRED = f.read().splitlines()

with open("README.md", "r") as fh:
    LONG_DESCRIPTION = fh.read()

setup(
    version="0.9.0",
    name="taskcat-v9",
    packages=["taskcat"],
    description="An OpenSource Cloudformation Deployment Framework",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    author="Tony Vattathil, Santiago Cardenas, Shivansh Singh, Jay McConnell, "
    "Andrew Glenn",
    author_email="tonynv@amazon.com, sancard@amazon.com, sshvans@amazon.com, "
    "jmmccon@amazon.com, andglenn@amazon.com",
    url="https://aws-quickstart.github.io/taskcat/",
    license="Apache License 2.0",
    download_url="https://github.com/aws-quickstart/taskcat/tarball/master",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Topic :: Software Development :: Libraries",
        "Topic :: Software Development :: Testing",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS :: MacOS X ",
    ],
    scripts=["bin/taskcat-v9"],
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
