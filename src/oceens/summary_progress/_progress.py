from dataclasses import dataclass

from sqlmodel import Session, case, func, select

from oceens.models import Summary

# Durée moyenne d'un job, mesurée le 25/09/2026 sur 10 synthèses réussies.
# L'estimation est une somme de durées : on multiplie par la moyenne, pas par
# la médiane.
SECONDS_PER_JOB = 20


@dataclass(frozen=True)
class SurveyProgress:
    """Avancement des synthèses d'un sondage.

    `finished` signifie « plus rien en attente », pas « toutes les synthèses
    sont là » : c'est `errors` qui dit combien manquent.
    """

    done: int
    total: int
    errors: int
    estimated_seconds_left: int
    finished: bool


def progress(
    session: Session, survey_id: int, seconds_per_job: int = SECONDS_PER_JOB
) -> SurveyProgress:
    """Où en sont les synthèses de ce sondage, et combien de temps reste-t-il ?

    La table `summaries` est la file : `http_status` 0 est en attente, 200 est
    fait, toute autre valeur est une erreur. Un sondage sans job, ou qui
    n'existe pas, revient avec un `total` de 0.
    """
    if seconds_per_job <= 0:
        raise ValueError(f"seconds_per_job doit être positif, reçu {seconds_per_job}")

    total, done, pending = session.exec(
        select(
            func.count(Summary.summary_id),
            func.count(case((Summary.http_status == 200, 1))),
            func.count(case((Summary.http_status == 0, 1))),
        ).where(Summary.survey_id == survey_id)
    ).one()

    estimated_seconds_left = 0
    if pending > 0:
        # Le daemon prend la première ligne en attente, sans ordre par sondage :
        # toute la file peut passer avant la fin de ce sondage.
        queue_pending = session.exec(
            select(func.count(Summary.summary_id)).where(Summary.http_status == 0)
        ).one()
        estimated_seconds_left = queue_pending * seconds_per_job

    return SurveyProgress(
        done=done,
        total=total,
        errors=total - done - pending,
        estimated_seconds_left=estimated_seconds_left,
        finished=total > 0 and pending == 0,
    )
