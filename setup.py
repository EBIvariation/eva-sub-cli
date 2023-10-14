import glob
from distutils.core import setup
from os.path import join, abspath, dirname

base_dir = abspath(dirname(__file__))
requirements_txt = join(base_dir, 'requirements.txt')
requirements = [l.strip() for l in open(requirements_txt) if l and not l.startswith('#')]

version = open(join(base_dir, 'eva_sub_cli', 'VERSION')).read().strip()

setup(
    name='eva_sub_cli',
    packages=['eva_sub_cli'],
    package_data={'eva_sub_cli': ['nextflow/*', 'etc/*', 'VERSION']},
    version=version,
    license='Apache',
    description='EBI EVA - validation and submission command line tool',
    url='https://github.com/EBIvariation/eva-sub-cli',
    keywords=['ebi', 'eva', 'python', 'submission', 'validation'],
    install_requires=requirements,
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3'
    ],
    scripts=glob.glob(join(dirname(__file__), 'bin', '*.py'))
)
