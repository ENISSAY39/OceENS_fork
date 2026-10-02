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


def test_the_estimate_counts_the_other_surveys_waiting_in_the_queue(session):
    fill_queue(session, survey_id=1, count=85)
    fill_queue(session, survey_id=2, count=85)

    assert progress(session, 1).estimated_seconds_left == 3_740

    fill_queue(session, survey_id=3, count=85)

    third = progress(session, 1)
    assert third.total == 85
    assert third.estimated_seconds_left == 5_610
    assert third.estimated_seconds_left > ONE_HOUR_THIRTY


def test_failed_jobs_are_errors_and_add_nothing_to_the_estimate(session):
    fill_queue(session, survey_id=1, count=10, http_status=200, summary_text="<p>ok</p>")
    fill_queue(session, survey_id=1, count=2, http_status=500)
    fill_queue(session, survey_id=1, count=4, http_status=400)
    fill_queue(session, survey_id=1, count=69)

    result = progress(session, 1)

    assert result.total == 85
    assert result.done == 10
    assert result.errors == 6
    assert not result.finished
    assert result.estimated_seconds_left == 1_518


def test_a_survey_can_be_finished_with_errors_and_an_empty_summary(session):
    fill_queue(session, survey_id=1, count=78, http_status=200, summary_text="<p>ok</p>")
    fill_queue(session, survey_id=1, count=1, http_status=200)
    fill_queue(session, survey_id=1, count=4, http_status=504)
    fill_queue(session, survey_id=1, count=2, http_status=-1)
    fill_queue(session, survey_id=2, count=85)

    result = progress(session, 1)

    assert result.finished
    assert result.done == 79
    assert result.errors == 6
    assert result.estimated_seconds_left == 0


@pytest.mark.parametrize("survey_id", [2, 999])
def test_a_survey_with_no_jobs_shows_no_progress_and_no_estimate(session, survey_id):
    fill_queue(session, survey_id=1, count=85)

    result = progress(session, survey_id)

    assert result.total == 0
    assert not result.finished
    assert result.estimated_seconds_left == 0


@pytest.mark.parametrize("seconds_per_job", [0, -22])
def test_a_duration_of_zero_or_less_is_refused(session, seconds_per_job):
    fill_queue(session, survey_id=1, count=85)

    with pytest.raises(ValueError):
        progress(session, 1, seconds_per_job=seconds_per_job)
