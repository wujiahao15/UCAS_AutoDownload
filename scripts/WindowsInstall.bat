pip install virtualenv
virtualenv --no-site-packages venv
venv\Scripts\activate
pip install -r win_requirements.txt
pyinstaller -F -w ..\src\main.py

move dist\main.exe .

del main.spec
rd /s /q dist
rd /s /q build
rd /s /q __pycache__