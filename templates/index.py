{% extends "_base.html" %}

{% block title %}index{% endblock %}

{% block content %}
    {% for forum in fora %}
        <h2>{{forum.name}}</h2>
    {% endfor %}
{% endblock %}
