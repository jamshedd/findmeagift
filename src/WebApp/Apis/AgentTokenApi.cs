using System.Net.Http.Headers;
using System.Text.Json;
using eShop.WebApp.Services;
using eShop.WebAppComponents.Services;

namespace eShop.WebApp.Apis;

public static class AgentTokenApi
{
    public static IEndpointRouteBuilder MapAgentTokenApi(this IEndpointRouteBuilder app)
    {
        app.MapPost("/api/agent/token", CreateAgentSession)
            .WithName("CreateAgentSession")
            .AllowAnonymous();

        app.MapPost("/api/agent/add-to-cart", AddToCart)
            .WithName("AgentAddToCart")
            .AllowAnonymous();

        return app;
    }

    private static async Task<IResult> AddToCart(
        AddToCartRequest request,
        BasketService basketService,
        CatalogService catalogService)
    {
        try
        {
            var item = await catalogService.GetCatalogItem(request.ItemId);
            if (item is null)
                return Results.Ok(new { success = false, message = "Item not found in catalog" });

            // Get current basket, add item, update
            var basket = (await basketService.GetBasketAsync()).ToList();
            var existing = basket.FirstOrDefault(b => b.ProductId == request.ItemId);
            if (existing is not null)
            {
                basket.Remove(existing);
                basket.Add(existing with { Quantity = existing.Quantity + 1 });
            }
            else
            {
                basket.Add(new BasketQuantity(request.ItemId, 1));
            }
            await basketService.UpdateBasketAsync(basket);
            return Results.Ok(new { success = true, message = $"Added \"{item.Name}\" to cart" });
        }
        catch (Exception e)
        {
            return Results.Ok(new { success = false, message = $"Could not add to cart: {e.Message}" });
        }
    }

    private static async Task<IResult> CreateAgentSession(IConfiguration configuration, IHttpClientFactory httpClientFactory)
    {
        var apiKey = configuration["Napster:ApiKey"];
        var agentId = configuration["Napster:AgentId"];

        if (string.IsNullOrEmpty(apiKey) || string.IsNullOrEmpty(agentId))
        {
            return Results.Problem("Napster agent not configured", statusCode: 503);
        }

        var client = httpClientFactory.CreateClient();
        var request = new HttpRequestMessage(HttpMethod.Post,
            $"https://companion-api.napster.com/public/agents/{agentId}/connections");
        request.Headers.Add("X-Api-Key", apiKey);
        request.Content = new StringContent(
            JsonSerializer.Serialize(new { channelType = "webrtc" }),
            new MediaTypeHeaderValue("application/json"));

        var response = await client.SendAsync(request);

        if (!response.IsSuccessStatusCode)
        {
            var error = await response.Content.ReadAsStringAsync();
            return Results.Problem($"Failed to create agent session: {error}", statusCode: (int)response.StatusCode);
        }

        var body = await response.Content.ReadAsStringAsync();
        return Results.Content(body, "application/json");
    }
}

public record AddToCartRequest(int ItemId);
