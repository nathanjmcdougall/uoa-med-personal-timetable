import sqlite3
from pathlib import Path

import ics

from uoa_med_personal_timetable.event import Event
from uoa_med_personal_timetable.main import main, this_event_is_for_this_person
from uoa_med_personal_timetable.person import Person


class TestMain:
    def test_single_student_single_event(self, tmp_path: Path):
        ## Arrange
        # Create a SQLite database for testing purposes
        db_path = tmp_path / "test.db"
        # Connect to the database
        cnxn = sqlite3.connect(db_path)
        cursor = cnxn.cursor()

        # Populate the Person table
        cursor.execute(
            """
            CREATE TABLE people (
                first TEXT,
                last TEXT,
                sga TEXT,
                hal TEXT,
                comlab TEXT
            )
            """
        )
        cursor.execute(
            """
            INSERT INTO people (first, last, sga, hal, comlab)
            VALUES ('John', 'Doe', 'SGA1', 'HAL1', 'ComLab1')
            """
        )

        # Populate the Event table with a single event
        cursor.execute(
            """
            CREATE TABLE tt (
                groupid TEXT,
                date TEXT,
                st TEXT,
                et TEXT,
                venue TEXT,
                module TEXT,
                session TEXT,
                title TEXT,
                staff TEXT
            )
            """
        )
        cursor.execute(
            """
            INSERT INTO tt (groupid, date, st, et, venue, module, session, title, staff)
            VALUES ('', '24 Jun 2002', '9:00 AM', '10:00 AM', 'Room 101', 'Module1', 'Session1', 'Title1', 'Staff1')
            """
        )

        # Commit the changes to the database
        cnxn.commit()

        ## Act
        # Run the timetabler
        main(
            output_dir=tmp_path,
            timetable_sqlite_path=db_path,
        )

        ## Assert
        # Check there are four files: the DB, the HTM, the ICS and the CSV
        assert len(list(tmp_path.iterdir())) == 4

        # Check the output filenames
        assert (tmp_path / "index.htm").exists()
        assert (tmp_path / "1.ics").exists()
        assert (tmp_path / "1.csv").exists()

        # Check the timetable file is a valid iCal file
        ics_path = tmp_path / "1.ics"
        with open(ics_path) as f:
            calendar = ics.Calendar(f.read())
            assert len(calendar.events) == 1


class TestThisEventIsForThisPerson:
    def test_core_course(self):
        # Arrange
        event = Event(
            date="19 Feb 2024",
            st="9:00 AM",
            et="1:00 PM",
            venue="505-011, 503020",
            module="221",
            session="Lecture",
            title="Introduction",
            staff="C Barrett",
            groupid="",
        )
        person = Person(
            first="John", last="Doe", sga="SGA1", hal="HAL1", comlab="ComLab1"
        )

        # Act
        result = this_event_is_for_this_person(event=event, person=person)

        # Assert
        assert result is True
