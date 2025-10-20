# High-Performance Cryptocurrency Matching Engine

This project delivers a **Proof-of-Concept (POC)** for a **low-latency, high-throughput cryptocurrency exchange core**, designed around principles of **strict Price-Time Priority** and **architectural decoupling**.  
It ensures market fairness while integrating essential financial features, including a **Maker-Taker Fee Model** and **State Persistence**.

---



## 1.  Core Architectural Design

The engine utilizes a **Decoupled Asynchronous Architecture** (`asyncio`) to ensure **determinism** and **high throughput**.

| **Component** | **Role** | **Technical Rationale** |
|----------------|----------|--------------------------|
| **Matching Core** | `matching_engine_loop()` |  **Guaranteed Fairness:** Single-threaded loop eliminates race conditions and ensures strict FIFO (First-In-First-Out) order processing. |
| **I/O Layer** | Network Handling (WebSockets) |  **Asynchronous Concurrency:** Handles thousands of clients and broadcasts in real time without blocking the matching logic. |
| **ENGINE_QUEUE** | Communication Buffer |  **Backpressure Control:** Prevents flooding the single-threaded core with excessive external orders. |
| **Data Structures** | In-Memory State (`dict` + `collections.deque`) |  **O(1)** time complexity for queue operations, ensuring Price-Time Priority. |

---

## 2.  Compliance and Algorithm (REG NMS)

The core logic enforces **strict market rules** inspired by **Regulated Exchange Principles (REG NMS)**.

###  Matching Waterfall Algorithm

The `OrderBook.process_order()` function implements the *Matching Waterfall*:
- **Price Priority:** Iterates through sorted price keys (Best Price first).  
- **Time Priority:** Consumes orders from the front of each `PriceLevel`’s `deque` (FIFO).  
- **Internal Order Protection:** Prevents trade-throughs using:
  ```python
  if incoming_order.price < price:
      break
##  Supported Order Types

| **Type** | **Function** | **Time-in-Force** |
|-----------|---------------|------------------|
| **LIMIT** | Rests on the book until executed or cancelled. | GTC (Good-Till-Cancelled) |
| **MARKET** | Executes immediately against best available liquidity. | IOC |
| **IOC** | Executes immediately (partial fill allowed), cancels remainder. | Immediate-or-Cancel |
| **FOK** | Executes immediately and fully, or cancels entirely. | Fill-or-Kill |

## 📂 Project Structure

crypto_matching_engine/
├── .venv/ # Python Virtual Environment (Dependencies)
├── order_types.py # Defines Order, PriceLevel, Fee Constants
├── order_book.py # Core Matching Algorithm, Persistence Logic
├── engine_server.py # Main Async Server, Architecture, API Handlers
├── client_test.py # Simulation Script for Testing and Benchmarking
└── README.md # Documentation

## ⚙️ Setup and Installation
- A. Environment Setup (PowerShell on Windows)
# Navigate to project folder
cd crypto_matching_engine

# Create virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1


## Your terminal prompt should now show (.venv) at the start.

- B. Install Dependencies
(.venv) pip install websockets

### 🧩 A. Environment Setup (PowerShell on Windows)


# Navigate to project folder
cd crypto_matching_engine

# Create virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

## 🌐 API Endpoints

All APIs use the **WebSocket protocol** (`ws://`) for low-latency, real-time communication.

| **Endpoint** | **Port** | **I/O Direction** | **Content** |
|---------------|-----------|-------------------|-------------|
| **Order Submission (Taker)** | `8000` | Client → Server | Accepts Market, Limit, IOC, and FOK orders. |
| **Market Data Feed** | `8001` | Server → Client | Real-time **L2_UPDATE** (BBO and top 10 price levels). |
| **Trade Execution Feed** | `8002` | Server → Client | Real-time **TRADE_REPORT** (includes price, quantity, fees, and latency). |

## ⚙️ Performance Snapshot

| **Metric** | **Result** |
|-------------|------------|
| **Core Latency** | ~21 μs |
| **Architecture** | Single-threaded, Async I/O |
| **Fairness Model** | Strict FIFO + Price-Time Priority |
| **Recovery** | Full Order Book Persistence |
| **Fees** | Maker **0.10%**, Taker **0.20%** |

## 🧩 Tech Stack

| **Category** | **Tools / Technologies** |
|---------------|---------------------------|
| **Language** | Python 3.11+ |
| **Concurrency** | asyncio, websockets |
| **Data Structures** | dict, collections.deque |
| **Persistence** | pickle |
| **Performance** | time.perf_counter_ns() |
| **Architecture** | Event-driven, Decoupled, Non-blocking |
| **Compliance** | REG NMS-inspired Price-Time Priority Matching |

