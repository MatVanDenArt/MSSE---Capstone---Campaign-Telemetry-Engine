def update_matrix():
    with open('app/templates/components/mod_persona_matrix.html', 'r', encoding='utf-8') as f:
        content = f.read()

    content = content.replace("/api/dashboard/audience-data${campaignId", "/api/dashboard/audience-data-scoped${campaignId")

    with open('app/templates/components/mod_persona_matrix.html', 'w', encoding='utf-8') as f:
        f.write(content)

update_matrix()
