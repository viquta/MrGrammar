# I'm still building the project! 
Currently it (vers 0.0.4) does NOT have a very good NLP/AI pipeline to make it functional for real German learning.

## Acknowledgements

This project has been implemented with substantial AI assistance during development. Claude and GPT were both used to help with coding, iteration, and implementation support.

# MrGrammar

MrGrammar is a grammar-feedback platform for German language learning. The project focuses on a more active correction workflow than typical writing assistants: students should notice an error, try to fix it, receive a hint if needed, and only then see the final answer. The longer-term goal is to help teachers reduce correction workload while still getting useful insight into student progress and recurring error patterns.

## Project Status

This repository already contains a working full-stack prototype, but it is still under active development. Core flows such as authentication, submissions, feedback handling, analytics scaffolding, and the frontend app are in place, but the product still needs broader testing, refinement, and hardening before it should be treated as finished.

## Current Scope

- Django + Django REST Framework backend
- SvelteKit frontend
- PostgreSQL database
- German error detection pipeline using (local) LanguageTool server and spaCy library
- Guided correction workflow with hints and answer reveal
- Teacher and student oriented analytics foundation

## Quick Start

The easiest way to run the project locally is with Docker Compose.

```bash
docker compose up --build
```

Then open:

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000/api/`

For first-time setup, run migrations in the backend container:

```bash
docker compose exec backend python manage.py migrate
```

If you want the explanation step to work, you will also need an Ollama instance reachable by the backend container. The current Docker setup expects it through `OLLAMA_BASE_URL`, which defaults to `http://host.docker.internal:11434`.

## Documentation

More detailed project documentation is available in the [docs](docs/README.md) folder:

- [Architecture overview](docs/01-architecture-overview.md)
- [Data model](docs/02-data-model.md)
- [API reference](docs/03-api-reference.md)
- [Sequence diagrams](docs/04-sequence-diagrams.md)
- [Deployment notes](docs/05-deployment.md)

## Checklist

### Still Need To Test

- [ ] try out spacy-llm instead for only spacy
- [ ] implement specific grammar rules from my grammar book
- [ ] End-to-end student workflow from submission to correction completion
- [ ] End-to-end teacher workflow for classrooms, submissions, and analytics views
- [ ] Authentication edge cases such as token expiry, refresh, and unauthorized access
- [ ] Role-based permissions across student, teacher, and admin accounts
- [ ] NLP quality on real student German texts, especially false positives and weak hints
- [ ] Reliability of Ollama-generated explanations and fallback behavior when unavailable
- [ ] Frontend usability and accessibility, especially keyboard flow and error visibility
- [ ] Docker-based setup on a clean machine

### Still Need To Develop Or Improve

- [ ] 
- [ ] Better teacher dashboards and clearer class-level analytics
- [ ] More robust learner progress tracking over time (current is just 404)
- [ ] Stronger automated test coverage for core backend services and API flows
- [ ] Better error handling, logging, and operational diagnostics
- [ ] Security and privacy hardening for school-oriented deployment
- [ ] Configuration cleanup and environment management for development vs production
- [ ] UI polish and clearer feedback interactions in the frontend
- [ ] Documentation cleanup as the product scope stabilizes

for testing: 


<<<<<<< Updated upstream
=======
MrGrammar is a grammar-feedback platform for German language learning. The project focuses on a more active correction workflow than typical writing assistants: students should notice an error, try to fix it, receive a hint if needed, and only then see the final answer. The longer-term goal is to help teachers reduce correction workload while still getting useful insight into student progress and recurring error patterns.

## Project Status

This repository already contains a working full-stack prototype, but it is still under active development. Core flows such as authentication, submissions, feedback handling, analytics scaffolding, and the frontend app are in place, but the product still needs broader testing, refinement, and hardening before it should be treated as finished.

## Current Scope

- Django + Django REST Framework backend
- SvelteKit frontend
- PostgreSQL database
- German error detection pipeline using LanguageTool and spaCy
- Guided correction workflow with hints and answer reveal
- Teacher and student oriented analytics foundation

## Quick Start

The easiest way to run the project locally is with Docker Compose.

```bash
docker compose up --build
```

Then open:

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000/api/`

For first-time setup, run migrations in the backend container:

```bash
docker compose exec backend python manage.py migrate
```

If you want the explanation step to work, you will also need an Ollama instance reachable by the backend container. The current Docker setup expects it through `OLLAMA_BASE_URL`, which defaults to `http://host.docker.internal:11434`.

## Documentation

More detailed project documentation is available in the [docs](docs/README.md) folder:

- [Architecture overview](docs/01-architecture-overview.md)
- [Data model](docs/02-data-model.md)
- [API reference](docs/03-api-reference.md)
- [Sequence diagrams](docs/04-sequence-diagrams.md)
- [Deployment notes](docs/05-deployment.md)

## Checklist

### Still Need To Test

- [ ] try out spacy-llm instead for only spacy
- [ ] implement specific grammar rules from my grammar book?
- [ ] End-to-end student workflow from submission to correction completion
- [ ] End-to-end teacher workflow for classrooms, submissions, and analytics views
- [ ] Authentication edge cases such as token expiry, refresh, and unauthorized access
- [ ] Role-based permissions across student, teacher, and admin accounts
- [ ] NLP quality on real student German texts, especially false positives and weak hints
- [ ] Reliability of Ollama-generated explanations and fallback behavior when unavailable
- [ ] Frontend usability and accessibility, especially keyboard flow and error visibility
- [ ] Docker-based setup on a clean machine

### Still Need To Develop Or Improve

- [ ] 
- [ ] Better teacher dashboards and clearer class-level analytics
- [ ] More robust learner progress tracking over time (current is just 404)
- [ ] Stronger automated test coverage for core backend services and API flows
- [ ] Better error handling, logging, and operational diagnostics
- [ ] Security and privacy hardening for school-oriented deployment
- [ ] Configuration cleanup and environment management for development vs production
- [ ] UI polish and clearer feedback interactions in the frontend
- [ ] Documentation cleanup as the product scope stabilizes

for testing: 


>>>>>>> Stashed changes
