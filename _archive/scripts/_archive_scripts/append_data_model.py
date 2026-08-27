def append_data_model():
    with open('app/templates/components/data_model.html', 'r', encoding='utf-8') as f:
        content = f.read()

    new_content = content + """
    <div class="mt-8 space-y-8">
        <!-- Module 4: Audience User Journey -->
        {% include 'components/mod_audience_journey.html' %}
        
        <!-- Module 5: Account & Persona Matrix -->
        {% include 'components/mod_persona_matrix.html' %}
    </div>
"""

    with open('app/templates/components/data_model.html', 'w', encoding='utf-8') as f:
        f.write(new_content)
        
    print('Appended Module 4 and 5 to data_model.html')

append_data_model()
