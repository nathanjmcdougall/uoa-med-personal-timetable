def do_line(event_id, *, sga, hal, comlab):
    if not event_id:
        return True
    if event_id[0:3] == "SGA":
        return p_num(event_id[4:].replace("& SGA", " ").strip(), sga)
    if event_id[0:6] == "ComLab":
        return p_num(event_id[6:].strip(), comlab)
    if event_id == "6B-15B":
        event_id = "Tbl " + event_id
    if event_id[0:3] == "Tbl":
        return p_num(event_id[3:].replace("& Tbl", " ").strip(), hal, True)
    msg = f"Unknown group label {event_id}"
    raise ValueError(msg)
    return True


def p_num(nrange, match, ha=False):
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
                    msg = f"Unexpected {c} during range"
                    raise ValueError(msg)
                for x in range(startrange, v + 1):
                    inrange.append(str(x) + groupcode)
                startrange = 0
                buildnum = ""
            else:
                inrange.append(str(v) + groupcode)
                buildnum = ""
                if c != " ":
                    msg = f"Unexpected {c} during spec"
                    raise ValueError(msg)
    return match in inrange
