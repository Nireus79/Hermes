from cx_Freeze import setup, Executable

packages = []

include_files = []

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
