

BuDoBase is a datamanagement-solution for a summercamp called BuDo.
It is meant to make the work of trainers there easier to open up more ressources to work with the children and teenagers in the camp,
rather than having to deal with excel-sheets.

It is built on Django and Postgres (although any other database can be configured since (Djangos Object relational mapping)[https://www.pythontutorial.net/django-tutorial/django-orm/] is used) and accepts an Excel-File with information about the kids to populate the database. At the end of the summercamp, the data can be exported as an Excel-File again.

The application is built so that trainers can create different groups of children,
check children in and out if they are not in camp and alter information.

While this project is very specific to the needs of the summercamp I'm working at,
it might be a good starting point for a similar project.

## Features:
- List views for specific groups (includes formatting for printing)
    - birthdays
    - special medical needs
    - for the first time in the summercamp
    - for the last time in the summercamp
    - age-based family groups (automatically sorted)
    - 1page - namelist with all teamers and kids for games where names need to be drawn
    - Special lists that allow list-specific data-manipulation:
        - Organised train ride from Vienna
        - Organised train ride to Vienna
        - Schwerpunkt allocation
        - Happy Cleaning csv that can be used in Notion to assign multiple kids to Happy cleaning stations at the same time
- Check in and out children
- Detail view for all kids
- Import and export data through Excel-Files (needs the specific s.t.e.f.a.n format)
- Manage pocketmoney of the children
- add notes for children
- summary of dietery needs both for teamers and children
- summary of portions needed for different Schwerpunkt-groups
- Database with Auslagerorte, including a map view, notes, coordinates and pictures for easier Schwerpunkt planning
- Search bar that allows to search for children
- Click-to-call functionality for parents phone numbers
- Responsive design so that it can be used on phones
- Accounting for personal expenses of teamers (to be deprecated in favor of Excel file)
- Backend access to manipulate all data (only for the roles admin and organiser)

### Ideas for future releases:
- Redesign with focus on accesibility
- Moving from postgres to supabase to allow realtime-functionality for Happy Cleaning and Schwerpunkt allocation
    - rebuilding database schema for improved performance and cleanliness
- Rebuilding the frontend with React & Redux for improved performance and maintainability, with a test-driven development approach

While I document the most common and necessery commands needed for this project, I highly reccomend the following ressources if this is the first time you're using Django:
[W3 schools Django Tutorial](https://www.w3schools.com/django/index.php)
[Django Documentation](https://docs.djangoproject.com/en/5.1/)

Reading over the tutorials may give you a better understanding of how Django works, what files are necessary and what they do.

## Installing the project locally

Clone the repository:
```bash
git clone https://github.com/budo-app/budo_database.git
```

Install Python if it is not already installed.
```bash
brew install python
```

Activate the virtual environment:
```bash
source bd_venv/bin/activate
```
Create a virtual environment, if there is none:
```bash
python -m venv bd_venv
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
As always: check if your Virtual environment is activated.

Change into the project directory:
```bash
cd budo_database
```

Run the project:
```bash
python manage.py runserver
```

## Deploying:
To create a new Django secret-key, run this command in the folder that contains your manage.py file:
```bash
python manage.py shell -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

🚨 Important: The secret key in the development settings is only for development. NEVER EVER use it in production.
Whenever you deploy your project in production, you need to set a new secret key. You do not need a new key every time you push your changes, only when you deploy your project on a new service.

Set your Environment variables:
- DJANGO_SECRET_KEY
- DJANGO_ENVIRONMENT=production
- DATABASE_URL (you get this from your database, see below)


On a service like heroku/vercel/railway, once you have set your environment variables, you can deploy the project simply by connecting the repository and pushing your changes to your remote repository (Github/Gitlab/etc). It will automatically build the project and run it.

You still have to run migrations on the deployed project to create the tables in the database. I'll describe how to do this for Railway, but the process should be similar for other services:

Deploy a postgres database within the same project as your application through Railway.

Add the DATABASE_URL environment variable from to your project.

(Railway CLI documentation)[https://docs.railway.com/guides/cli]

Install the Railway CLI on your machine:
```bash
brew install railway
```

Login to Railway:
```bash
railway login
```

Link your project:
```bash
railway link
```

Select your project from the list.
Then select the deployed application, not the database.

Start a shell:
```bash
railway shell
```

Now you're remotely in the deployed application, so you can run the same commands as if you were on your local machine.

Activate the virtual environment:
```bash
source bd_venv/bin/activate
```

Change into the project directory:
```bash
cd budo_database
```

Run migrations:
```bash
python manage.py migrate
```

Last thing to do is to create a superuser to have access to the admin panel:
```bash
python manage.py createsuperuser
```

You can now access the admin panel at the url of your deployed application followed by /admin with your superuser credentials.

You can exit the Railway shell by typing `exit`.

## Making changes to the project
As always: check if your Virtual environment is activated (and yes, I repeat myself because I wasted too much time on errors because of this).

Upgrade individual packages:
```bash
pip install --upgrade <package_name>
```
Upgrade all packages:
Yes, if you're coming from node.js world, this is a bit of a pain. But hey, it works. 🤷‍♂️

```bash
pip --disable-pip-version-check list --outdated --format=json | python -c "import json, sys; print('\n'.join([x['name'] for x in json.load(sys.stdin)]))" | xargs -n1 pip install -U

```
Credits to rbp for the command in this stackoverflow [answer](https://stackoverflow.com/questions/2720014/how-to-upgrade-all-python-packages-with-pip).

If you install or update packages, update the requirements. This project has four different requirement-files:

.budo_database/requirements.txt // necessery for auto-builds, links to requirements/base.txt
./budo_database/requirements/
  base.txt // this includes all packages which should be installed regardless of the environment
  dev.txt // this includes references base.txt and includes additionally all packages which should be installed for development
  production.txt // this includes references base.txt and includes additionally all packages which should be installed for production

You can define which packages should only be installed in development by adding them to ./dev_only_packages.toml

Making use of an alias defined in bd_venv/bin/activate, you can update the requirements while seperating development and production packages. This uses the pip freeze command under the hood:

```bash
pipfreeze
```

### Troubleshooting if pipfreeze doesn't work:
1) Deactivate the virtual environment and then activate it again:
```bash
deactivate
source bd_venv/bin/activate
```

2) If you run into an error like `ModuleNotFoundError: No module named 'pip'`, try to install pip again in the virtual environment:

```bash
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
python get-pip.py
```

If pipfreeze doesn't work at all, you can manually update the requirements by running:
```bash
pip freeze > ./budo_database/requirements/base.txt
```

