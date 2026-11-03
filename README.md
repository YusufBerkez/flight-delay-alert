# Flight Delay Monitor

A simple Python tool to track flight delays, gate changes, and cancellations. It fetches schedule updates (via AirLabs API or local demo data) and delivers push notifications using ntfy.

## Features
* Compares current flight status against saved records to detect news.
* Triggers alerts based on custom delay thresholds.
* Supports zero-network demo mode for testing.

## Getting Started

### Prerequisites
* Python 3.8+
* `requests` library

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd <repository-name>
