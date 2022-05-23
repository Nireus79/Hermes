from cx_Freeze import setup, Executable

build_exe_options = {
    'packages': ['static', 'templates', 'js', 'styles'],
    'include_files': ['main.css', 'financial.js', 'hermes_logo.png', 'hw.ico']
}

target = Executable(
    script='run.py',
    base='Win32GUI',
    icon='hw.ico'
)

setup(
    name='Hermes',
    version='0.1',
    description='Crypto trading bot',
    author='Themis Angelopoulos',
    options={'build.exe': build_exe_options},
    executables=[target]
)
