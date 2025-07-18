Embeddable Python 3.13.5 is extracted here.
The run scripts expect the interpreter at:
  python/python-3.13.5-embed-amd64/python.exe
If `pip` is not detected, `install_requirements` will append `import site`
to `python*._pth` so that the interpreter loads `Lib\\site-packages`.
