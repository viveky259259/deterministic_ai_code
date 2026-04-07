# DetermBot: Deterministic Code Generation Agent

Welcome to the documentation for DetermBot, a specification-executing agent that produces structurally identical, semantically equivalent code every time the same intent is expressed — regardless of phrasing.

This documentation provides a comprehensive overview of the project, its architecture, and its components.

## Core Principles

- **Determinism over creativity:** Structural identity across equivalent phrasings, always.
- **Fail loudly, never silently:** Schema violations and drift events raise exceptions.
- **Separation of concerns:** Normalisation, classification, generation, and validation are independent pipeline stages.
- **Temperature lock is mandatory:** `temperature=0` on all API calls, no runtime override.
- **Specs bypass normalisation:** YAML/JSON specs skip synonym collapse.
- **One function per output:** Each pipeline run produces exactly one function.

## Getting Started

To get started with DetermBot, please refer to the [Getting Started](./getting-started.md) guide, which provides instructions on how to set up and run the project.

## Architecture

For a high-level overview of the project's architecture, please see the [Architecture](./architecture.md) page.

## Components

Detailed documentation for each component can be found in the [Components](./components/) section.
