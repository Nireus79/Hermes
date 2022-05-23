from cx_Freeze import setup, Executable

include_files = ['Hermes/files/templates/', 'Hermes/files/static/']

include = ['jinja2', 'jinja2.ext', ]

target = Executable(script="run.py",
                    base="Win32GUI",
                    targetName="Hermes",
                    icon="hw.ico"
                    )
setup(
    name="Hermes",
    version="0.1",
    author="Themis Angelopoulos",
    description="Forex trading bot",
    options={
        'build_exe': {
            'include_files': include_files,
            'includes': include,
            'build_exe': "build"
        }
    },
    executables=[target],  # requires=['flask']
)

#  https://gist.github.com/jorgegarciadev/a68714ef51ddeb1cdcf4
