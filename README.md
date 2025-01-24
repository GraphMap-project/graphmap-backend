# Graphmap-algorithms

# Technology Stack

[![My Skills](https://skillicons.dev/icons?i=py,fastapi)](https://skillicons.dev)

To run: 
- create virtual environment

```
python -m venv venv
```
- activate it
```
venv/Scripts/activate
```
- install all dependencies
```
pip install -r requirements.txt
```
- type ``uvicorn main:app --reload`` to execute file

To make and run migrations:

- Make migrations
```
alembic revision --autogenerate -m "Message"
```
- To run migrations
```
alembic upgrade head
```