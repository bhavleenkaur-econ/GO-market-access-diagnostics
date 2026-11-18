"""Write the stakeholder brief from the scored table, so every figure in the text matches the table."""

import pandas as pd

from . import config as C


def _n(value, digits=0):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "n/a"
    if number != number:
        return "n/a"
    return f"{number:,.{digits}f}"


def _share(row):
    value = row.constraint_share
    if value is None or value != value:
        return "n/a"
    return f"{value:.0f}%"


def _names(frame):
    names = list(frame.station_name)
    if len(names) <= 1:
        return "".join(names)
    if len(names) == 2:
        return f"{names[0]} and {names[1]}"
    return ", ".join(names[:-1]) + ", and " + names[-1]


def _findings(priority, meta, names, table):
    """Priority table, then one recommendation for each constraint."""
    from .recommendations import ACTIONS

    lines = ["## What I found", ""]
    counts = priority.primary_likely.value_counts()
    counted = ", ".join(f"{n} {label.lower()}" for label, n in counts.items())
    lines.append(f"I found {len(priority)} priority stations: {counted}.")
    lines.append("")
    lines.append(
        "The share is the largest numeric deficit divided by the sum of the deficits that are below "
        "the reference stations. Where I use the land-use rule, that share still belongs to the largest "
        "numeric deficit. I do not treat the land-use label as a percentage."
    )
    lines.append("")
    lines.append(
        "| Station | Line | Market | Conditions | What I would act on | Largest deficit | Close second | On its own line |"
    )
    lines.append("| --- | --- | ---: | ---: | --- | --- | --- | --- |")
    for row in priority.itertuples():
        second = row.second_constraint if row.is_tie and isinstance(row.second_constraint, str) else ""
        own = row.corridor_constraint or ""
        lines.append(
            f"| {row.station_name} | {row.line_name} | {row.market_score:.0f} | {row.conditions_score:.0f} | "
            f"{row.primary_likely} | {row.largest_deficit} ({_share(row)}) | {second} | {own} |"
        )
    lines.append("")
    order = ["Rail service", "Local connections", "Walk access", "Parking headroom", "Fare burden", "Land use"]
    key_of = {label: key for key, label in C.CONDITION_LABELS.items()}
    for label in order:
        group = priority[priority.primary_likely.eq(label)]
        if group.empty:
            continue
        action = ACTIONS[key_of[label]]["action"]
        owners = ", ".join(dict.fromkeys(group.owner))
        lines.append(f"**{label}.** {_names(group)}. {action} The owner is {owners}.")
        lines.append("")
        if label == "Local connections":
            detail = table[table.station_id.isin(set(group.station_id))]
            bits = [
                f"{r.station_name} has {_n(r.feeder_am_arrivals, 0)} AM-peak bus arrivals and a median wait of {_n(r.am_transfer_wait_min, 0)} minutes"
                for r in detail.itertuples()
            ]
            longest = (
                table[table.station_id.isin(set(priority.station_id))]
                .dropna(subset=["am_transfer_wait_min"])
                .nlargest(1, "am_transfer_wait_min")
                .iloc[0]
            )
            follow = (
                "I already flag that station for rail service, because the thin timetable is the larger gap."
                if longest.primary_likely == "service"
                else "I keep the label I already assigned there, and I treat the wait as a second look."
            )
            lines.append(
                ". ".join(bits)
                + f". The longest median wait in the priority set is {longest.station_name}, at "
                f"{_n(longest.am_transfer_wait_min, 0)} minutes. " + follow
            )
            lines.append("")
        if label == "Land use":
            none = table[table.station_id.isin(set(group.station_id)) & table.feeder_am_arrivals.fillna(0).eq(0)]
            if len(none):
                lines.append(
                    f"{_names(none)} also have no local bus stop within 250 m. A rail add at those stations "
                    "would still leave the trip dependent on driving or a long walk."
                )
                lines.append("")
        ties = group[group.is_tie & group.second_constraint.fillna("").ne("")]
        if len(ties):
            bits = [f"{r.station_name} ({r.second_constraint.lower()})" for r in ties.itertuples()]
            lines.append(
                "The second deficit is within 10 points at " + ", ".join(bits)
                + ", so I would not fund only one of them."
            )
            lines.append("")
        flips = group[group.label_changes_with_corridor & group.corridor_constraint.fillna("").ne("")]
        if len(flips):
            bits = [f"{r.station_name} ({r.corridor_constraint.lower()})" for r in flips.itertuples()]
            lines.append(
                "Compared with its own line, the largest deficit changes at " + ", ".join(bits) + "."
            )
            lines.append("")
            if label == "Rail service":
                for line_name, members in flips.groupby("line_name"):
                    if len(members) < 3:
                        continue
                    stations = list(members.station_name)
                    joined = ", ".join(stations[:-1]) + ", and " + stations[-1] if len(stations) > 1 else stations[0]
                    lines.append(
                        f"{joined} are all on the {line_name} line. I first compared them with the rest of the "
                        "network, where the timetable is the gap. I then compared them with each other. Stations "
                        "that share one timetable have the same service score, so the own-line deficit moves to "
                        "another condition. I would keep the service recommendation, because the within-line "
                        "comparison cannot see a gap that the whole line shares."
                    )
                    lines.append("")
    stable = meta.get("priority_stable") or []
    stable_names = ", ".join(names.get(s, s) for s in stable) or "none"
    spearman = meta.get("weight_spearman") or {}
    schemes = meta.get("priority_by_scheme") or {}
    equal = set(schemes.get("equal") or [])
    access = set(schemes.get("access_heavy") or [])
    service = set(schemes.get("service_heavy") or [])
    leaves = ", ".join(names.get(s, s) for s in sorted(equal - access)) or "none"
    joins = ", ".join(names.get(s, s) for s in sorted(service - equal)) or "none"
    lines.append(
        "I then recomputed the conditions score with access weighted twice as heavily, and again with "
        "service weighted twice as heavily. Rank correlation with the equal-weight score is "
        + ", ".join(f"{k.replace('_', ' ')} {v:.2f}" for k, v in spearman.items())
        + f". Stations that stay in the priority set under all three weights are: {stable_names}. "
        f"Stations that leave the priority set when I weight access more heavily are: {leaves}. "
        f"Stations that join when I weight service more heavily are: {joins}."
    )
    lines.append("")
    clear = ", ".join(names.get(s, s) for s in (meta.get("priority_clear") or [])) or "none"
    sensitive = ", ".join(names.get(s, s) for s in (meta.get("priority_threshold_sensitive") or [])) or "none"
    looser = ", ".join(names.get(s, s) for s in (meta.get("priority_looser_only") or [])) or "none"
    lines.append(
        f"The median is one cut. I also split the conditions score at the 40th percentile "
        f"({_n(meta.get('conditions_p40'), 1)}) and the 60th ({_n(meta.get('conditions_p60'), 1)}). "
        f"Stations in the priority set at all three cuts are: {clear}. "
        f"Stations that are priority at the median, and not at the 40th, are threshold-sensitive: {sensitive}. "
        f"Stations that would join only if I moved the cut up to the 60th are: {looser}."
    )
    lines.append("")
    sens = meta.get("fare_sensitivity") or {}
    changed = sens.get("labels_changed") or {}

    def _who(key):
        vals = changed.get(key) or []
        return ", ".join(vals) if vals else "none"

    lines.append(
        "The GTFS fare file has one price per zone pair, so I do not apply a PRESTO discount I cannot see. "
        f"I recomputed the fare deficit after subtracting ${float(sens.get('flat_discount') or 0):.0f} from "
        f"every fare, after a {100 * float(sens.get('percent_discount') or 0):.0f}% reduction, with the "
        "frequency delay set to a quarter of the headway, and with the value of time at 35% and at 70% of "
        "the shed wage. The largest deficit changes under the flat reduction at: "
        f"{_who('flat_discount')}. Under the percent reduction: {_who('percent_discount')}. "
        f"Under a timed arrival: {_who('timed_arrival')}. Under the lower value of time: {_who('vot_low')}. "
        f"Under the higher value of time: {_who('vot_high')}."
    )
    lines.append("")
    return lines


