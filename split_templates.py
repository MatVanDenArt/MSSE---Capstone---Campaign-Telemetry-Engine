import re

def split_templates():
    with open('app/templates/components/mod_audience_journey.html', 'r', encoding='utf-8') as f:
        content = f.read()

    # For mod_user_cards.html
    user_cards = content
    # Remove toggle switch completely
    user_cards = re.sub(r'<!-- Toggle Switch -->.*?</div>\s*</div>', '</div>', user_cards, flags=re.DOTALL)
    # Remove Network Graph section
    user_cards = re.sub(r'<!-- Network Graph \(Dark Mode\) -->.*?</div>\s*<!-- JS for D3 -->', '<!-- JS for D3 -->', user_cards, flags=re.DOTALL)
    # Change fetch URL
    user_cards = user_cards.replace("fetch('/api/dashboard/audience-data')", "const campaignId = '{{ campaign_id }}';\n        fetch(`/api/dashboard/audience-data-scoped${campaignId ? '?campaign_id='+campaignId : ''}`)")
    # Remove x-show constraints
    user_cards = user_cards.replace("x-show=\"viewMode === 'cards' || viewMode === 'network'\"", "")
    user_cards = user_cards.replace("x-show=\"viewMode === 'cards'\"", "")
    
    with open('app/templates/components/mod_user_cards.html', 'w', encoding='utf-8') as f:
        f.write(user_cards)
        
    # For mod_network_graph.html
    network = content
    # Remove toggle switch
    network = re.sub(r'<!-- Toggle Switch -->.*?</div>\s*</div>', '</div>', network, flags=re.DOTALL)
    # Remove cards view
    network = re.sub(r'<!-- Cards View \(Light Mode style like the reference image\) -->.*?<!-- Network Graph \(Dark Mode\) -->', '<!-- Network Graph (Dark Mode) -->', network, flags=re.DOTALL)
    # Remove User Detail Modal Overlay
    network = re.sub(r'<!-- User Detail Modal Overlay -->.*?<!-- Network Graph \(Dark Mode\) -->', '<!-- Network Graph (Dark Mode) -->', network, flags=re.DOTALL)
    # Set viewMode to network and add initNetwork to fetch success
    network = network.replace("viewMode: 'cards',", "viewMode: 'network',")
    network = network.replace("this.loading = false;\n            })", "this.loading = false;\n                this.initNetwork();\n            })")
    # Remove x-show constraints
    network = network.replace("x-show=\"viewMode === 'cards' || viewMode === 'network'\"", "")
    network = network.replace("x-show=\"viewMode === 'network'\"", "")
    
    with open('app/templates/components/mod_network_graph.html', 'w', encoding='utf-8') as f:
        f.write(network)

split_templates()
