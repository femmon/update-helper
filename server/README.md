# **Server**

# Requirements
- Developed with Python 3.6
# Installing
Run the command from the module root '/server':
```
python3 -m pipenv install # Install dependencies
```
# Running
Besides the universal environment variables, add to `.env` file at the module root the line: `FLASK_ENV=development`. This module hasn't been tested on a production setting.
```
python3 -m pipenv shell # Load environment
python3 ./app.py
```
