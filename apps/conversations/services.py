from .models import Session


def get_or_create_session(tenant, channel, customer_identifier):
    """
    Return (session, created).

    Reuse the customer's ACTIVE session for this channel; if there is none, start a
    brand-new one. A completed/handed-off conversation is never reused — the next
    inbound message begins a fresh session (FR-09 / D-05).
    """
    session = (
        Session.objects.filter(
            tenant=tenant,
            channel=channel,
            customer_identifier=customer_identifier,
            status=Session.Status.ACTIVE,
        )
        .order_by("-started_at")
        .first()
    )
    if session:
        return session, False

    session = Session.objects.create(
        tenant=tenant,
        channel=channel,
        customer_identifier=customer_identifier,
        status=Session.Status.ACTIVE,
    )
    return session, True
