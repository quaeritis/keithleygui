import platform
from setuptools import setup, find_packages

data_files = []
if platform.system() in ['Linux', 'FreeBSD']:
    data_files += [('share/applications', ['data/keithleygui.desktop'])]

setup(
    name='keithleygui',
    version='0.1.0',
    description="",
    author='Sam Schott',
    author_email='ss2151@cam.ac.uk',
    url='https://github.com/oe-fet/keithleygui.git',
    license='MIT',
    long_description=open('README.md').read(),
    packages=find_packages(),
    package_data={
        'keithleygui': ['*.ui', '*.mplstyle'],
    },
    data_files=data_files,
    entry_points={
        'console_scripts': [
            'keithleygui=keithleygui.main:run'
        ],
        'gui_scripts': [
            'keithleygui=keithleygui.main:run'
        ]
    },
    install_requires=[
        'setuptools',
        'QtPy',
        'keithley2600',
        'matplotlib',
        'repr',
    ],
    zip_safe=False,
    keywords='keithleygui',
    classifiers=[
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
    test_suite='tests',
    tests_require=[
    ]
)
