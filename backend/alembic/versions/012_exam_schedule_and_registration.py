"""Academic event schedule fields and exam registrations."""

from alembic import op
import sqlalchemy as sa

from backend.alembic_migration_utils import column_names, has_fk, has_index, has_table


revision = "012_exam_schedule"
down_revision = "011_waitlist_any_slot"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    ae = column_names(bind, "academic_events")

    if "time_from" not in ae:
        op.add_column("academic_events", sa.Column("time_from", sa.Time(), nullable=True))
    if "time_to" not in ae:
        op.add_column("academic_events", sa.Column("time_to", sa.Time(), nullable=True))
    if "hall" not in ae:
        op.add_column("academic_events", sa.Column("hall", sa.String(length=255), nullable=True))
    if "exam_period_id" not in ae:
        op.add_column("academic_events", sa.Column("exam_period_id", sa.Integer(), nullable=True))
    if "academic_year" not in ae:
        op.add_column(
            "academic_events",
            sa.Column("academic_year", sa.String(length=32), nullable=False, server_default="2025/2026"),
        )
        op.alter_column("academic_events", "academic_year", server_default=None)

    if not has_fk(bind, "academic_events", "fk_academic_events_exam_period"):
        op.create_foreign_key(
            "fk_academic_events_exam_period",
            "academic_events",
            "exam_periods",
            ["exam_period_id"],
            ["id"],
        )

    if not has_table(bind, "exam_registrations"):
        op.create_table(
            "exam_registrations",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("student_id", sa.Integer(), nullable=False),
            sa.Column("academic_event_id", sa.Integer(), nullable=False),
            sa.Column(
                "status",
                sa.Enum("REGISTERED", "CANCELLED", name="examregistrationstatus"),
                nullable=False,
            ),
            sa.Column("registered_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["academic_event_id"], ["academic_events.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("student_id", "academic_event_id", name="uq_exam_reg_student_event"),
        )

    if has_table(bind, "exam_registrations"):
        if not has_index(bind, "exam_registrations", "ix_exam_registrations_student_id"):
            op.create_index(
                "ix_exam_registrations_student_id",
                "exam_registrations",
                ["student_id"],
                if_not_exists=True,
            )
        if not has_index(bind, "exam_registrations", "ix_exam_registrations_academic_event_id"):
            op.create_index(
                "ix_exam_registrations_academic_event_id",
                "exam_registrations",
                ["academic_event_id"],
                if_not_exists=True,
            )


def downgrade() -> None:
    op.drop_index("ix_exam_registrations_academic_event_id", table_name="exam_registrations")
    op.drop_index("ix_exam_registrations_student_id", table_name="exam_registrations")
    op.drop_table("exam_registrations")
    op.execute(sa.text("DROP TYPE IF EXISTS examregistrationstatus"))

    op.drop_constraint("fk_academic_events_exam_period", "academic_events", type_="foreignkey")
    op.drop_column("academic_events", "academic_year")
    op.drop_column("academic_events", "exam_period_id")
    op.drop_column("academic_events", "hall")
    op.drop_column("academic_events", "time_to")
    op.drop_column("academic_events", "time_from")
