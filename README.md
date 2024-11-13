## activate virtual environment
```
source venv/bin/activate
```

BuDoBase is a datamanagement-solution for summercamps.
It is meant to make the work of trainers easier to open up more ressources to work with the children and teenagers in the camp,
rather than to have to deal with excel-sheets.

It is built on Django and Bootstrap and accepts an Excel-File with information about the kids to populate the database.
The application is built so that trainers can create different groups of children,
check children in and out if they are not in camp and alter information.

It's also possibile to include a list of important places with their GPS-coordinates or a Google-Maps Link.

Features under development:
- Detect phone numbers
- Dark mode
- New Design

While I document the most common and necessery commands needed for this project, I highly reccomend the following ressources if this is the first time you're using Django:
[W3 schools Django Tutorial](https://www.w3schools.com/django/index.php)
[Django Documentation](https://docs.djangoproject.com/en/5.1/)

Reading over the tutorials may give you a better understanding of how Django works, what files are necessary and what they do.

## Installing the project

Clone the repository:
```bash
git clone https://github.com/budo-app/budo_database.git
```

Install Python if it is not already installed.
```bash
brew install python
```

Create a virtual environment:
```bash
python -m venv venv
```
Activate the virtual environment:
```bash
source venv/bin/activate
```

Install the requirements:
```bash
pip install -r requirements.txt
```

## Running the project
### Virtual Environment
Check if the virtual environment is activated:
If it is active it will have a (venv) in front of your terminal path.
If it is not active run:

```bash
source venv/bin/activate
```
A common error is that you're in the wrong directory, when you try to activate the virtual environment.

### Get it up and running
Change into the project directory:
```bash
cd budo_database
```

Run the project:
```bash
python manage.py runserver
```

## Making changes to the project
If you install new packages, update the requirements.txt:
```bash
pip freeze > requirements.txt
```

