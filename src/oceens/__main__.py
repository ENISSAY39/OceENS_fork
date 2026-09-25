"""Point d'entrée `oceens` (et `python -m oceens`) : sert l'application.

L'application est passée à uvicorn par son chemin d'import, sans être importée
ici : uvicorn configure la journalisation avant de charger `oceens.main`,
exactement comme `uvicorn oceens.main:app` en ligne de commande. L'importer
d'abord ferait tourner le code de démarrage (avertissements de `core.auth`,
niveau DEBUG de `core.dependencies`) avant cette configuration, qui l'écraserait.
"""

import uvicorn


def run():
    """Sert l'application sur toutes les interfaces, port 8000."""
    uvicorn.run(
        "oceens.main:app",
        host="0.0.0.0",
        port=8000,
    )


if __name__ == "__main__":
    run()
