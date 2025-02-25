import sqlite3
from pathlib import Path

import pandera as pa
from ics import Calendar, Event
from pandera import DataFrameModel

from uoa_med_personal_timetable.date import fixdate
from uoa_med_personal_timetable.html_ import footer, header
from uoa_med_personal_timetable.parse import this_event_is_for_this_person


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


def main(*, output_dir: Path, timetable_sqlite_path: Path):
    cnxn = sqlite3.connect(timetable_sqlite_path)
    cnxn.row_factory = sqlite3.Row
    c = cnxn.cursor()

    people = c.execute("select * from people").fetchall()
    people = sorted(people, key=get_surname_initial)

    # N.B. this needs to be extracted from a single unified iCal file, which populates
    # this SQLite table.
    timetables = c.execute("select * from tt order by rowid").fetchall()

    create_ical_files(output_dir, people=people, timetables=timetables)
    create_csv_files(output_dir, people=people, timetables=timetables)

    with open(output_dir / "index.htm", mode="w") as f:
        f.writelines(
            header()
            + get_surname_initial_hyperlink_str(people)
            + get_html_body(people)
            + footer()
        )


def create_ical_files(
    output_dir: Path, *, people: list[Person], timetables: list[Timetable]
) -> None:
    for idx, person in enumerate(people, start=1):
        events: list[Event] = []
        for timetable in timetables:
            event_id = timetable[Timetable.groupid]

            if this_event_is_for_this_person(event_id, person=person):
                event = Event(
                    begin=fixdate(
                        f"{timetable[Timetable.date]} {timetable[Timetable.st]}"
                    ),
                    end=fixdate(
                        f"{timetable[Timetable.date]} {timetable[Timetable.et]}"
                    ),
                    location=timetable[Timetable.venue],
                )
                if timetable[Timetable.groupid]:
                    event.categories = [timetable[Timetable.groupid]]
                if timetable[Timetable.title]:
                    event.name = timetable[Timetable.title]
                else:
                    event.name = get_event_title(timetable)
                event.description = get_event_description(timetable)
                events.append(event)

        calendar = Calendar(events=events)
        save_cal(calendar=calendar, filename=output_dir / f"{idx}.ics")


def create_csv_files(
    output_dir: Path, *, people: list[Person], timetables: list[Timetable]
):
    for idx, person in enumerate(people, start=1):
        csv_str = "Date,Start Time,End Time,Venue,Module,Session,Title,Staff,Group\r\n"
        for timetable in timetables:
            event_id = timetable[Timetable.groupid]
            if this_event_is_for_this_person(event_id=event_id, person=person):
                csv_str += f'{timetable[Timetable.date]},{timetable[Timetable.st]},{timetable[Timetable.et]},"{timetable[Timetable.venue]}","{timetable[Timetable.module]}",{timetable[Timetable.session]},"{timetable[Timetable.title]}","{timetable[Timetable.staff]}",{timetable[Timetable.groupid]}\r\n'

        save_csv_str(csv_str=csv_str, filename=output_dir / f"{idx}.csv")


def get_html_body(people: list[sqlite3.Row]) -> str:
    recorded_initials = set()
    body = "<br>"
    for idx, person in enumerate(people, start=1):
        lastname_initial = get_surname_initial(person)

        first_initial_instance = lastname_initial not in recorded_initials
        if first_initial_instance:
            recorded_initials.add(lastname_initial)

        body += get_person_html_body(
            person, stem=str(idx), first_initial_instance=first_initial_instance
        )


def get_event_description(timetable: sqlite3.Row) -> str:
    title = get_event_title()

    if timetable[Timetable.staff]:
        description = f"{title} Staff: {timetable[Timetable.staff]}"
    else:
        description = title

    return description


def get_event_title(timetable: sqlite3.Row) -> str:
    return f"{timetable[Timetable.session]}({timetable[Timetable.module]})"


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


def save_cal(*, calendar: Calendar, filename: Path) -> None:
    lines = calendar.serialize_iter()
    with open(filename, mode="w") as my_file:
        for line in lines:
            my_file.writelines(line.replace("00Z", "00"))


def save_csv_str(*, csv_str: str, filename: Path) -> None:
    with open(filename, mode="w") as f:
        f.writelines(csv_str)


if __name__ == "__main__":
    main(
        output_dir=Path.cwd() / ".output",
        timetable_sqlite_path="tt.db",
    )
