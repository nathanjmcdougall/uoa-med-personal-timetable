import sqlite3
import sys
from datetime import datetime

from ics import Calendar, Event


def getGPVisit(name):
    # 2:00 PM,5:00 PM,Offsite,LabILA,GP Visit
    # "Student Name" TEXT, "Site" TEXT, "GP Visit date"
    sql = 'select * from gpvisit where `student name`="' + name + '"'
    rs = c.execute(sql)
    gps = rs.fetchall()
    if len(gps) == 0:
        # print(name)
        return 0, None, None
        x = "30/4/2004,8:00 AM,5:00 PM,NO GP VISIT SCHEDULED,LabILA - GP Visit\r\n"
        e = Event()
        e.begin = fixdate2("30/4/2004 8:00 AM")
        e.end = fixdate2("30/4/2004 10:00 PM")
        e.name = "NO GP VISIT SCHEDULED"
        e.description = "LabILA"
        return x, e
    gp = gps[0]
    x = gp[2] + ",2:00 PM,5:00 PM," + gp[1] + ",LabILA - GP Visit\r\n"
    e = Event()
    e.begin = fixdate2(gp[2] + " 2:00 PM")
    e.end = fixdate2(gp[2] + " 5:00 PM")
    e.location = gp[1]
    e.name = "GP Visit"
    e.description = "LabILA"
    sql = 'update gpvisit set matched=1 where `student name`="' + name + '"'
    rs = c.execute(sql)
    return 1, x, e


def fixdate2(x):
    dt = datetime.strptime(x, "%d/%m/%Y %I:%M %p")
    x = dt.isoformat()
    return x


def fixdate(x):
    dt = datetime.strptime(x, "%d %b %Y %I:%M %p")
    x = dt.isoformat()
    return x


def footer():
    o = """<br clear=all><hr><form method=post action=f.php><small><h2>Feedback</h2><a name=feedback>We love criticism. It doesn't have to be constructive. You can <a href="mailto:waynemcdougall+med@gmail.com">email us</a> if you have any comments, questions or complaints</a> or you can fill out this anonymous form:
<br><textarea name=message style='width:99%;height:5vh' placeholder="Type your feedback here..."></textarea><br>Optional email or phone number if you want a reply: <input type=text name=contact><br><input type=submit value="Send Feedback"></small></form>
"""
    return o


def pNum(nrange, match, ha=False):
    inrange = []
    buildnum = ""
    groupcode = ""
    startrange = 0
    for c in nrange + " ":
        if c in ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]:
            buildnum += c
        elif ha and c in ["A", "B"]:
            groupcode = c
            c = " "
        elif buildnum:
            v = int(buildnum)
            if c == "-":
                startrange = v
                buildnum = ""
            elif startrange:
                if c != " ":
                    print(c, "during range")
                for x in range(startrange, v + 1):
                    inrange.append(str(x) + groupcode)
                startrange = 0
                buildnum = ""
            else:
                inrange.append(str(v) + groupcode)
                buildnum = ""
                if c != " ":
                    print(c, "during spec")
    return match in inrange


def doLine(event_id, sga, hal, comlab):
    if not event_id:
        return True
    if event_id[0:3] == "SGA":
        return pNum(event_id[4:].replace("& SGA", " ").strip(), sga)
    if event_id[0:6] == "ComLab":
        return pNum(event_id[6:].strip(), comlab)
    if event_id == "6B-15B":
        event_id = "Tbl " + event_id
    if event_id[0:3] == "Tbl":
        return pNum(event_id[3:].replace("& Tbl", " ").strip(), hal, True)
    print("Unknown group label", event_id)
    return True


db = sqlite3.connect("tt.db")
db.row_factory = sqlite3.Row
c = db.cursor()
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
    rsched, x, e = getGPVisit(fullname)
    if rsched:
        z += x
        cal.events.add(e)
        # print(fullname,e.location)
    for t in tt:
        if (t["session"] != "GP Visit" or rsched == 0) and doLine(
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
