import PyInstaller.__main__

PyInstaller.__main__.run([
    'app.py',
    # '--console',
    '--windowed',
    '--onefile',
    '--clean',
    '-n teacher_control',
])
