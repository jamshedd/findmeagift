// FindMeAGift - Napster OmniAgent SDK integration
window.giftAgent = {
    instance: null,
    retryCount: 0,
    maxRetries: 10,

    init: async function () {
        // Wait for document.body to be available
        var body = document.body || document.documentElement;
        if (!body) {
            if (window.giftAgent.retryCount < window.giftAgent.maxRetries) {
                window.giftAgent.retryCount++;
                setTimeout(function() { window.giftAgent.init(); }, 1000);
            }
            return;
        }

        // Wait for SDK to be loaded
        if (typeof napsterCompanionApiSDK === 'undefined') {
            if (window.giftAgent.retryCount < window.giftAgent.maxRetries) {
                window.giftAgent.retryCount++;
                console.log('Gift agent: waiting for SDK, attempt ' + window.giftAgent.retryCount);
                setTimeout(function() { window.giftAgent.init(); }, 1000);
            }
            return;
        }

        try {
            console.log('Gift agent: starting initialization...');
            const response = await fetch('/api/agent/token', { method: 'POST' });
            if (!response.ok) {
                const errorBody = await response.text();
                console.warn('Gift agent: token endpoint returned', response.status, errorBody);
                let container = document.getElementById('gift-agent-container');
                if (container) {
                    const attempt = (window.giftAgent.tokenRetry || 0) + 1;
                    container.innerHTML = '<div style="background:#1a1a2e;color:#fff;padding:16px;border-radius:12px 0 0 0;font-family:sans-serif;font-size:13px;height:100%;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;">'
                        + '<div style="font-size:32px;margin-bottom:8px;">🎁</div>'
                        + '<div style="font-weight:600;margin-bottom:4px;">Ivy is getting ready...</div>'
                        + '<div style="opacity:0.7;">Waiting for connection (attempt ' + attempt + '/12)</div>'
                        + '</div>';
                }
                if (!window.giftAgent.tokenRetry || window.giftAgent.tokenRetry < 12) {
                    window.giftAgent.tokenRetry = (window.giftAgent.tokenRetry || 0) + 1;
                    setTimeout(function() { window.giftAgent.init(); }, 10000);
                }
                return;
            }
            window.giftAgent.tokenRetry = 0;

            const data = await response.json();
            const token = data.token;

            if (!token) {
                console.warn('Gift agent: no token in response');
                return;
            }

            let container = document.getElementById('gift-agent-container');
            if (!container) {
                container = document.createElement('div');
                container.id = 'gift-agent-container';
                container.style.cssText = 'width:100%;height:100%;';
                document.body.appendChild(container);
            }

            console.log('Gift agent: calling SDK init...');
            const result = await napsterCompanionApiSDK.init(token, {
                mountContainer: container,
                className: 'omniagent-sdk-root',
                avatarStyle: { view: 'rectangle' },
                position: 'bottom-right',
                onData: window.giftAgent.handleData
            });

            window.giftAgent.instance = result;
            console.log('Gift agent: initialized successfully');
        } catch (error) {
            console.error('Gift agent: initialization failed', error);
        }
    },

    handleData: function (event) {
        if (event.event === 'message_received' && event.data?.message?.type === 'session' && event.data?.message?.action === 'created') {
            setTimeout(function() {
                if (window.giftAgent.instance) {
                    window.giftAgent.instance.sendCommand({
                        type: 'send_text',
                        data: { text: 'Hi!' }
                    });
                }
            }, 1500);
        }

        // Handle tool calls - check both event formats
        if (event.type === 'function_implicitly_called' && event.data) {
            const callId = event.data.call_id;
            const fnName = event.data.name;
            const args = event.data.arguments || {};
            console.log('Gift agent: tool call (implicit)', fnName, callId, args);

            if (fnName === 'search_gifts') {
                window.giftAgent.searchGifts(callId, args);
            } else if (fnName === 'get_item_details') {
                window.giftAgent.getItemDetails(callId, args);
            } else if (fnName === 'add_to_cart') {
                window.giftAgent.addToCart(callId, args);
            }
            return;
        }

        // Fallback: SDK wrapper format
        if (event.event === 'message_received' && event.data?.message) {
            const msg = event.data.message;
            if (msg.type === 'function_call' && msg.action === 'completed') {
                const callId = msg.call_id;
                const args = typeof msg.content === 'string' ? JSON.parse(msg.content) : (msg.content || {});
                let fnName = msg.name;
                if (!fnName) {
                    if (args.interests || args.relationship_type || args.budget_tier) fnName = 'search_gifts';
                    else if (args.item_name || args.quantity || args.product_id) fnName = 'add_to_cart';
                    else if (args.item_id) fnName = 'get_item_details';
                }
                console.log('Gift agent: tool call (sdk)', fnName, callId, args);

                if (fnName === 'search_gifts') window.giftAgent.searchGifts(callId, args);
                else if (fnName === 'get_item_details') window.giftAgent.getItemDetails(callId, args);
                else if (fnName === 'add_to_cart') window.giftAgent.addToCart(callId, args);
            }
        }
    },

    searchGifts: async function (callId, args) {
        try {
            const response = await fetch('/api/agent/search-gifts', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(args)
            });
            const data = await response.json();
            console.log('Gift agent: search results', data);
            window.giftAgent.sendToolOutput(callId, data);

            // Navigate parent to filtered catalog showing Ivy's picks
            if (data.items && data.items.length > 0) {
                const ids = data.items.map(function(i) { return i.item_id || i.id; }).filter(function(id) { return id != null; }).join(',');
                if (ids) {
                    // Use postMessage to tell parent to navigate without full reload
                    window.parent.postMessage({ type: 'agent-navigate', url: '/?items=' + ids }, '*');
                }
            }
        } catch (error) {
            console.error('Gift agent: search failed', error);
            window.giftAgent.sendToolOutput(callId, { error: 'Search failed' });
        }
    },

    getItemDetails: async function (callId, args) {
        try {
            const response = await fetch('/api/agent/item-details', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(args)
            });
            const data = await response.json();
            console.log('Gift agent: item details', data);
            window.giftAgent.sendToolOutput(callId, data);
        } catch (error) {
            console.error('Gift agent: item details failed', error);
            window.giftAgent.sendToolOutput(callId, { error: 'Failed to get item details' });
        }
    },

    sendToolOutput: function (callId, output) {
        if (window.giftAgent.instance) {
            window.giftAgent.instance.sendCommand({
                type: 'send_function_output',
                data: {
                    call_id: callId,
                    output: output,
                    delay: false
                }
            });
            console.log('Gift agent: sent tool output for', callId);
        }
    },

    addToCart: async function (callId, args) {
        try {
            const itemId = args.item_id;
            console.log('Gift agent: adding to cart', itemId, args.item_name);
            const response = await fetch('/api/agent/add-to-cart', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ itemId: itemId })
            });
            const data = await response.json();
            console.log('Gift agent: add to cart result', data);
            window.giftAgent.sendToolOutput(callId, data);
        } catch (error) {
            console.error('Gift agent: add to cart failed', error);
            window.giftAgent.sendToolOutput(callId, { success: false, message: 'Failed to add item to cart' });
        }
    },

    destroy: function () {
        if (window.giftAgent.instance) {
            window.giftAgent.instance.destroy();
            window.giftAgent.instance = null;
        }
    }
};
