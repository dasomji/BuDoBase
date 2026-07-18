from django.urls import path

from budo_app import happy_cleaning_todo_views as views


urlpatterns = [
    path(
        "events/<int:event_id>/stations/<int:station_id>/todos/add/",
        views.todo_add,
        name="happy-cleaning-todo-add-api",
    ),
    path(
        "events/<int:event_id>/stations/<int:station_id>/todos/<int:todo_id>/check/",
        views.todo_check,
        name="happy-cleaning-todo-check-api",
    ),
    path(
        "events/<int:event_id>/stations/<int:station_id>/todos/<int:todo_id>/reopen/",
        views.todo_reopen,
        name="happy-cleaning-todo-reopen-api",
    ),
]
