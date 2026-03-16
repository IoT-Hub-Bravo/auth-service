# IoT Hub Auth Service

Authentication and authorization service for the IoT Hub platform.

## Purpose

The Auth Service is responsible for identity and access management across the platform.  
It manages users, authentication flows, authorization primitives, and token-related concerns.

## Responsibilities

- user management
- authentication
- authorization
- token issuance and validation
- identity-related lifecycle events
- access control primitives for other platform services

## Owned data

- users
- authentication credentials
- roles and permissions
- identity metadata

## Integrations

### Inbound
- frontend
- API gateway
- internal platform clients

### Outbound
- audit flow for important identity-related actions
- other services through token validation or identity context propagation

## Technology

- Django
- PostgreSQL
- Docker
