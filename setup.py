from setuptools import setup

setup(
    name='VulnPryer',
    setup_requires=['setuptools_scm'],
    use_scm_version=True,
    test_suite='nose.collector',
    tests_require=['nose'],
    author='David F. Severski',
    author_email='davidski@deadheaven.com',
    description='Prying context into your vulnerability information.',
    packages=['vulnpryer'],
    long_description=open('README.rst').read(),
    url='https://github.com/davidski/VulnPryer',
    license='MIT',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Information Technology',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Security'
    ],
    install_requires=[
        "boto3 >= 1.4.0",
        "filechunkio >= 1.8.0",
        "lxml >= 3.7.1",
        "oauth2 >= 1.9.0",
        "pymongo >= 3.4.0",
        "simplejson >= 3.10.0",
        "requests >= 2.12.0",
        "requests_oauthlib >= 0.7.0",
        "python-dateutil >= 2.6.0",
        "configparser >= 2.5.0",
        "future >= 0.16.0",
        "python-crontab >= 2.1.1"
    ],
    scripts=['bin/vulnpryer'],
    include_package_data=True,
    keywords='security vulnerability vulndb redseal',
    data_files=[('/etc', ['conf/vulnpryer.conf.sample'])],
)
