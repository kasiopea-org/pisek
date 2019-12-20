import setuptools

setuptools.setup(
    name='pisek',
    version='0.1',
    description='Nástroj na kontrolování úloh',
    packages=setuptools.find_packages(),
    install_requires=['pyyaml'],
    entry_points={
        'console_scripts': ['pisek=pisek.pisek:main'],
    }
)
