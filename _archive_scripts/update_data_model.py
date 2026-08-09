def update_data_model():
    with open('app/templates/components/data_model.html', 'r', encoding='utf-8') as f:
        content = f.read()

    content = content.replace("{% include 'components/mod_audience_journey.html' %}", "{% include 'components/mod_network_graph.html' %}")

    with open('app/templates/components/data_model.html', 'w', encoding='utf-8') as f:
        f.write(content)

update_data_model()
