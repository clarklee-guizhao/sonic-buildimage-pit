from setuptools import setup, find_packages

dependencies = [
]

setup(
    name='sonic-pit',
    version='1.0',
    description='Platform Integration Test',
    license='Apache 2.0',
    author='S3IP PIT dev-team',
    author_email='guizhao.lh@alibaba-inc.com',
    maintainer='S3IP PIT dev-team',
    maintainer_email='guizhao.lh@alibaba-inc.com',
    install_requires=dependencies,
    packages=find_packages(),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: No Input/Output (Daemon)',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 2.7',
        'Topic :: System :: Utilities',
    ],
    keywords='SONiC Platform Integration Test'
)
