from django.urls import path

from budo_app import happy_cleaning_command_views as views


urlpatterns = [
    path(
        "events/create/",
        views.event_create,
        name="happy-cleaning-event-create-api",
    ),
    path(
        "events/<int:event_id>/delete/",
        views.event_delete,
        name="happy-cleaning-event-delete-api",
    ),
    path(
        "events/<int:event_id>/stations/create/",
        views.station_create,
        name="happy-cleaning-station-create-api",
    ),
    path(
        "events/<int:event_id>/stations/reorder/",
        views.station_reorder,
        name="happy-cleaning-station-reorder-api",
    ),
    path(
        "events/<int:event_id>/stations/copy/",
        views.station_copy,
        name="happy-cleaning-station-copy-api",
    ),
    path(
        "events/<int:event_id>/stations/<int:station_id>/update/",
        views.station_update,
        name="happy-cleaning-station-update-api",
    ),
    path(
        "events/<int:event_id>/stations/<int:station_id>/delete/",
        views.station_delete,
        name="happy-cleaning-station-delete-api",
    ),
    path(
        "events/<int:event_id>/stations/<int:station_id>/todos/create/",
        views.todo_create,
        name="happy-cleaning-todo-create-api",
    ),
    path(
        "events/<int:event_id>/stations/<int:station_id>/todos/reorder/",
        views.todo_reorder,
        name="happy-cleaning-todo-reorder-api",
    ),
    path(
        "events/<int:event_id>/stations/<int:station_id>/todos/<int:todo_id>/update/",
        views.todo_update,
        name="happy-cleaning-todo-update-api",
    ),
    path(
        "events/<int:event_id>/stations/<int:station_id>/todos/<int:todo_id>/delete/",
        views.todo_delete,
        name="happy-cleaning-todo-delete-api",
    ),
]
