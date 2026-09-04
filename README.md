# SwiftTrack — Enterprise Logistics Microservices Platform

[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![RabbitMQ](https://img.shields.io/badge/Rabbitmq-FF6600?style=for-the-badge&logo=rabbitmq&logoColor=white)](https://www.rabbitmq.com/)
[![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/postgresql-4169e1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)

## 📖 Overview

SwiftTrack is a robust, highly scalable middleware architecture prototype designed for modern e-commerce and last-mile delivery providers. It tackles complex enterprise application integration (EAI) challenges by bridging heterogeneous systems—such as legacy Client Management Systems (CMS), Route Optimization Systems (ROS), and proprietary Warehouse Management Systems (WMS)—into a unified, modern, **Event-Driven Ecosystem**.

This repository is built as a showcase of advanced distributed systems engineering. It emphasizes fault tolerance, asynchronous processing, and architectural decoupling, making it an ideal reference for enterprise-grade microservice design.

![SwiftTrack Architecture Diagram](SwiftTrack%20Arch%20Diagram.png)

---

## 🎯 The Problem vs. The Solution

### The Problem
In legacy logistics environments, systems are often tightly coupled using synchronous point-to-point connections (REST/SOAP). This leads to:
- **Cascading Failures:** If the Warehouse Management System (WMS) is down, the Order Management system fails.
- **Performance Bottlenecks:** Users are forced to wait while multiple downstream systems process an order synchronously.
- **Data Inconsistencies:** Partial failures across disparate databases lead to ghost orders and corrupted states.
- **Protocol Mismatches:** Modern web apps struggle to communicate directly with legacy SOAP or raw TCP/IP services.

### The SwiftTrack Solution
SwiftTrack introduces an **Event-Driven, Asynchronous Middleware**:
- **Decoupling via Message Broker:** Services communicate by publishing and consuming events (AMQP) via RabbitMQ, ensuring that order ingestion is instantaneous and highly available.
- **Distributed Saga Pattern:** Implements intelligent **Compensation Transactions**. If a downstream system fails, compensating events are automatically published to safely roll back upstream states (e.g., releasing warehouse inventory), ensuring absolute data consistency without distributed locking.
- **Anti-Corruption Layers (Adapters):** Specialized microservices act as translators, converting modern JSON/AMQP events into the specific legacy protocols (SOAP, TCP/IP) required by older systems, protecting the core domain.

---

## 🛠️ Technology Stack & Justification

The ecosystem is fully containerized and orchestrated via Docker, ensuring seamless parity between development and production environments.

| Component | Technology | Design Justification |
| :--- | :--- | :--- |
| **Message Broker** | `RabbitMQ` | Chosen for robust routing capabilities (Topic Exchanges) and reliable message delivery, forming the backbone of the Event-Driven Architecture. |
| **Core Services** | `Python`, `FastAPI` | FastAPI provides high-performance asynchronous I/O, perfect for handling thousands of concurrent requests without blocking. |
| **Persistence Layer** | `PostgreSQL`, `asyncpg` | Relational integrity with isolated, domain-specific databases ensuring bounded context integrity. `asyncpg` maximizes non-blocking throughput. |
| **Legacy Integration** | `aio-pika`, Custom Adapters | Anti-corruption layers (Adapters) translating AMQP events to SOAP (CMS), TCP/IP (WMS), and REST (ROS) protocols natively. |
| **Real-Time Updates** | `WebSockets` | Consumes broker events and streams real-time updates directly to connected clients, eliminating the need for aggressive, resource-heavy API polling. |
| **Frontend UI** | `HTML5`, `Vanilla JS`, `CSS3` | A lightweight, dependency-free role-based web portal (Client/Driver) that visualizes the complex backend orchestration in real-time. |
| **Infrastructure** | `Docker`, `Docker Compose` | Provides a deterministic, "one-click" deployment model that encapsulates the complex multi-service topology. |

---

## 💻 Full-Stack Capabilities & Role-Based Workflows

Unlike standard backend-only prototypes, SwiftTrack includes a fully functional, event-reactive **Web UI** demonstrating end-to-end integration:

* **Client Portal:** Clients can submit orders, view aggregated statistics, and watch their order progress through the distributed network in real-time via WebSocket pushed events (from "Created" to "Route Assigned").
* **Driver Dashboard:** A separate role-based view for delivery drivers. Drivers receive live alerts when routes are assigned, can look up manifests, and trigger final states (e.g., uploading Proof of Delivery or marking an order as Failed).

---

## ⚙️ Architecture & Event Choreography

The system utilizes event choreography to process high-volume logistics requests asynchronously. An order never blocks a user waiting for a response; instead, it triggers a chain of events:

```text
[Client] POST /orders
    │
    ▼
order-service ──(Saves to DB)──> publishes: order.created
                                      │
    ┌─────────────────────────────────┼─────────────────────────────────┐
    ▼                                 ▼                                 ▼
cms-adapter                      wms-adapter                      notification-service
 ─(SOAP)─> Legacy CMS             ─(TCP)──> Warehouse              ─(WebSocket)─> Client (Order Received)
    │                                 │
publishes:                        publishes:
cms.confirmed                     wms.registered
                                      │
                                      ▼
                                 ros-adapter
                                  ─(REST)─> Route Engine
                                      │
                                  publishes:
                                  ros.route_assigned
                                      │
                                      ▼
                             notification-service ─(WebSocket)─> Client (Driver Assigned)
```

### Fault Tolerance & Sagas
If the `cms-adapter` receives a failure from the Legacy CMS (e.g. customer account suspended), it publishes an `order.compensate` event. The `wms-adapter` listens for this and automatically issues a rollback command to the warehouse to release the reserved items, resolving the distributed transaction gracefully.

---

## 🚀 Getting Started

Want to see SwiftTrack in action? Setting up the entire distributed ecosystem takes just one command. Please refer to the execution guide to spin up the cluster and test the Web UI, API, and failure scenarios.

👉 **[View the Testing & Execution Guide (TESTING_GUIDE.md)](TESTING_GUIDE.md)**

---

*Built to demonstrate industry-standard software architecture and distributed integration patterns.*
