# Images and Diagrams

This page contains a collection of diagrams that illustrate various architectural decisions and important use cases of the DetermBot agent.

## Spec-Driven Development (SDD) Workflow

This diagram shows the workflow of using a YAML spec to generate code. The spec bypasses the natural language understanding part of the pipeline and directly feeds a canonical intent to the `TemplateBinder`.

```mermaid
graph TD
    subgraph "User"
        A[YAML/JSON Spec]
    end
    subgraph "DetermBot Pipeline"
        B(SpecValidator)
        C(TemplateBinder)
        D(ClaudeAPIAdapter)
        E(SchemaParser)
        F(DriftDetector)
    end
    A --> B;
    B --> C;
    C --> D;
    D --> E;
    E --> F;
    F --> G[DeterministicResult];
```

## Multi-Intent Request Flow

This diagram shows how a multi-intent request is split and processed by the agent.

```mermaid
graph TD
    A[Multi-Intent Request] --> B{MultiIntentSplitter};
    B --> C[Sub-Intent 1];
    B --> D[Sub-Intent 2];
    B --> E[...];

    subgraph "Agent"
        C --> F(Pipeline);
        D --> G(Pipeline);
        E --> H(Pipeline);
    end

    F --> I[Result 1];
    G --> J[Result 2];
    H --> K[...];
```

## Project Composition Flow

This diagram shows the flow of composing a project from a project spec.

```mermaid
graph TD
    A[Project Spec YAML] --> B{ProjectSpecParser};
    B --> C[ProjectSpec Object];
    C --> D{DependencyResolver};
    D --> E[Sorted Generation Items];
    E --> F{Agent};
    F --> G[Generated Code];
```
