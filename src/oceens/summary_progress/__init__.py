"""Avancement de la génération des synthèses d'un sondage.

Une seule question : où en sont les synthèses de ce sondage, et combien de
temps reste-t-il ? Les tableaux de bord la posent à `progress` et ne comptent
plus eux-mêmes les lignes de `summaries`.
"""

from oceens.summary_progress._progress import SurveyProgress, progress

__all__ = ["SurveyProgress", "progress"]
