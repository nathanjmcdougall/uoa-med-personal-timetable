import sqlite3
import sys

from ics import Calendar, Event

from uoa_med_personal_timetable.date import fixdate
from uoa_med_personal_timetable.gp import get_gp_visit
from uoa_med_personal_timetable.html_ import footer
from uoa_med_personal_timetable.parse import do_line

if __name__ == "__main__":
    cnxn = sqlite3.connect("tt.db")
    cnxn.row_factory = sqlite3.Row
    c = cnxn.cursor()
    rs = c.execute("select * from tt order by rowid")
    tt = rs.fetchall()
    rs = c.execute("select * from people")
    person = rs.fetchall()
    lastname = ""
    labels = "<h1>Medical School Personal Timetables</h1>"
    body = "<br>"

    for idx, p in enumerate(person, start=1):
        firstchar = p["last"][0:1].upper()
        if firstchar not in ("'", lastname):
            if firstchar < lastname:
                print(p["first"] + " " + p["last"])
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
        z = "Date,Start Time,End Time,Venue,Module,Session,Title,Staff,Group\r\n"
        cal = Calendar()
        rsched, x, e = get_gp_visit(fullname)
        if rsched:
            z += x
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
                    print(t["title"], t["date"], "start", t["st"], "end", t["et"])
                    e.begin = fixdate(t["date"] + " " + t["et"])
                    try:
                        e.end = fixdate(t["date"] + " " + t["st"])
                    except ValueError:
                        print("End time error " + t["et"])
                        print(t["title"], t["date"], "start", t["st"], "end", t["et"])
                        sys.exit(10)
                    pass
                e.location = t["venue"]
                x = t["session"] + " (" + t["module"] + ")"
                if t["title"]:
                    e.name = t["title"]
                else:
                    e.name = x
                if t["staff"]:
                    x += " Staff: " + t["staff"]
                if t["groupid"]:
                    e.categories = [t["groupid"]]
                e.description = x
                cal.events.add(e)
                z += (
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
        with open(f"{idx}.csv", "w") as f:
            f.writelines(z)
        x = cal.serialize_iter()
        with open(f"{idx}.ics", "w") as my_file:
            for line in x:
                my_file.writelines(line.replace("00Z", "00"))
    with open("index.htm", "w") as f:
        f.writelines(labels + body + footer())
