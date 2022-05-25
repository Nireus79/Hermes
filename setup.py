from cx_Freeze import setup, Executable

packages = ['altgraph', 'attrs', 'bottle', 'certifi', 'cffi',
            'click', 'colorama', 'coremltools', 'docopt', 'future',
            'gevent', 'greenlet', 'idna', 'itsdangerous', 'jinja2', 'jsonschema',
            'kraken', 'krakenex', 'lxml', 'mpmath', 'numpy', 'packaging', 'pandas', 'pefile',
            'pip', 'pipreqs', 'pycparser', 'pykrakenapi', 'pyparsing', 'pyrsistent',
            'pytz', 'regex', 'requests', 'scipy', 'setuptools', 'six',
            'sympy', 'ta', 'torch', 'torchvision', 'tqdm', 'typing_extensions', 'urllib3', 'wheel',
            'whichcraft', 'yarg', 'zope.event', 'zope.interface',
            'bottle-websocket', 'charset-normalizer', 'cx-Freeze', 'cx-Logging', 'Eel', 'Flask', 'gen-exe',
            'gevent-websocket', 'Pillow', 'protobuf', 'python-bidi', 'python-dateutil', 'pywin32', 'pywin32-ctypes',
            'Werkzeug', 'licensespring']

include_files = []  # packages tried in files before

include = []

target = Executable(script="run.py",
                    base="Win32GUI",
                    targetName="Hermes"
                    )
setup(
    name="Hermes",
    version="0.1",
    author="Themis Angelopoulos",
    description="Forex trading bot",
    options={
        'build_exe': {
            'packages': packages,
            'include_files': include_files,
            'includes': include,
            'build_exe': "build"
        }
    },
    executables=[target],
)

#  https://gist.github.com/jorgegarciadev/a68714ef51ddeb1cdcf4
