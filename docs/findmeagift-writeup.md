# FindMeAGift

Gift shopping is personal. Finding the right thing for the right person takes thought, time, and often more scrolling than anyone enjoys. FindMeAGift is a curated online marketplace built around that challenge - a storefront stocked with over 5,100 handcrafted and specialty items spanning dozens of categories, from artisan kitchenware and handmade jewelry to outdoor gear, wellness products, and unique home decor. The breadth of the catalog is a strength, but it also means customers can feel overwhelmed before they even begin.

That is where Ivy comes in.

## Meet Ivy

Ivy is a real-time AI voice concierge powered by the Napster OmniAgent platform. She lives inside the shopping experience as a persistent video-and-voice companion - visible on every page, ready the moment a customer needs help. She is not a chatbot buried in a corner or a support form hidden behind three clicks. Ivy appears on screen, speaks naturally, listens to what the customer says, and responds in conversation.

When a shopper lands on FindMeAGift, they can simply tell Ivy who they are shopping for and what the occasion is. Ivy asks a few follow-up questions - budget, interests, any preferences to avoid - and then searches the catalog in real time. Results appear on the page while Ivy walks the customer through her picks, explaining why each item fits. If something catches their eye, Ivy can add it to the cart. The entire interaction happens through voice, hands-free, with no typing required.

## Why It Matters

Traditional e-commerce search relies on keywords and filters. Customers have to already know what they want. Gift shopping is the opposite - people rarely know exactly what they are looking for. They know who the gift is for and roughly how much they want to spend. Ivy bridges that gap by turning vague intent into curated results through natural conversation.

Because Ivy is integrated directly with the storefront's catalog and cart, she is not just answering questions. She is an active participant in the shopping flow. She searches inventory, retrieves item details, and manages the basket on behalf of the customer - all through implicit tool calls executed in real time during the conversation.

## How It Works

Ivy connects to the storefront via WebRTC, establishing a live audio and video session directly in the browser. The Napster OmniAgent platform handles speech recognition, natural language understanding, and response generation. Custom tools registered with the agent (search_gifts, get_item_details, add_to_cart) give Ivy the ability to interact with the store's backend APIs as the conversation unfolds.

The storefront itself is built on ASP.NET with Blazor, runs on Azure Container Apps orchestrated by .NET Aspire, and uses a PostgreSQL-backed catalog with vector search capabilities. The agent persists across page navigation through an isolated iframe architecture, ensuring the conversation is never interrupted as customers browse.

## The Experience

FindMeAGift reimagines online gift shopping as a conversation rather than a search query. Customers talk to Ivy the way they would talk to a knowledgeable friend who happens to know every item in the store. She is warm, helpful, and always available - a personal shopper that scales to every visitor without a wait.

## Demo

In this short demo, a customer asks Ivy to find gifts for their sister who likes baking, with a budget under $200. Ivy asks a couple of follow-up questions, searches the catalog using the `search_gifts` tool call, and presents a shortlist of matching items. The customer picks one and asks Ivy to add it to the cart. Ivy uses the `add_to_cart` tool call to place the item in the basket - all through natural voice conversation, no typing or clicking required.

[Watch the demo video](https://fmagvideos00868.blob.core.windows.net/videos/FindMeAGift-demo.mov)
