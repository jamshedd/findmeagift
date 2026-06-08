using System.Text.Json;

namespace eShop.Catalog.API;

public static class AgentApi
{
    private static List<CatalogItemWithAttributes>? _catalogIndex;
    private static readonly object _lock = new();

    public static IEndpointRouteBuilder MapAgentApi(this IEndpointRouteBuilder app)
    {
        var api = app.MapGroup("api/agent");

        api.MapPost("/search-gifts", SearchGifts)
            .WithName("AgentSearchGifts")
            .WithSummary("Search gifts by attributes for the agent")
            .AllowAnonymous();

        api.MapPost("/item-details", GetItemDetails)
            .WithName("AgentGetItemDetails")
            .WithSummary("Get item details for the agent")
            .AllowAnonymous();

        return app;
    }

    private static List<CatalogItemWithAttributes> GetCatalogIndex(IWebHostEnvironment env)
    {
        if (_catalogIndex is not null)
            return _catalogIndex;

        lock (_lock)
        {
            if (_catalogIndex is not null)
                return _catalogIndex;

            var path = Path.Combine(env.ContentRootPath, "Setup", "catalog.json");
            var json = File.ReadAllText(path);
            _catalogIndex = JsonSerializer.Deserialize<List<CatalogItemWithAttributes>>(json,
                new JsonSerializerOptions { PropertyNameCaseInsensitive = true }) ?? [];
            return _catalogIndex;
        }
    }

    private static IResult SearchGifts(AgentSearchRequest request, IWebHostEnvironment env, ILogger<Program> logger)
    {
        logger.LogInformation("Agent SearchGifts called: occasion={Occasion}, relationship={Relationship}, budget={Budget}, age={Age}, tone={Tone}, style={Style}",
            request.Occasion, request.RelationshipType, request.BudgetTier, request.AgeRange, request.Tone, request.AestheticStyle);

        var catalog = GetCatalogIndex(env);
        var results = catalog.AsEnumerable();

        if (!string.IsNullOrEmpty(request.Occasion))
            results = results.Where(i => MatchesAttribute(i, "occasion", request.Occasion));

        if (!string.IsNullOrEmpty(request.RelationshipType))
            results = results.Where(i => MatchesAttribute(i, "relationship_type", request.RelationshipType));

        if (!string.IsNullOrEmpty(request.BudgetTier))
            results = results.Where(i => MatchesAttribute(i, "budget_tier", request.BudgetTier));

        if (!string.IsNullOrEmpty(request.AgeRange))
            results = results.Where(i => MatchesAttribute(i, "age_range", request.AgeRange));

        if (!string.IsNullOrEmpty(request.Tone))
            results = results.Where(i => MatchesAttribute(i, "tone", request.Tone));

        if (!string.IsNullOrEmpty(request.AestheticStyle))
            results = results.Where(i => MatchesAttribute(i, "aesthetic_style", request.AestheticStyle));

        if (!string.IsNullOrEmpty(request.GenderPreference))
            results = results.Where(i => MatchesAttribute(i, "gender_preference", request.GenderPreference));

        if (!string.IsNullOrEmpty(request.Interests))
            results = results.Where(i => MatchesAnyAttribute(i, "interests", request.Interests.Split(',', ' ').Select(s => s.Trim()).Where(s => s.Length > 0).ToList()));

        var matched = results.Take(10).Select(i => new
        {
            item_id = i.Id,
            name = i.Name,
            description = i.Description,
            price = i.Price,
            category = i.Type
        }).ToList();

        logger.LogInformation("Agent SearchGifts returning {Count} results", matched.Count);
        return Results.Ok(new { 
            items = matched, 
            total_matches = matched.Count,
            note = "IMPORTANT: When calling add_to_cart or get_item_details, use the exact item_id number from these results. Never invent an ID."
        });
    }

    private static IResult GetItemDetails(AgentItemRequest request, IWebHostEnvironment env, ILogger<Program> logger)
    {
        logger.LogInformation("Agent GetItemDetails called: itemId={ItemId}", request.ItemId);
        var catalog = GetCatalogIndex(env);
        var item = catalog.FirstOrDefault(i => i.Id == request.ItemId);

        if (item is null)
            return Results.NotFound(new { error = "Item not found" });

        return Results.Ok(new
        {
            item.Id,
            item.Name,
            item.Description,
            item.Price,
            Category = item.Type,
            item.Attributes
        });
    }

    private static bool MatchesAttribute(CatalogItemWithAttributes item, string key, string value)
    {
        if (item.Attributes is null || !item.Attributes.TryGetValue(key, out var values))
            return false;
        return values.Any(v => v.Equals(value, StringComparison.OrdinalIgnoreCase));
    }

    private static bool MatchesAnyAttribute(CatalogItemWithAttributes item, string key, List<string> searchValues)
    {
        if (item.Attributes is null || !item.Attributes.TryGetValue(key, out var values))
            return false;
        return searchValues.Any(sv => values.Any(v => v.Equals(sv, StringComparison.OrdinalIgnoreCase)));
    }
}

public class AgentSearchRequest
{
    public string? Occasion { get; set; }
    public string? RelationshipType { get; set; }
    public string? BudgetTier { get; set; }
    public string? AgeRange { get; set; }
    public string? Interests { get; set; }
    public string? Tone { get; set; }
    public string? AestheticStyle { get; set; }
    public string? GenderPreference { get; set; }
}

public class AgentItemRequest
{
    public int ItemId { get; set; }
}

public class CatalogItemWithAttributes
{
    public int Id { get; set; }
    public string? Type { get; set; }
    public string? Brand { get; set; }
    public string? Name { get; set; }
    public string? Description { get; set; }
    public decimal Price { get; set; }
    public Dictionary<string, List<string>>? Attributes { get; set; }
}
