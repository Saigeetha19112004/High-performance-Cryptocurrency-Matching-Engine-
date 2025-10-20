# ⚡ High-Performance Cryptocurrency Matching Engine

This project delivers a **Proof-of-Concept (POC)** for a **low-latency, high-throughput cryptocurrency exchange core**, designed around principles of **strict Price-Time Priority** and **architectural decoupling**.  
It ensures market fairness while integrating essential financial features, including a **Maker-Taker Fee Model** and **State Persistence**.

---

## 📑 Table of Contents

1. [Core Architectural Design](#1-core-architectural-design)  
2. [Compliance and Algorithm (REG NMS)](#2-compliance-and-algorithm-reg-nms)  
3. [Bonus Feature Highlights](#3-bonus-feature-highlights)  
4. [Project Structure](#4-project-structure)  
5. [Setup and Installation](#5-setup-and-installation)  
6. [Running the Engine and Client](#6-running-the-engine-and-client)  
7. [API Endpoints](#7-api-endpoints)

---

## 1. 🧠 Core Architectural Design

The engine utilizes a **Decoupled Asynchronous Architecture** (`asyncio`) to ensure **determinism** and **high throughput**.

| **Component** | **Role** | **Technical Rationale** |
|----------------|----------|--------------------------|
| **Matching Core** | `matching_engine_loop()` | ✅ **Guaranteed Fairness:** Single-threaded loop eliminates race conditions and ensures strict FIFO (First-In-First-Out) order processing. |
| **I/O Layer** | Network Handling (WebSockets) | ⚙️ **Asynchronous Concurrency:** Handles thousands of clients and broadcasts in real time without blocking the matching logic. |
| **ENGINE_QUEUE** | Communication Buffer | 🧩 **Backpressure Control:** Prevents flooding the single-threaded core with excessive external orders. |
| **Data Structures** | In-Memory State (`dict` + `collections.deque`) | ⚡ **O(1)** time complexity for queue operations, ensuring Price-Time Priority. |

---

## 2. 🧾 Compliance and Algorithm (REG NMS)

The core logic enforces **strict market rules** inspired by **Regulated Exchange Principles (REG NMS)**.

### 🧮 Matching Waterfall Algorithm

The `OrderBook.process_order()` function implements the *Matching Waterfall*:
- **Price Priority:** Iterates through sorted price keys (Best Price first).  
- **Time Priority:** Consumes orders from the front of each `PriceLevel`’s `deque` (FIFO).  
- **Internal Order Protection:** Prevents trade-throughs using:
  ```python
  if incoming_order.price < price:
      break
