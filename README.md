# FindMeAGift

A curated online gift marketplace with over 5,100 handcrafted and specialty items, powered by an AI voice concierge that helps customers find the perfect gift through natural conversation.

**[Live Demo](https://webapp.thankfulflower-3ed369d7.eastus2.azurecontainerapps.io/)** | **[Watch the Demo Video](https://fmagvideos00868.blob.core.windows.net/videos/FindMeAGift-demo.mov)**

## Overview

FindMeAGift reimagines online gift shopping by pairing a rich catalog spanning dozens of categories - artisan kitchenware, handmade jewelry, outdoor gear, wellness products, home decor, and more - with **Ivy**, a real-time AI voice and video concierge powered by the [Napster OmniAgent](https://docs.napster.com) platform.

Customers tell Ivy who they are shopping for, their budget, and the occasion. Ivy searches the catalog in real time, walks them through her picks, and can add items to their cart - all through voice, hands-free.

For a detailed writeup, see [docs/findmeagift-writeup.md](docs/findmeagift-writeup.md).

## Tech Stack

- **ASP.NET** with **Blazor** (server-side rendering + enhanced navigation)
- **PostgreSQL** with pgvector for catalog and vector search
- **.NET Aspire** for local orchestration
- **Azure Container Apps** for cloud deployment
- **Napster OmniAgent** (WebRTC) for the AI voice/video agent
- **Redis** for basket state
- **RabbitMQ** for event-driven messaging

## Getting Started

### Prerequisites

- [.NET 9 SDK](https://dot.net/download)
- [Docker Desktop](https://docs.docker.com/engine/install/) (for PostgreSQL, RabbitMQ)
- Redis running on localhost:6379 (or Docker)

### Running locally

```sh
cd src
dotnet run --project eShop.AppHost/eShop.AppHost.csproj
```

The Aspire dashboard URL will appear in the console output. The webapp runs at `http://localhost:5045`.

### Configuration

Set the following user secrets for the WebApp project:

```sh
cd src/WebApp
dotnet user-secrets set "Napster:ApiKey" "<your-napster-api-key>"
dotnet user-secrets set "Napster:AgentId" "<your-napster-agent-id>"
dotnet user-secrets set "ConnectionStrings:redis" "localhost:6379"
```

### Deploy to Azure

```sh
azd auth login
azd up
```

This deploys all services to Azure Container Apps. Set the Napster secrets as environment variables on the `webapp` container app after deployment.

## Architecture

The application uses a microservices architecture orchestrated by .NET Aspire:

- **WebApp** - Blazor storefront with embedded Napster agent (iframe-based for persistence across navigation)
- **Catalog.API** - Product catalog with agent search endpoints
- **Basket.API** - Shopping cart (gRPC, Redis-backed)
- **Identity.API** - Authentication
- **Ordering.API** - Order processing
- **OrderProcessor / PaymentProcessor** - Background event-driven services

## The Agent (Ivy)

Ivy connects via WebRTC directly in the browser. She has access to three tools:

- **search_gifts** - Search the catalog by interests, occasion, budget
- **get_item_details** - Retrieve full details for a specific item
- **add_to_cart** - Add an item to the customer's basket

The agent persists across page navigation using an isolated iframe architecture, ensuring conversations are never interrupted as customers browse.
