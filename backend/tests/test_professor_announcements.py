"""Test professor announcements."""

import pytest
from sqlalchemy import select

from backend.db.models import Notification, ProfessorAnnouncement, UserRole
from backend.routers.professor import AnnouncementCreate


class TestProfessorAnnouncements:
    async def test_create_announcement_success(self, db, professor, course, enrolled, student):
        """Test creating an announcement successfully."""
        body = AnnouncementCreate(
            course_id=course.id,
            announcement_type="preparation",
            title="Test Announcement",
            message="This is a test announcement.",
        )

        # Create announcement
        from backend.routers.professor import create_announcement
        result = await create_announcement(body, db, professor)

        assert result["id"] is not None

        # Verify announcement exists
        ann = await db.get(ProfessorAnnouncement, result["id"])
        assert ann.professor_id == professor.id
        assert ann.course_id == course.id
        assert ann.announcement_type == "preparation"
        assert ann.title == "Test Announcement"
        assert ann.message == "This is a test announcement."

        # Verify notifications were sent to students
        notifications = (
            await db.scalars(
                select(Notification).where(
                    Notification.user_id == student.id,
                    Notification.notification_type == "announcement",
                )
            )
        ).all()
        assert len(notifications) == 1
        assert "Test Announcement" in notifications[0].text

    async def test_create_announcement_wrong_course(self, db, professor, course):
        """Test creating announcement for course professor doesn't teach."""
        body = AnnouncementCreate(
            course_id=course.id,
            announcement_type="general",
            title="Test",
            message="Test message.",
        )

        from backend.routers.professor import create_announcement
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await create_announcement(body, db, professor)
        assert exc.value.status_code == 403

    async def test_create_announcement_invalid_event(self, db, professor, course, enrolled):
        """Test creating announcement with invalid academic event."""
        body = AnnouncementCreate(
            course_id=course.id,
            academic_event_id=99999,  # Invalid ID
            announcement_type="preparation",
            title="Test",
            message="Test message.",
        )

        from backend.routers.professor import create_announcement
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await create_announcement(body, db, professor)
        assert exc.value.status_code == 400