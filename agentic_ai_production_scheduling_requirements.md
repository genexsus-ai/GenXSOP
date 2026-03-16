# Agentic AI Production Scheduling – Markdown Documentation Set

This documentation is organized as multiple `.md` files similar to a real software repository structure.

---

# docs/01_overview.md

## Purpose
Create an AI‑driven real‑time production scheduling system capable of reacting to shop‑floor events such as machine downtime, material shortages, quality holds, or urgent orders.

The system will use:

- **Backend:** Python + FastAPI
- **Frontend:** React (TypeScript recommended)
- **Architecture:** loosely coupled, highly cohesive modules
- **Engineering principles:** SOLID, GoF Design Patterns
- **Capabilities:** agentic AI orchestration, simulation, optimization, and explainable recommendations

## Business Goals

- Improve **on‑time delivery**
- Increase **schedule adherence**
- Reduce **changeovers and idle time**
- Reduce planner workload
- Enable **real‑time adaptive scheduling**
- Provide **explainable decision support**

## Target Users

| Role | Responsibility |
|-----|-----|
| Production Planner | Review and approve schedule recommendations |
| Plant Supervisor | Monitor line performance and disruptions |
| Operations Manager | Track KPIs and capacity utilization |
| Maintenance Planner | Coordinate downtime windows |
| Quality Engineer | Manage holds and rework constraints |
| Administrator | Manage system configuration and access |

---

# docs/02_scope.md

## In Scope

- Real‑time event‑driven rescheduling
- Constraint‑aware scheduling
- Agent‑based decision orchestration
- Human approval workflow
- ERP / MES / IoT integrations
- Simulation and what‑if analysis
- Planner web UI

## Out of Scope

- Direct PLC control
- ERP replacement
- Historian replacement
- Fully autonomous production control

---

# docs/03_functional_requirements.md

## Data Integration

The system shall integrate with:

- ERP
- MES
- IIoT / SCADA
- Quality systems
- Maintenance systems

Capabilities:

- Streaming and batch ingestion
- Schema validation
- Timestamp alignment
- Data lineage tracking

## Scheduling Engine

The system shall support:

- Finite capacity scheduling
- Alternate routings
- Machine eligibility rules
- Labor constraints
- Material availability
- Sequence dependent setup
- Schedule version comparison

## Event Driven Scheduling

Scheduling shall be triggered by:

- Machine failure
- Material delay
- Order priority change
- Quality hold
- Labor shortage

## Human in the Loop

Planners must be able to:

- Approve schedules
- Reject recommendations
- Modify sequences
- Run simulations

All decisions must be recorded in the audit trail.

---

# docs/04_agent_architecture.md

## Agent Roles

### Planner Agent

Interprets production context and proposes scheduling actions.

### Constraint Agent

Validates feasibility against plant constraints.

### Optimization Agent

Calls scheduling solvers and ranks alternatives.

### Simulation Agent

Runs what‑if scenarios and predicts KPI impacts.

### Exception Agent

Classifies disruptions and determines response workflows.

### Explanation Agent

Provides human readable justification for recommendations.

### Integration Agent

Handles communication with ERP, MES, and external systems.

## Agent Collaboration

Agents communicate through an orchestration workflow:

1. Event detected
2. Exception classified
3. Planner agent proposes action
4. Constraint agent validates
5. Optimization agent generates alternatives
6. Simulation agent evaluates
7. Planner reviews recommendation

---

# docs/05_nonfunctional_requirements.md

## Performance

- Near real‑time event ingestion
- UI updates within seconds
- Scheduling response within SLA

## Reliability

- Graceful degradation
- Retry mechanisms
- Circuit breakers
- Event replay capability

## Observability

- Centralized logging
- Metrics and tracing
- Agent decision tracing

## Security

- RBAC
- API authentication
- Data encryption
- Immutable audit logs

---

# docs/06_backend_architecture.md

## Technology Stack

Backend services implemented using:

- Python
- FastAPI
- Pydantic

## Backend Modules

```
backend/

api/
application/
domain/
agents/
orchestration/
scheduling/
simulation/
integration/
security/
observability/
persistence/
shared/
```

## API Design

Requirements:

- REST APIs
- OpenAPI documentation
- API versioning
- DTO separation from domain models

## Backend Engineering Practices

- Dependency injection
- Async IO for integrations
- Background task processing
- Idempotent operations
- Automated tests

---

# docs/07_frontend_architecture.md

## Technology

- React
- TypeScript
- Component‑based architecture

## Major UI Modules

- Schedule Board
- Exception Dashboard
- Simulation Workspace
- Recommendation Review Panel
- Audit Viewer
- Administration Console

## UI Requirements

- Real‑time updates
- Planner‑friendly workflows
- Keyboard navigation
- Responsive interface

