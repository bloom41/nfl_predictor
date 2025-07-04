from django.urls import path
from . import views

app_name = 'nfl_api'

urlpatterns = [
    # Home page
    path('', views.home, name='home'),
    
    # API endpoints
    path('api/status', views.api_status, name='api_status'),
    path('api/rankings', views.get_rankings, name='get_rankings'),
    path('api/player', views.analyze_player, name='analyze_player'),
    path('api/features', views.get_features, name='get_features'),
    path('api/injury', views.injury_analysis, name='injury_analysis'),
    path('api/boom-bust', views.boom_bust_analysis, name='boom_bust_analysis'),
    path('api/batch-rankings', views.batch_rankings, name='batch_rankings'),
]