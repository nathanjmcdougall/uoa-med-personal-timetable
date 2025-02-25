import sqlite3
from pathlib import Path

from ics import Calendar
from ics import Event as ICSEvent

from uoa_med_personal_timetable.date import fixdate
from uoa_med_personal_timetable.event import Event
from uoa_med_personal_timetable.html_ import footer, header
from uoa_med_personal_timetable.person import Person


def main(*, output_dir: Path, timetable_sqlite_path: Path):
    cnxn = sqlite3.connect(timetable_sqlite_path)
    cnxn.row_factory = sqlite3.Row
    c = cnxn.cursor()

    people = [
        Person.model_validate(dict(row))
        for row in c.execute("select * from people").fetchall()
    ]
    people = sorted(people, key=Person.get_surname_initial)

    # N.B. this needs to be extracted from a single unified iCal file, which populates
    # this SQLite table.
    events = [
        Event.model_validate(dict(row))
        for row in c.execute("select * from tt order by rowid").fetchall()
    ]

    create_ical_files(output_dir, people=people, events=events)
    create_csv_files(output_dir, people=people, events=events)

    with open(output_dir / "index.htm", mode="w") as f:
        f.writelines(
            header()
            + get_surname_initial_hyperlink_str(people)
            + get_html_body(people)
            + footer()
        )


def create_ical_files(
    output_dir: Path, *, people: list[Person], events: list[Event]
) -> None:
    for idx, person in enumerate(people, start=1):
        ics_events: list[ICSEvent] = []
        for event in events:
            if this_event_is_for_this_person(event=event, person=person):
                ics_event = ICSEvent(
                    begin=fixdate(f"{event.date} {event.st}"),
                    end=fixdate(f"{event.date} {event.et}"),
                    location=event.venue,
                    categories=event.get_event_categories(),
                    name=event.get_event_title(),
                    description=event.get_event_description(),
                )

                ics_events.append(ics_event)

        calendar = Calendar(events=ics_events)
        save_cal(calendar=calendar, filename=output_dir / f"{idx}.ics")


def create_csv_files(output_dir: Path, *, people: list[Person], events: list[Event]):
    for idx, person in enumerate(people, start=1):
        csv_str = "Date,Start Time,End Time,Venue,Module,Session,Title,Staff,Group\r\n"
        for event in events:
            if this_event_is_for_this_person(event=event, person=person):
                csv_str += f"{event.date},{event.st},{event.et},{event.venue},{event.module},{event.session},{event.title},{event.staff},{event.groupid}\r\n"

        save_csv_str(csv_str=csv_str, filename=output_dir / f"{idx}.csv")


def this_event_is_for_this_person(*, event: Event, person: Person) -> bool:
    event_id: str = event.groupid
    personal_sga = person.sga
    personal_hal = person.hal
    personal_comlab = person.comlab

    if not event_id:
        # Core teaching which doesn't need personalization since it's for everyone
        return True
    if event_id.startswith("SGA"):
        return is_matching_class_code(
            event_class_code=event_id.removeprefix("SGA").replace("& SGA", " ").strip(),
            person_class_code=personal_sga,
            is_tbl=False,
        )
    if event_id.startswith("ComLab"):
        return is_matching_class_code(
            event_class_code=event_id.removeprefix("ComLab").strip(),
            person_class_code=personal_comlab,
            is_tbl=False,
        )
    if event_id == "6B-15B":
        event_id = "Tbl " + event_id
    if event_id.startswith("Tbl"):
        return is_matching_class_code(
            event_class_code=event_id.removeprefix("Tbl").replace("& Tbl", " ").strip(),
            person_class_code=personal_hal,
            is_tbl=True,
        )
    msg = f"Unknown group label {event_id}"
    raise NotImplementedError(msg)


def is_matching_class_code(
    *, event_class_code: str, person_class_code: str, is_tbl: bool
) -> bool:
    allowed_class_codes: set[str] = set()
    buildnum = ""
    groupcode = ""
    startrange = 0
    for c in event_class_code + " ":
        if c.isdigit():
            buildnum += c
        elif is_tbl and c in {"A", "B"}:
            groupcode = c
            c = " "
        elif buildnum:
            v = int(buildnum)
            if c == "-":
                startrange = v
                buildnum = ""
            elif startrange:
                if c != " ":
                    msg = f"Unexpected {c} during range"
                    raise ValueError(msg)
                for x in range(startrange, v + 1):
                    allowed_class_codes.add(str(x) + groupcode)
                startrange = 0
                buildnum = ""
            else:
                allowed_class_codes.add(str(v) + groupcode)
                buildnum = ""
                if c != " ":
                    msg = f"Unexpected {c} during spec"
                    raise ValueError(msg)
    return person_class_code in allowed_class_codes


def get_html_body(people: list[Person]) -> str:
    recorded_initials = set()
    body = "<br>"
    for idx, person in enumerate(people, start=1):
        lastname_initial = person.get_surname_initial()

        first_initial_instance = lastname_initial not in recorded_initials
        if first_initial_instance:
            recorded_initials.add(lastname_initial)

        body += get_person_html_body(
            person, stem=str(idx), first_initial_instance=first_initial_instance
        )

    return body


def get_person_html_body(
    person: Person, *, stem: str, first_initial_instance: bool = False
) -> str:
    # This is the HTML corresponding to this person
    person_body = ""
    if first_initial_instance:
        person_body += f"<a name={person.get_surname_initial}> </a>"
    person_body += "<br>"
    person_body += person.get_full_name()
    person_body += f"<a href={stem}.ics>iCal</a> | <a href={stem}.csv>CSV</a>"
    return person_body


def get_surname_initial_hyperlink_str(people: list[Person]) -> str:
    surname_initials = sorted(
        {person.get_surname_initial(): person for person in people}
    )
    surname_initial_hyperlinks = [
        f"<a href=#{initial}>{initial}</a>" for initial in surname_initials
    ]
    surname_initial_hyperlinks_str = " | ".join(surname_initial_hyperlinks)
    return surname_initial_hyperlinks_str


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