def _evidence(table):
    focus = table[table.quadrant.eq("priority") | table.station_id.isin(C.KITCHENER_CASE)].sort_values(
        ["quadrant", "market_score"], ascending=[True, False]
    )
    lines = ["## Competing explanations", ""]
    lines.append(
        "For each priority station, and for the Kitchener stations I look at up close, I set the label "
        "next to the evidence that supports it and the evidence that cuts against it. Confidence is high "
        "only when one deficit is at least half of the gap, the station's own line agrees, the land-use "
        "rule did not replace the deficit, and the station is not within 5 points of a median."
    )
    lines.append("")
    lines.append("| Station | Primary | Second | Confidence | Supporting evidence | Contradictory evidence |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for row in focus.itertuples():
        primary = C.CONDITION_LABELS.get(row.primary_likely, row.primary_likely)
        second = C.CONDITION_LABELS.get(row.runner_up, "") if pd.notna(row.runner_up) else ""
        lines.append(
            f"| {row.station_name} | {primary} | {second} | {row.confidence} | "
            f"{row.supporting_evidence} | {row.contradictory_evidence} |"
        )
    lines.append("")
    return lines


def _kitchener(table, meta):
    lines = ["## Kitchener line", ""]
    kit = table[table.station_id.isin(C.KITCHENER_CASE)].sort_values("weekday_to_union")
    bits = [
        f"{r.station_name}: AM headway {_n(r.am_headway_min)} minutes, longest midday gap "
        f"{_n(r.midday_max_gap_min)} minutes, trains from {r.first_departure_clock} to {r.last_departure_clock}, "
        f"weekend span {_n(r.weekend_span_hours, 1)} hours"
        for r in kit.itertuples()
    ]
    lines.append(
        "I then looked at the Kitchener line on its own, because this is the corridor I can speak to from "
        "Guelph. " + ". ".join(bits) + "."
    )
    lines.append("")
    guelph = table[table.station_id.eq("GL")]
    if len(guelph):
        g = guelph.iloc[0]
        fare_label = C.CONDITION_LABELS.get(g.numeric_primary, g.numeric_primary)
        gap = float(g.conditions_gap) if pd.notna(g.conditions_gap) else 0.0
        side = "below" if gap > 0 else "above"
        near = (
            " It is within 5 points of a median, so I do not treat that side of the cut as a firm class."
            if bool(g.near_cut) else ""
        )
        in_set = " It is in the priority set." if g.quadrant == "priority" else " It is not in the priority set."
        lines.append(
            f"Guelph Central is the station I can check on the ground. Its market score is {g.market_score:.0f} "
            f"and its conditions score is {g.conditions_score:.1f}. The conditions median is "
            f"{meta.get('conditions_median'):.1f}, so Guelph sits {abs(gap):.1f} points {side} the conditions cut."
            f"{in_set}{near} The largest deficit against the reference stations "
            f"is still {str(fare_label).lower()}, at {g.primary_deficit:.0f} points. "
            f"The walk catchment has about {_n(g.walk_pop, 0)} residents and {_n(g.walk_jobs, 0)} jobs, and the "
            f"station shed has about {_n(g.shed_pop, 0)} residents. The census subdivision sends "
            f"{100 * g.commute_to_toronto_share:.1f}% of its commuters to Toronto, and "
            f"{100 * g.shed_wfh_share:.0f}% of employed residents in the shed worked at home in 2021. "
            f"The 2019 lot has {_n(g.parking_spaces_2019, 0)} spaces. That is too small to score as a network "
            f"commuter lot, and it was over capacity in 2019. Local buses are Guelph Transit's. The AM-peak "
            f"scheduled wait from a bus to the next train toward Union is {_n(g.am_transfer_wait_min, 0)} minutes."
        )
        lines.append("")
    kitchener = table[table.station_id.eq("KI")]
    if len(kitchener):
        k = kitchener.iloc[0]
        schemes = meta.get("priority_by_scheme") or {}
        equal, access, service = set(schemes.get("equal") or []), set(schemes.get("access_heavy") or []), set(schemes.get("service_heavy") or [])
        weight = []
        if "KI" in equal and "KI" not in access:
            weight.append("When I weight access more heavily, Kitchener leaves the priority set.")
        if "KI" in service:
            weight.append("When I weight service more heavily, Kitchener stays in the priority set.")
        if "GL" not in equal and "GL" in service:
            weight.append("Under that same service weighting, Guelph Central joins the priority set.")
        place = "is in the priority set" if k.quadrant == "priority" else "is not in the priority set"
        deficit_name = C.CONDITION_LABELS.get(k.numeric_primary, k.numeric_primary)
        lines.append(
            f"Kitchener {place}. The published fare to Union is ${k.fare_to_union:.2f}. "
            f"The scheduled ride is {_n(k.ivt_to_union_min, 0)} minutes, the AM headway toward Union is "
            f"{_n(k.am_headway_min, 0)} minutes, and the generalized cost at half the shed wage is "
            f"${k.generalized_cost:.2f}. The walk catchment has about {_n(k.walk_pop, 0)} residents and "
            f"{_n(k.walk_jobs, 0)} jobs. The largest deficit is {str(deficit_name).lower()}. " + " ".join(weight)
        )
        lines.append("")
    et = table[table.station_id.eq("ET")]
    if len(et):
        e = et.iloc[0]
        lines.append(
            f"Etobicoke North is the Kitchener station I would act on for walk access. The walkshed covers "
            f"{100 * e.walk_reach_ratio:.0f}% of the 800 m circle and holds about {_n(e.walk_pop, 0)} "
            f"{'resident' if float(e.walk_pop) < 1.5 else 'residents'} "
            f"and {_n(e.walk_jobs, 0)} jobs. The station sits in employment land, with a station shed of about "
            f"{_n(e.shed_pop, 0)} residents and {100 * e.commute_to_toronto_share:.0f}% of the home "
            f"municipality's commuters working in Toronto."
        )
        lines.append("")
    return lines


def write(table, recs, meta):
    scored = table[table.in_score]
    priority = recs[recs.quadrant.eq("priority")]
    names = dict(zip(table.station_id, table.station_name))
    lines = []
    lines.append("# Where GO ridership cannot show up yet")
    lines.append("")
    lines.append("## The question")
    lines.append("")
    lines.append(
        "I asked which GO and UP stations have a strong surrounding travel market, but weak walk access, "
        "local connections, rail service, parking headroom, or fare. I did not ask which stations have low "
        "ridership. Station boardings and PRESTO transactions are not open, so a ridership model would have "
        "been a guess. The scorecard is the evidence I can defend, and it is the question I would take to "
        "Transit Strategy and Insights."
    )
    lines.append("")
    lines.append("## What I did, in order")
    lines.append("")
    lines.append(
        f"I first took the current GO and UP Express schedules for Wednesday "
        f"{C.GO_WEEKDAY[:4]}-{C.GO_WEEKDAY[4:6]}-{C.GO_WEEKDAY[6:]}, the Saturday, and the Sunday inside that "
        "feed. I measured the AM headway toward Union, the longest midday gap, the weekday span from the "
        "first train to the last, and the weekend span. Trip counts stay in the table as evidence. They do "
        "not enter the service score. I then placed every local bus stop within 250 m of a station, using "
        "the latest open feed from each of 14 municipal operators, and measured the scheduled wait from an "
        "arriving bus to the next train toward Union. I then built two catchments. The walk catchment is "
        "the street network within 800 m. The station shed is the area closer to that station than to any "
        "other, capped at 10 km. I put 2021 Census population, jobs, recent housing, work from home, and "
        "the share of commuters whose usual workplace is Toronto into those catchments. For the fare "
        "condition I used a generalized cost: the published fare to Union, plus a value of time applied to "
        "the scheduled ride and to half the AM headway. The value of time is half the shed's median "
        "household income, spread over 2,080 hours. Only after that table was complete did I score the "
        "stations and name a primary likely constraint."
    )
    lines.append("")
    lines.append("## The two analyses")
    lines.append("")
    lines.append(
        f"Analysis 1 is a quadrant, not a cause. I scored {len(scored)} stations. Union Station is the "
        "network destination, and Stratford is outside the tracted census area, so I left both out of the "
        f"ranking. The median market score is {_n(meta.get('market_median'), 1)} and the median conditions "
        f"score is {_n(meta.get('conditions_median'), 1)}. A station above the market median and below the "
        "conditions median is a priority: the market is ahead of the conditions. I also mark a station that "
        f"sits within {C.NEAR_CUT_POINTS} points of either median, because that station would change class "
        "if the cut moved by a small amount."
    )
    lines.append("")
    lines.append(
        "Analysis 2 names the primary likely constraint for those priority stations. I compared each "
        f"condition with the {meta.get('reference_n')} stations that have both a strong market and strong "
        "conditions. The deficit is the number of points the station sits below that reference median. "
        "The largest deficit is the primary likely constraint. If the second deficit is within 10 points, "
        "I call it a tie and I do not recommend a single capital project. Land use is the label when recent "
        "housing growth carries the market score while the walk catchment is still thin."
    )
    lines.append("")
    if priority.empty:
        lines.extend(
            [
                "## What I found",
                "",
                "The median split did not leave a priority set. I would inspect the scores before treating that as a finding that every station is fine.",
                "",
            ]
        )
    else:
        lines.extend(_findings(priority, meta, names, table))
    lines.extend(_evidence(table))
    lines.extend(_kitchener(table, meta))
    lines.append("## What I would measure next")
    lines.append("")
    lines.append(
        "If a local connection is shortened, I would track the scheduled AM-peak wait and, once boardings "
        "exist, boardings at that station against another station on the same line. If span of service is "
        "added, I would track off-peak and weekend boardings. I would not read a change as the effect of "
        "the intervention without accounting for return to office, construction, and the April 2024 service "
        "increase, which added trips on Lakeshore West, Lakeshore East, Kitchener, Stouffville, and Milton. "
        "That increase is an evaluation design, not a result I can estimate from open data."
    )
    lines.append("")
    lines.append("## What this does not say")
    lines.append("")
    lines.append(
        "A weak score is a weak condition, not a low ridership number. The 2021 Census counts commuting "
        "during a period of high work from home, and I use that as a feature of the market rather than "
        "correcting it away. Parking is a 2019 snapshot. Transfer waits are scheduled, not observed. "
        "Catchments and municipal commute shares are approximations. Service and parking were supplied "
        "with ridership in mind, so I do not treat a score as a causal effect. The generalized cost uses "
        "the one published fare in the GTFS file, a stated value of time, and a scheduled wait. It is not "
        "the fare a PRESTO card charges, and it is not the cost of a whole trip from the traveller's door."
    )
    lines.append("")
    path = C.REPORTS / "executive_brief.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")
    return path
