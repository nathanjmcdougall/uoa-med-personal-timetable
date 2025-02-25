import sqlite3

from pandera import DataFrameModel


class Person(DataFrameModel):
    first: str
    last: str
    sga: str
    hal: str
    comlab: str


def get_full_name(person: sqlite3.Row) -> str:
    first_name = str(person[Person.first]).strip("'")
    last_name = str(person[Person.last]).strip("'")
    return f"{first_name} {last_name}"


def get_surname_initial(person: sqlite3.Row) -> str:
    return str(person[Person.last]).strip("'")[0].upper()
