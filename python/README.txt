Embeddable Python 3.13.5 is extracted here.
The run scripts expect the interpreter at:
  python/python-3.13.5-embed-amd64/python.exe
If `pip` is not detected, `install_requirements` will patch `python*._pth`
to include the current directory (a lone `.` line) and `import site` so the
interpreter loads `Lib\\site-packages`.
