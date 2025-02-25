import sqlite3
from pathlib import Path

import pandera as pa
from ics import Calendar, Event
from pandera import DataFrameModel

from uoa_med_personal_timetable.date import fixdate
from uoa_med_personal_timetable.gp import get_gp_visit
from uoa_med_personal_timetable.html_ import footer, header
from uoa_med_personal_timetable.parse import do_line


class Person(DataFrameModel):
    first: str
    last: str
    sga: str
    hal: str
    comlab: str


class Timetable(DataFrameModel):
    date: str
    st: str = pa.Field(description="Start Time")
    et: str = pa.Field(description="End Time")
    venue: str
    module: str
    session: str
    title: str
    staff: str
    groupid: str


def main(timetable_sqlite_path: Path):
    cnxn = sqlite3.connect(timetable_sqlite_path)
    cnxn.row_factory = sqlite3.Row
    c = cnxn.cursor()
    tt = c.execute("select * from tt order by rowid").fetchall()
    people = c.execute("select * from people").fetchall()
    body = "<br>"

    people = sorted(people, key=get_surname_initial)
    recorded_initials = set()

    for idx, person in enumerate(people, start=1):
        lastname_initial = get_surname_initial(person)

        first_initial_instance = lastname_initial not in recorded_initials
        if first_initial_instance:
            recorded_initials.add(lastname_initial)

        body += get_person_html_body(
            person, stem=str(idx), first_initial_instance=first_initial_instance
        )

    for idx, person in enumerate(people, start=1):
        csv_str = "Date,Start Time,End Time,Venue,Module,Session,Title,Staff,Group\r\n"
        cal = Calendar()
        rsched, lines, e = get_gp_visit(get_full_name(person))
        if rsched:
            csv_str += lines
            cal.events.add(e)

        for t in tt:
            if (t[Timetable.session] != "GP Visit" or rsched == 0) and do_line(
                t[Timetable.groupid],
                person[Person.sga],
                person[Person.hal],
                person[Person.comlab],
            ):
                e = Event()
                e.begin = fixdate(t[Timetable.date] + " " + t[Timetable.st])
                try:
                    e.end = fixdate(t[Timetable.date] + " " + t[Timetable.et])
                except ValueError:
                    e.begin = fixdate(t[Timetable.date] + " " + t[Timetable.et])
                    e.end = fixdate(t[Timetable.date] + " " + t[Timetable.st])
                e.location = t[Timetable.venue]
                lines = t[Timetable.session] + " (" + t[Timetable.module] + ")"
                if t[Timetable.title]:
                    e.name = t[Timetable.title]
                else:
                    e.name = lines
                if t[Timetable.staff]:
                    lines += " Staff: " + t[Timetable.staff]
                if t[Timetable.groupid]:
                    e.categories = [t[Timetable.groupid]]
                e.description = lines
                cal.events.add(e)
                csv_str += (
                    t[Timetable.date]
                    + ","
                    + t[Timetable.st]
                    + ","
                    + t[Timetable.et]
                    + ',"'
                    + t[Timetable.venue]
                    + '","'
                    + t[Timetable.module]
                    + '",'
                    + t[Timetable.session]
                    + ',"'
                    + t[Timetable.title]
                    + '","'
                    + t[Timetable.staff]
                    + '",'
                    + t[Timetable.groupid]
                    + "\r\n"
                )

        save_csv_str(csv_str, f"{idx}.csv")
        save_cal(cal, f"{idx}.ics")

    with open("index.htm", "w") as f:
        f.writelines(
            header() + get_surname_initial_hyperlink_str(people) + body + footer()
        )


def get_person_html_body(
    person: sqlite3.Row, *, stem: str, first_initial_instance: bool = False
) -> str:
    # This is the HTML corresponding to this person
    person_body = ""
    if first_initial_instance:
        person_body += f"<a name={get_surname_initial(person)}> </a>"
    person_body += "<br>"
    person_body += get_full_name(person)
    person_body += f"<a href={stem}.ics>iCal</a> | <a href={stem}.csv>CSV</a>"


def get_full_name(person: sqlite3.Row) -> str:
    first_name = str(person[Person.first]).strip("'")
    last_name = str(person[Person.last]).strip("'")
    return f"{first_name} {last_name}"


def get_surname_initial_hyperlink_str(people: list[sqlite3.Row]) -> str:
    surname_initials = sorted(
        {get_surname_initial(person): person for person in people}
    )
    surname_initial_hyperlinks = [
        f"<a href=#{initial}>{initial}</a>" for initial in surname_initials
    ]
    surname_initial_hyperlinks_str = " | ".join(surname_initial_hyperlinks)
    return surname_initial_hyperlinks_str


def get_surname_initial(person: sqlite3.Row) -> str:
    return str(person[Person.last]).strip("'")[0].upper()


def save_cal(cal: Calendar, filename: str) -> None:
    lines = cal.serialize_iter()
    with open(filename, "w") as my_file:
        for line in lines:
            my_file.writelines(line.replace("00Z", "00"))


def save_csv_str(csv_str: str, filename: str) -> None:
    with open(filename, "w") as f:
        f.writelines(csv_str)


if __name__ == "__main__":
    main(timetable_sqlite_path="tt.db")