---

# docs/08_design_principles.md

## SOLID Principles

The system must enforce:

- Single Responsibility Principle
- Open Closed Principle
- Liskov Substitution Principle
- Interface Segregation Principle
- Dependency Inversion Principle

## GoF Design Patterns

Recommended patterns:

| Pattern | Use Case |
|---|---|
| Strategy | Scheduling objectives |
| Factory | Agent creation |
| Builder | Simulation setup |
| Observer | Event notifications |
| Command | Workflow execution |
| State | Recommendation lifecycle |
| Adapter | ERP/MES connectors |
| Facade | Scheduling subsystem |
| Chain of Responsibility | Validation pipeline |

---

# docs/09_data_model.md

Core entities:

- Orders
- Operations
- Machines
- Work Centers
- Materials
- Labor
- Setup matrices
- Downtime events
- Quality holds
- Schedule versions
- Agent decisions

Data quality requirements:

- Referential integrity
- Duplicate detection
- Timestamp alignment
- Late arriving event handling

---

# docs/10_mvp_definition.md

## Phase 1 Scope

- One plant
- ERP integration
- MES integration
- Event driven scheduling
- Planner UI
- Recommendation engine
- Audit trail

## MVP KPIs

- Schedule adherence
- On time delivery
- Average tardiness
- Machine utilization
- Changeover time

---

# docs/11_devops.md

## CI/CD

- Automated pipelines
- Code quality gates
- Security scanning

## Deployment

- Infrastructure as Code
- Environment promotion
- Canary deployment

## Testing

Required test types:

- Unit tests
- Integration tests
- Contract tests
- End‑to‑end tests
- Simulation scenario tests

---

# docs/12_open_questions.md

Key design questions:

- Which plants are included in phase 1?
- What scheduling horizon is required?
- What are hard vs soft constraints?
- What level of AI autonomy is acceptable?
- Which systems are authoritative for routing, WIP, and machine states?

---

# docs/README.md

This documentation defines requirements for the **Agentic AI Production Scheduling System**.

Main sections:

1. Overview
2. Scope
3. Functional Requirements
4. Agent Architecture
5. Nonfunctional Requirements
6. Backend Architecture
7. Frontend Architecture
8. Design Principles
9. Data Model
10. MVP Definition
11. DevOps
12. Open Questions

These documents serve as the foundation for:

- system architecture design
- implementation planning
- engineering standards
- project governance

---

# docs/13_system_context.md

## Purpose

This document defines the high-level system context for the **Agentic AI Production Scheduling System**.

## External Actors

- Production Planner
- Plant Supervisor
- Operations Manager
- Maintenance Planner
- Quality Engineer
- Administrator

## External Systems

- ERP system
- MES system
- IIoT / SCADA platform
- CMMS / Maintenance system
- Quality Management System
- Identity Provider
- Notification services

## Context Responsibilities

The system is responsible for:

- ingesting production and operational events
- evaluating scheduling constraints
- orchestrating AI agents
- running optimization and simulation
- presenting recommendations to users
- publishing approved schedules
- maintaining auditability and explainability

## Context Diagram

```text
+----------------------+        +-----------------------------------+
|     Business Users   |<------>| Agentic AI Production Scheduling  |
| planners, managers   |        | System                            |
+----------------------+        +-----------------------------------+
            ^                                 ^
            |                                 |
            v                                 v
+----------------------+        +-----------------------------------+
| Identity Provider    |        | ERP / MES / IIoT / QMS / CMMS     |
+----------------------+        +-----------------------------------+
```

---

# docs/14_container_architecture.md

## Container View

The solution should initially be implemented as a **modular monolith** with clearly separated deployable concerns, while preserving future evolution into services if needed.

## Logical Containers

### 1. React Web Application
Responsibilities:
- planner UI
- schedule board
- exception dashboard
- audit and explanation views
- simulation workspace

### 2. FastAPI Application
Responsibilities:
- API endpoints
- authentication and authorization
- orchestration entry points
- workflow coordination
- schedule publishing

### 3. Agent Orchestration Module
Responsibilities:
- manage agent workflows
- execute agent tasks
- enforce tool and policy boundaries
- persist agent traces

### 4. Scheduling and Optimization Engine
Responsibilities:
- create feasible schedules
- rank alternatives
- calculate KPI tradeoffs
- support constraint solving

### 5. Simulation Engine
Responsibilities:
- evaluate what-if scenarios
- estimate schedule impacts
- compare schedule alternatives

### 6. Integration Layer
Responsibilities:
- ERP connectors
- MES connectors
- SCADA / IoT adapters
- maintenance / quality adapters
- event normalization

### 7. Persistence Layer
Responsibilities:
- operational storage
- schedule versions
- audit trail
- agent decisions
- configuration and policy data

