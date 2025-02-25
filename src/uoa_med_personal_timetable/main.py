import sqlite3
from pathlib import Path

from ics import Calendar, Event

from uoa_med_personal_timetable.date import fixdate
from uoa_med_personal_timetable.gp import get_gp_visit
from uoa_med_personal_timetable.html_ import footer, header
from uoa_med_personal_timetable.parse import do_line


def main(timetable_sqlite_path: Path):
    cnxn = sqlite3.connect(timetable_sqlite_path)
    cnxn.row_factory = sqlite3.Row
    c = cnxn.cursor()
    rs = c.execute("select * from tt order by rowid")
    tt = rs.fetchall()
    rs = c.execute("select * from people")
    person = rs.fetchall()
    lastname = ""
    labels = ""
    body = "<br>"

    for idx, p in enumerate(person, start=1):
        firstchar = p["last"][0:1].upper()
        if firstchar not in ("'", lastname):
            lastname = firstchar
            labels += f"<a href=#{firstchar}>{firstchar}</a> |"
            nt = f"<a name={firstchar}> </a>"
        fullname = p["first"] + " " + p["last"]
        body += (
            nt
            + "<br>"
            + fullname
            + f" <a href={idx}.ics>iCal</a> | <a href={idx}.csv>CSV</a>"
        )
        nt = ""
        csv_str = "Date,Start Time,End Time,Venue,Module,Session,Title,Staff,Group\r\n"
        cal = Calendar()
        rsched, lines, e = get_gp_visit(fullname)
        if rsched:
            csv_str += lines
            cal.events.add(e)

        for t in tt:
            if (t["session"] != "GP Visit" or rsched == 0) and do_line(
                t["groupid"], p["sga"], p["hal"], p["comlab"]
            ):
                e = Event()
                e.begin = fixdate(t["date"] + " " + t["st"])
                try:
                    e.end = fixdate(t["date"] + " " + t["et"])
                except ValueError:
                    e.begin = fixdate(t["date"] + " " + t["et"])
                    e.end = fixdate(t["date"] + " " + t["st"])
                e.location = t["venue"]
                lines = t["session"] + " (" + t["module"] + ")"
                if t["title"]:
                    e.name = t["title"]
                else:
                    e.name = lines
                if t["staff"]:
                    lines += " Staff: " + t["staff"]
                if t["groupid"]:
                    e.categories = [t["groupid"]]
                e.description = lines
                cal.events.add(e)
                csv_str += (
                    t["date"]
                    + ","
                    + t["st"]
                    + ","
                    + t["et"]
                    + ',"'
                    + t["venue"]
                    + '","'
                    + t["module"]
                    + '",'
                    + t["session"]
                    + ',"'
                    + t["title"]
                    + '","'
                    + t["staff"]
                    + '",'
                    + t["groupid"]
                    + "\r\n"
                )

        save_csv_str(csv_str, f"{idx}.csv")
        save_cal(cal, f"{idx}.ics")

    with open("index.htm", "w") as f:
        f.writelines(header() + labels + body + footer())


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
