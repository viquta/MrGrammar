# MrGrammar — Technical Documentation

Comprehensive technical documentation for MrGrammar, a pedagogically driven grammar-feedback platform for German-language learners.

---

## Table of Contents

| # | Document | Description |
|---|----------|-------------|
| 1 | [Architecture Overview](01-architecture-overview.md) | System purpose, technology stack, layered architecture, role-based access control, design patterns, and external integrations. |
| 2 | [Data Model](02-data-model.md) | All seven Django models with field tables, constraints, enumerations, and relationship descriptions. |
| 3 | [API Reference](03-api-reference.md) | Complete REST API specification — endpoints, permissions, request/response schemas, status codes, and examples. |
| 4 | [Sequence Diagrams](04-sequence-diagrams.md) | Three core workflows: authentication, submission & NLP analysis, and guided correction — with step-by-step narratives. |
| 5 | [Deployment & Infrastructure](05-deployment.md) | Docker Compose services, port mapping, environment variables, volumes, and network architecture. |

---

## UML Diagrams

All diagrams are in Draw.io XML format (`.drawio`). Open them with:
- **VS Code**: Install the [Draw.io Integration](https://marketplace.visualstudio.com/items?itemName=hediet.vscode-drawio) extension
- **Browser**: Upload to [diagrams.net](https://app.diagrams.net)

| Diagram | File | Type |
|---------|------|------|
| Class Diagram | [diagrams/class-diagram.drawio](diagrams/class-diagram.drawio) | UML Class Diagram — 7 models, 5 enumerations, associations with cardinality |
| Auth Sequence | [diagrams/sequence-auth.drawio](diagrams/sequence-auth.drawio) | UML Sequence — Registration → Login → JWT lifecycle |
| Submission Sequence | [diagrams/sequence-submission.drawio](diagrams/sequence-submission.drawio) | UML Sequence — Submit text → NLP analysis → Error display |
| Correction Sequence | [diagrams/sequence-correction.drawio](diagrams/sequence-correction.drawio) | Legacy UML Sequence — older correction flow kept for reference until redrawn |
| Workflow Phase 1 Concept | [diagrams/my_idea_workflow_phase_1.drawio](diagrams/my_idea_workflow_phase_1.drawio) | Product workflow concept — analyze text and render grouped highlights |
| Workflow Phase 2 Concept | [diagrams/my_idea_workflow_phase_2.drawio](diagrams/my_idea_workflow_phase_2.drawio) | Product workflow concept — second try, correctness check, and hint path |
| Workflow Phase 3 Concept | [diagrams/my_idea_workflow_phase_3.drawio](diagrams/my_idea_workflow_phase_3.drawio) | Product workflow concept — third try, answer reveal, and short explanation |
| Component & Deployment | [diagrams/component-deployment.drawio](diagrams/component-deployment.drawio) | UML Component + Deployment — Docker containers, components, interfaces |

### Exporting Diagrams to PNG

To embed diagrams in documents or presentations, export each `.drawio` file to PNG:

1. Open the `.drawio` file in Draw.io (VS Code or browser)
2. **File → Export as → PNG** (or use `Ctrl+Shift+E`)
3. Save to `diagrams/exported/` with the same base name (e.g., `class-diagram.png`)

The Markdown documents reference these exported PNGs at their expected paths in `diagrams/exported/`.

---

## Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Frontend | SvelteKit + Svelte 5 + Tailwind CSS 4 | SvelteKit 2.57 |
| Backend | Django + Django REST Framework + SimpleJWT | Django 6.0 |
| NLP | LanguageTool (self-hosted) + spaCy + Ollama | — |
| Database | PostgreSQL | 16 |
| Infrastructure | Docker Compose | — |

---

## Project Structure

```
MrGrammar/
├── accounts/          # User model, authentication, role-based permissions
├── classrooms/        # Classroom and membership management
├── submissions/       # Student text submission lifecycle
├── feedback/          # Error records, correction workflow, explanation generation
├── nlp/               # LanguageTool integration, error detection pipeline
├── analytics/         # Error summary aggregation, student/classroom analytics
├── mrgrammar/         # Django project settings, URL routing
├── frontend/          # SvelteKit SPA (Svelte 5, Tailwind 4, TypeScript 6)
├── docs/              # This documentation
│   ├── diagrams/      # Draw.io UML diagrams
│   └── diagrams/exported/  # PNG exports of diagrams
├── docker-compose.yml # Multi-container orchestration
├── Dockerfile.backend # Backend container build
├── requirements.txt   # Python dependencies
└── manage.py          # Django management CLI
```
