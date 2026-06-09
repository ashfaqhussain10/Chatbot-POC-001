"""
Flow engine (C-03) — the rule-based "brain".

Given one inbound message (a button tap or free text), it advances the customer's
session and returns the list of outbound messages to send. It is **stateless**: all
state is read from / written to the DB, inside a transaction with select_for_update on
the session row so concurrent messages for one session serialize (D-105).

Scope: pure flow logic. It does NOT parse webhooks (C-01) or call the Meta API (C-04) —
callers pass a normalised message and send the returned outbounds. Handoff email
delivery is the handoff service (C-05 / D1-24); here we only offer/transition.
"""
from django.db import transaction

from apps.conversations.models import Message, Session
from apps.conversations.services import get_or_create_session
from apps.handoff.services import trigger_handoff


def _render_step(step):
    return {
        "kind": "step",
        "text": step.message_text,
        "buttons": [o.button_label for o in step.options.all()],
    }


def _msg(kind, text, buttons=None):
    return {"kind": kind, "text": text, "buttons": buttons or []}


def handle_inbound(tenant, channel, customer_identifier, *, text=None, button_label=None):
    """Advance the session for one inbound message; return outbound messages (list of dicts)."""
    outbounds = []
    with transaction.atomic():
        session, created = get_or_create_session(tenant, channel, customer_identifier)
        # Lock the row so concurrent inbound messages for this session serialize (D-105).
        session = Session.objects.select_for_update().get(pk=session.pk)

        Message.objects.create(
            session=session,
            direction=Message.Direction.INBOUND,
            content=text or button_label or "",
            channel=channel,
        )

        start = tenant.steps.filter(is_start=True).first()

        # 1) First contact → greeting then the start step (FR-05).
        if created:
            if tenant.greeting_message:
                outbounds.append(_msg("greeting", tenant.greeting_message))
            if start:
                session.current_step = start
                session.save(update_fields=["current_step", "updated_at"])
                outbounds.append(_render_step(start))
            return _finish(session, outbounds)

        # 2) Handoff was offered → waiting for the tap (FR-11/13).
        if session.awaiting_handoff:
            if button_label is not None:
                session.status = Session.Status.HANDED_OFF
                session.awaiting_handoff = False
                session.save(update_fields=["status", "awaiting_handoff", "updated_at"])
                trigger_handoff(session)  # email the business (D1-24 / FR-11)
                outbounds.append(_msg("confirmation", "Thanks — a human will be in touch shortly."))
            else:
                outbounds.append(_msg("handoff_offer", "Would you like to talk to a human?", ["Talk to a human"]))
            return _finish(session, outbounds)

        # 3) Deleted-step recovery (ERR-04): current step was SET_NULL'd → reset to start.
        if session.current_step_id is None:
            session.current_step = start
            session.save(update_fields=["current_step", "updated_at"])
            if tenant.greeting_message:
                outbounds.append(_msg("greeting", tenant.greeting_message))
            if start:
                outbounds.append(_render_step(start))
            return _finish(session, outbounds)

        # 4) Free text → re-prompt current step; do not advance (FR-08).
        if button_label is None:
            outbounds.append(_render_step(session.current_step))
            return _finish(session, outbounds)

        # 5) Button tap → find the matching option.
        option = session.current_step.options.filter(button_label=button_label).first()
        if option is None:
            outbounds.append(_render_step(session.current_step))  # unknown button → re-prompt
            return _finish(session, outbounds)

        # 6) Terminal branch (FR-10): offer handoff, or send closing + complete (FR-12).
        if option.next_step is None:
            if tenant.handoff_enabled:
                session.awaiting_handoff = True
                session.save(update_fields=["awaiting_handoff", "updated_at"])
                outbounds.append(_msg("handoff_offer", "Would you like to talk to a human?", ["Talk to a human"]))
            else:
                session.status = Session.Status.COMPLETED
                session.current_step = None
                session.save(update_fields=["status", "current_step", "updated_at"])
                outbounds.append(_msg("closing", tenant.closing_message or "Thanks for chatting!"))
            return _finish(session, outbounds)

        # 7) Non-terminal → advance and render the next step (FR-07/09).
        session.current_step = option.next_step
        session.save(update_fields=["current_step", "updated_at"])
        outbounds.append(_render_step(option.next_step))
        return _finish(session, outbounds)


def _finish(session, outbounds):
    for ob in outbounds:
        Message.objects.create(
            session=session,
            direction=Message.Direction.OUTBOUND,
            content=ob.get("text", ""),
            channel=session.channel,
        )
    return outbounds
