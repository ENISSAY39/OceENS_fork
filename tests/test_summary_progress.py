"""Avancement des synthèses d'un sondage, demandé à `progress` sur une file en mémoire."""

import pytest
from sqlmodel import Session, SQLModel, create_engine

from oceens.models import Summary
from oceens.summary_progress import progress

ONE_HOUR_THIRTY = 5_400


@pytest.fixture
def session():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def fill_queue(session, survey_id, count, http_status=0, summary_text=None):
    session.add_all(
        Summary(
            survey_id=survey_id,
            http_status=http_status,
            summary_text=summary_text,
            metadata_text=None,
        )
        for _ in range(count)
    )
    session.commit()


def test_a_survey_just_clicked_shows_about_31_min_left(session):
    fill_queue(session, survey_id=1, count=85)

    result = progress(session, 1)

    assert result.total == 85
    assert result.done == 0
    assert result.errors == 0
    assert not result.finished
    assert result.estimated_seconds_left == 1_870
    assert result.estimated_seconds_left <= ONE_HOUR_THIRTY


def test_at_the_120_s_cap_the_estimate_is_beyond_1_h_30_and_not_capped(session):
    fill_queue(session, survey_id=1, count=85)

    result = progress(session, 1, seconds_per_job=120)

    assert result.estimated_seconds_left == 10_200
    assert result.estimated_seconds_left > ONE_HOUR_THIRTY
