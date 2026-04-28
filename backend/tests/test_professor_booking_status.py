"""Professor booking status transitions and idempotency."""

import pytest
from fastapi import HTTPException

from backend.db.models import Booking, BookingStatus, ConsultationType, UserRole
from backend.routers.professor import BookingStatusPatch, patch_booking_status

from .conftest import _user, future_session


class TestProfessorPatchBookingStatus:
    async def test_active_to_attended_ok(self, db, student, professor, course, enrolled):
        cs = future_session(professor.id, course.id, ConsultationType.general)
        db.add(cs)
        await db.flush()
        b = Booking(
            student_id=student.id,
            session_id=cs.id,
            status=BookingStatus.active,
            group_size=1,
        )
        db.add(b)
        await db.flush()

        out = await patch_booking_status(
            b.id,
            BookingStatusPatch(status=BookingStatus.attended),
            db,
            professor,
        )
        assert out == {"ok": True}
        await db.refresh(b)
        assert b.status == BookingStatus.attended

    async def test_active_to_no_show_ok(self, db, student, professor, course, enrolled):
        cs = future_session(professor.id, course.id, ConsultationType.general)
        db.add(cs)
        await db.flush()
        b = Booking(student_id=student.id, session_id=cs.id, status=BookingStatus.active, group_size=1)
        db.add(b)
        await db.flush()

        await patch_booking_status(
            b.id,
            BookingStatusPatch(status=BookingStatus.no_show),
            db,
            professor,
        )
        await db.refresh(b)
        assert b.status == BookingStatus.no_show

    async def test_active_to_cancelled_ok(self, db, student, professor, course, enrolled):
        cs = future_session(professor.id, course.id, ConsultationType.general)
        db.add(cs)
        await db.flush()
        b = Booking(student_id=student.id, session_id=cs.id, status=BookingStatus.active, group_size=1)
        db.add(b)
        await db.flush()

        await patch_booking_status(
            b.id,
            BookingStatusPatch(status=BookingStatus.cancelled),
            db,
            professor,
        )
        await db.refresh(b)
        assert b.status == BookingStatus.cancelled

    async def test_idempotent_same_status(self, db, student, professor, course, enrolled):
        cs = future_session(professor.id, course.id, ConsultationType.general)
        db.add(cs)
        await db.flush()
        b = Booking(student_id=student.id, session_id=cs.id, status=BookingStatus.attended, group_size=1)
        db.add(b)
        await db.flush()

        out = await patch_booking_status(
            b.id,
            BookingStatusPatch(status=BookingStatus.attended),
            db,
            professor,
        )
        assert out == {"ok": True}

    async def test_invalid_transition_attended_to_active(self, db, student, professor, course, enrolled):
        cs = future_session(professor.id, course.id, ConsultationType.general)
        db.add(cs)
        await db.flush()
        b = Booking(student_id=student.id, session_id=cs.id, status=BookingStatus.attended, group_size=1)
        db.add(b)
        await db.flush()

        with pytest.raises(HTTPException) as exc:
            await patch_booking_status(
                b.id,
                BookingStatusPatch(status=BookingStatus.active),
                db,
                professor,
            )
        assert exc.value.status_code == 400
        assert "transition" in (exc.value.detail or "").lower()

    async def test_invalid_transition_cancelled_to_attended(self, db, student, professor, course, enrolled):
        cs = future_session(professor.id, course.id, ConsultationType.general)
        db.add(cs)
        await db.flush()
        b = Booking(student_id=student.id, session_id=cs.id, status=BookingStatus.cancelled, group_size=1)
        db.add(b)
        await db.flush()

        with pytest.raises(HTTPException) as exc:
            await patch_booking_status(
                b.id,
                BookingStatusPatch(status=BookingStatus.attended),
                db,
                professor,
            )
        assert exc.value.status_code == 400

    async def test_patch_unknown_booking_404(self, db, professor, course, enrolled):
        with pytest.raises(HTTPException) as exc:
            await patch_booking_status(
                999_999,
                BookingStatusPatch(status=BookingStatus.attended),
                db,
                professor,
            )
        assert exc.value.status_code == 404

    async def test_active_to_waitlist_forbidden(self, db, student, professor, course, enrolled):
        cs = future_session(professor.id, course.id, ConsultationType.general)
        db.add(cs)
        await db.flush()
        b = Booking(student_id=student.id, session_id=cs.id, status=BookingStatus.active, group_size=1)
        db.add(b)
        await db.flush()

        with pytest.raises(HTTPException) as exc:
            await patch_booking_status(
                b.id,
                BookingStatusPatch(status=BookingStatus.waitlist),
                db,
                professor,
            )
        assert exc.value.status_code == 400

    async def test_wrong_professor_forbidden(self, db, student, professor, course, enrolled):
        other = _user(UserRole.professor, "Other", "Prof")
        db.add(other)
        await db.flush()
        cs = future_session(professor.id, course.id, ConsultationType.general)
        db.add(cs)
        await db.flush()
        b = Booking(student_id=student.id, session_id=cs.id, status=BookingStatus.active, group_size=1)
        db.add(b)
        await db.flush()

        with pytest.raises(HTTPException) as exc:
            await patch_booking_status(
                b.id,
                BookingStatusPatch(status=BookingStatus.attended),
                db,
                other,
            )
        assert exc.value.status_code == 403
