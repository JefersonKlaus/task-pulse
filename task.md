4:40

## FLAG
1  = 


## Task description *
First goal, is configure the mobile design for the django web page.
Second goal, is add a function to export the payment report to a CSV file.
The last goal is create a dashboard to my statistics, tasks and money.



## How to judge completion *
run the project create tasks and update them, after check them as paid see the report and export it.
After that run the pytest commando and see all tests passing.
today we have 194 tests, so, this number will be bigger.


## Other notes for the reviewer (optional)
This is a Django project I build to manage my tasks as a freelance on Aligneer plataform, now, I need to improve it to use in many differente systemas and to be able to import historyc datas (excel). Now the task is create the function to export the report, where I can see how much I am doing.
This is a open source project that can be find here https://github.com/JefersonKlaus/task-pulse.


## How to test
I ran the projec using python manage.py runserver and could create project, add tasks import my excel files to load all my data, to see the dashboadn and generate a report of payments.
After I run the pytest.

SETUP:
python -m venv .venv
source .venv/bin/activate            
pip install -r requirements-dev.txt  

ACTION:
python manage.py migrate
python manage.py createsuperuser     
python manage.py runserver
RESULT: You can navigate in the system

ACTION: pytest
RESULT:  243 passed