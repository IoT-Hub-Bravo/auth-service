# Microservice-Template

This repository serves as a **template for Django microservices**, organized in a feature-based structure. It is designed for easy scaling, clean separation of concerns, and consistent app layout.

---

## Project Structure
```
Microservice-Template/
│
├─ src/
│ ├─ core/ # Django settings and configuration (settings.py, wsgi.py, etc.)
│ │
│ ├─ apps/ # Business domains (users, telemetry, rules, etc.)
│ │
│ │ ├─ orders/
│ │ ├─ api/ # Serializers, Views (Interface Adapters)
│ │ │
│ │ ├─ services/ # Business logic (Use Cases)
│ │ │
│ │ ├─ models/ # Database schemas (Entities)
│ │ │
│ │ ├─ tests/ # Unit, Integration and E2E tests
│ │ 
│ ├─ common/ # Middleware, utils, base classes
│ │
│ ├─ tasks/ # Celery tasks for asynchronous processing
│
├─ docker/ # Dockerfiles for different environments
│
├─ scripts/ # CI/CD scripts, migrations, utilities
│
├─ .env.example # Sample environment variables file
│
├─ docker-compose.yml # Docker compose config
│
├─ pyproject.toml / requirements.txt # Dependency management files
```


---

### Folder descriptions

| Folder        | Description                                                             |
|---------------|-------------------------------------------------------------------------|
| `core/`       | Central Django configuration including settings, WSGI/ASGI entry points |
| `apps/`       | Business domains organized by feature (users, telemetry, rules, etc.)  |
| `api/`        | Interface adapters: views and serializers managing HTTP requests        |
| `services/`   | Business logic layer implementing use cases and domain rules            |
| `models.py`   | Database schema definitions (Entities)                                 |
| `common/`     | Shared middleware, utility functions, and base classes                  |
| `tasks/`      | Asynchronous task definitions using Celery                             |
| `tests/`      | Automated tests including unit, integration, and end-to-end            |
| `docker/`     | Docker configurations and files for various environments               |
| `scripts/`    | Automation scripts for CI/CD and database migrations                   |

---

This structure supports:

- Clear separation between configuration, business logic, and interface layers  
- Easy scaling by adding new domain apps under `apps/`  
- Organized asynchronous tasks and testing  
- Environment-specific Docker configurations  

---
