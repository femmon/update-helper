import setuptools

setuptools.setup(
    name='update-helper-database',
    packages=['updatehelperdatabase'],
    install_requires=[
        'pymysql==1.0.2',
        'requests==2.26.0'
    ]
)