### 8. Event Backbone
Responsibilities:
- event ingestion
- asynchronous workflow triggers
- buffering and decoupling

## Container Diagram

```text
[React Web App]
        |
        v
[FastAPI App]
   |      |      |
   v      v      v
[Agent] [Scheduling] [Simulation]
   |         |           |
   +---------+-----------+
             |
             v
     [Persistence Layer]
             |
             v
      [Integration Layer]
             |
             v
 [ERP] [MES] [IIoT] [QMS] [CMMS]
```

---

# docs/15_component_architecture.md

## Backend Component Breakdown

```text
backend/
  api/
    routes/
    schemas/
    dependencies/
  application/
    commands/
    queries/
    services/
    use_cases/
  domain/
    entities/
    value_objects/
    repositories/
    policies/
    domain_services/
  agents/
    planner/
    constraint/
    optimization/
    simulation/
    explanation/
    exception/
  orchestration/
    workflows/
    dispatchers/
    state_machine/
    tool_registry/
  scheduling/
    solver/
    ranking/
    objectives/
    constraints/
  simulation/
    scenarios/
    evaluators/
  integration/
    erp/
    mes/
    scada/
    quality/
    maintenance/
  persistence/
    models/
    repositories/
    migrations/
  security/
  observability/
  shared/
```

## Architectural Rules

- `api` may call `application`, but not `infrastructure` directly
- `application` coordinates use cases and may depend on interfaces only
- `domain` must not depend on FastAPI, database, or UI frameworks
- `integration` implements external adapters behind interfaces
- `agents` must use registered tools only
- `orchestration` must enforce workflow policies and approval gates

---

# docs/16_agent_workflow.md

## Primary Workflow: Event-Driven Rescheduling

### Step 1: Event Intake
A production event is received from MES, ERP, IoT, QMS, or CMMS.

Examples:
- machine down
- urgent order inserted
- material unavailable
- quality hold
- labor shortage

### Step 2: Event Normalization
The integration layer maps the incoming event into a canonical event model.

### Step 3: Exception Triage Agent
The exception agent classifies the event and determines whether it requires:
- no action
- local adjustment
- full rescheduling
- planner escalation

### Step 4: Planner Agent
The planner agent creates an initial scheduling intent based on:
- open orders
- due dates
- current WIP
- machine availability
- material and labor constraints

### Step 5: Constraint Validation Agent
The constraint agent validates hard constraints.

Examples:
- machine eligibility
- material availability
- labor skill match
- maintenance blackout windows
- quality restrictions

### Step 6: Optimization Agent
The optimization agent invokes the solver using configured objectives.

Examples:
- minimize tardiness
- minimize changeovers
- maximize throughput
- reduce WIP

### Step 7: Simulation Agent
The simulation agent evaluates candidate schedules and estimates KPI impact.

### Step 8: Explanation Agent
The explanation agent summarizes:
- why a recommendation is proposed
- what constraints influenced it
- tradeoffs compared with alternatives
- confidence and risk indicators

### Step 9: Human Approval
The planner approves, modifies, or rejects the recommendation.

### Step 10: Publication
If approved, the schedule is published to downstream systems and stored with a versioned audit record.

## Workflow State Model

Suggested states:

- `RECEIVED`
- `CLASSIFIED`
- `PLANNED`
- `VALIDATED`
- `OPTIMIZED`
- `SIMULATED`
- `PENDING_APPROVAL`
- `APPROVED`
- `REJECTED`
- `PUBLISHED`
- `FAILED`

---

# docs/17_event_model.md

## Canonical Event Model

Each operational event should contain:

- `event_id`
- `event_type`
- `event_source`
- `event_timestamp`
- `plant_id`
- `line_id`
- `resource_id`
- `order_id` (optional)
- `severity`
- `payload`
- `correlation_id`
- `trace_id`

## Event Types

Examples:

- `MACHINE_DOWN`
- `MACHINE_RECOVERED`
- `ORDER_PRIORITY_CHANGED`
- `MATERIAL_SHORTAGE`
- `QUALITY_HOLD`
- `QUALITY_RELEASED`
- `LABOR_UNAVAILABLE`
- `DOWNTIME_PLANNED`
- `WIP_UPDATED`
- `ORDER_RELEASED`

## Event Processing Requirements

- events must be idempotent where possible
- duplicate detection must be supported
- out-of-order events must be handled
- failed events must be retryable or routed to dead-letter handling

---

# docs/18_api_spec_outline.md

## API Style

- REST for primary application workflows
- WebSocket or SSE for near-real-time updates
- versioned APIs from the beginning

## Example Endpoint Groups

