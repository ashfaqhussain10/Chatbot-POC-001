"""
Server-side flow validation (AP-03). The frontend mirrors these for instant feedback,
but the server is the source of truth on activation. Rule IDs match frontend_spec.md §8d.
"""


def validate_flow(tenant):
    """Return {valid, errors, warnings} for a tenant's flow."""
    steps = list(tenant.steps.all().prefetch_related("options"))
    errors, warnings = [], []

    starts = [s for s in steps if s.is_start]
    if len(starts) == 0:
        errors.append({"code": "V-01", "message": "No start step."})
    elif len(starts) > 1:
        errors.append({"code": "V-02", "message": "More than one start step."})

    step_ids = {s.id for s in steps}
    adjacency = {}
    for s in steps:
        options = list(s.options.all())
        adjacency[s.id] = [o.next_step_id for o in options if o.next_step_id]
        for o in options:
            if o.next_step_id is not None and o.next_step_id not in step_ids:
                errors.append({"code": "V-03", "message": f"Step '{s.label}' links to a missing step."})
            if len(o.button_label) > 20:
                warnings.append({"code": "V-05", "message": f"Button label too long on '{s.label}'."})
        if len(options) > 3:
            warnings.append({"code": "V-06", "message": f"Step '{s.label}' has >3 options (sent as a list)."})

    # V-04 unreachable: walk from the (single) start step.
    if len(starts) == 1:
        reachable, frontier = set(), [starts[0].id]
        while frontier:
            cur = frontier.pop()
            if cur in reachable:
                continue
            reachable.add(cur)
            frontier.extend(adjacency.get(cur, []))
        for s in steps:
            if s.id not in reachable:
                errors.append({"code": "V-04", "message": f"Step '{s.label}' is unreachable from start."})

    return {"valid": not errors, "errors": errors, "warnings": warnings}
