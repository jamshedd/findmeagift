using eShop.WebApp.Components;
using eShop.WebApp.Apis;

var builder = WebApplication.CreateBuilder(args);

builder.AddServiceDefaults();

builder.Services.AddRazorComponents().AddInteractiveServerComponents();

builder.AddApplicationServices();

var app = builder.Build();

app.MapDefaultEndpoints();

// Configure the HTTP request pipeline.
if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error");
    // The default HSTS value is 30 days. You may want to change this for production scenarios, see https://aka.ms/aspnetcore-hsts.
    app.UseHsts();
}

app.UseAntiforgery();

app.UseHttpsRedirection();

app.UseStaticFiles();

app.MapRazorComponents<App>().AddInteractiveServerRenderMode();

app.MapForwarder("/product-images/{id}", "https+http://catalog-api", "/api/catalog/items/{id}/pic");
app.MapForwarder("/api/agent/search-gifts", "https+http://catalog-api", "/api/agent/search-gifts");
app.MapForwarder("/api/agent/item-details", "https+http://catalog-api", "/api/agent/item-details");

app.MapAgentTokenApi();

app.Run();