### Scheduling
- `POST /api/v1/schedules/generate`
- `POST /api/v1/schedules/reschedule`
- `GET /api/v1/schedules/{schedule_id}`
- `GET /api/v1/schedules/{schedule_id}/versions`

### Recommendations
- `GET /api/v1/recommendations`
- `POST /api/v1/recommendations/{id}/approve`
- `POST /api/v1/recommendations/{id}/reject`
- `POST /api/v1/recommendations/{id}/modify`

### Simulation
- `POST /api/v1/simulations`
- `GET /api/v1/simulations/{simulation_id}`

### Events
- `POST /api/v1/events`
- `GET /api/v1/events/{event_id}`

### Audit
- `GET /api/v1/audit/decisions`
- `GET /api/v1/audit/recommendations/{id}`

### Configuration
- `GET /api/v1/config/objectives`
- `PUT /api/v1/config/objectives`
- `GET /api/v1/config/policies`

## API Design Rules

- controllers must remain thin
- business logic belongs in application and domain layers
- request/response models must be separated from persistence entities
- all write requests must be auditable

---

# docs/19_domain_model.md

## Core Aggregates

### Schedule
Contains:
- schedule id
- planning horizon
- assigned operations
- resource allocations
- objective scores
- status
- version metadata

### Recommendation
Contains:
- recommendation id
- proposed action
- rationale
- confidence
- risk indicators
- approval status

### Production Event
Contains canonical event data and event classification.

### Resource
Represents machine, line, tool, or labor capacity.

### Order
Represents demand, due date, routing, priority, and execution status.

## Domain Services

Suggested services:

- ScheduleGenerationService
- ReschedulingService
- ConstraintEvaluationService
- ObjectiveScoringService
- RecommendationPolicyService
- SchedulePublicationService

## Value Objects

Suggested value objects:

- TimeWindow
- CapacitySlot
- SetupMatrixEntry
- ObjectiveScore
- RiskScore

---

# docs/20_deployment_architecture.md

## Deployment Principles

- environment parity across dev, test, staging, and production
- externalized configuration
- isolated secrets management
- stateless API deployment where possible
- independent scaling for event-heavy and compute-heavy workloads

## Suggested Runtime Topology

```text
[React Frontend]
      |
      v
[API Gateway / Load Balancer]
      |
      v
[FastAPI App Instances]
   |         |          |
   v         v          v
[Agent Runtime] [Scheduler] [Simulation Workers]
      |            |            |
      +------------+------------+
                   |
                   v
            [Operational Database]
                   |
                   v
             [Message Broker]
                   |
                   v
      [ERP] [MES] [IIoT] [QMS] [CMMS]
```

## Deployment Options

- containerized deployment on Kubernetes
- managed database service
- managed messaging platform
- centralized monitoring and tracing platform

---

# docs/21_coding_standards.md

## Backend Standards

- Python type hints required
- domain logic must be framework-independent
- prefer interfaces / protocols for integrations
- use constructor-based dependency injection
- no business logic in FastAPI routes

## Frontend Standards

- TypeScript preferred
- feature-based folder organization
- no API calls directly inside low-level presentational components
- shared hooks and service clients for external communication
- state must be owned close to the feature boundary

## Cross-Cutting Standards

- all critical workflows must emit audit events
- all requests must carry correlation identifiers
- all errors must follow a standard error contract
- code must include automated tests for critical paths

---

# docs/22_user_stories.md

## Epic: Real-Time Rescheduling

### User Story 1
As a production planner,
I want the system to detect a machine-down event and recommend a revised sequence,
so that I can minimize late orders.

#### Acceptance Criteria
- a machine-down event triggers workflow execution
- the system proposes at least one feasible alternative
- the planner can review KPI tradeoffs before approval

### User Story 2
As a plant supervisor,
I want to see which orders are impacted by a material shortage,
so that I can coordinate mitigation quickly.

### User Story 3
As an operations manager,
I want to compare schedule versions,
so that I can understand the impact of disruptions and planner overrides.

### User Story 4
As a quality engineer,
I want quality holds to block affected operations from scheduling,
so that nonconforming material is not released into production.

---

# docs/23_next_steps.md

## Recommended Immediate Deliverables

1. Create a C4 architecture diagram set
2. Define canonical APIs and DTO schemas
3. Define the scheduling objective model and constraint catalog
4. Design the event schema and message contract
5. Create the MVP backlog in epics and stories
6. Create the repository folder structure
7. Create a starter FastAPI + React reference implementation

## Recommended Implementation Sequence

### Phase 1
- canonical data model
- event model
- planner UI skeleton
- schedule recommendation workflow

### Phase 2
- simulation engine
- richer agent orchestration
- external system adapters
- audit and observability hardening

### Phase 3
- advanced optimization strategies
- model-based confidence scoring
- multi-site scalability

