# OcéEns

EPF's course-evaluation platform: *sondages* are created per program, students answer them, and the answers are exported, visualised and summarised.

## Language boundary

The project's working language is English: code identifiers, issues, ADRs and documentation. Code comments and docstrings are still mostly in French. The application is French: its pages, labels and messages are in French, and stay so.

Documentation keeps the product's French vocabulary where the application uses it, in italics (*sondage*, *synthèse*), and quotes interface labels exactly as they are displayed ("Se connecter", "Changer d'utilisateur"). Everything else is written in English. Terms below give the English name used in the code next to the French one used in the product.

## Language

### Surveys and summaries

**Sondage** (code: `Survey`):
A questionnaire for one program, semester and school year, answered by the students enrolled in it. It is open (students can answer) or closed (results can be summarised).
_Avoid_: poll, form

**Synthèse** (code: `Summary`):
An LLM-written summary of the open answers to one question, or to one module and teacher in a module section. Produced by the summaries daemon from a closed *sondage*.
_Avoid_: digest, report

**Verbatim**:
One free-text answer, as the student wrote it. A *synthèse* is built from the verbatims of a question.

### Authentication

**Development sign-in** (`AUTH_MODE=dev`):
Sign-in with no identity provider: you choose a user's e-mail address and are signed in as that user, with no proof of identity. It only exists when `AUTH_MODE=dev` and must never be used in production. The interface calls it *connexion de développement*.
_Avoid_: impersonation, spoofing, fake login
