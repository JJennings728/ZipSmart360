# Reference Architecture

## Objective

Demonstrate a controlled AI-assisted review path for aviation and specialty-insurance submissions without delegating underwriting authority to a model.

## Logical flow

    [Submission package]
           |
           v
    [Local input validation]
           |
           v
    [Data minimization / approved fields]
           |
           v
    [OpenAI Responses API]
           |
           v
    [JSON response parser + output validation]
           |
           v
    [Exception / completeness package]
           |
           v
    [Authorized human reviewer]
           |
           +--> Request information
           +--> Refer
           +--> Continue normal underwriting process

## Components

### 1. Input layer

The reference input is structured JSON representing a synthetic submission. A production implementation may need controlled ingestion of documents, spreadsheets, policy wordings, loss runs, exposure schedules, or approved system records.

Production ingestion should preserve source provenance so reviewers can trace model-supported observations to authoritative records.

### 2. Deterministic pre-check

Before any model call, the application checks for required top-level sections and records missing fields. Straightforward validation remains deterministic rather than being delegated to a generative model.

### 3. Model-assisted analysis

The application sends a minimized representation of the submission to the OpenAI Responses API with instructions to separate facts from assumptions, identify missing information, flag rather than decide risk/wording issues, avoid consequential determinations, and require human review.

### 4. Output validation

The application expects JSON output and performs basic structural validation before presenting it to a reviewer. A production implementation should use stronger schema enforcement, retry/error handling, telemetry, and evaluation gates.

### 5. Human decision point

The output is preparation material. An authorized underwriter or other qualified customer reviewer remains responsible for consequential decisions.

## Production integration options

Depending on customer discovery, the workflow could be implemented as an analyst-facing review application, a controlled service embedded in an underwriting workbench, an API-connected workflow feeding an existing system, or a delegated knowledge-work flow with an explicit human approval gate.

The correct surface and deployment model should be selected only after customer workflow, security, data, governance, and integration requirements are validated.

## Failure handling

A production design should define handling for unavailable or malformed source files, incomplete data, model/API errors, invalid JSON/schema failure, unsupported model statements, conflicting source records, missing reviewer authority, and unavailable downstream systems.

On failure, the safe default is to stop progression and route the item to a human reviewer.