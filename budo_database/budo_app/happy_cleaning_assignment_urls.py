from django.urls import path

from budo_app import happy_cleaning_assignment_views as views


urlpatterns = [
    path(
        "children/<int:child_id>/number/",
        views.child_number,
        name="happy-cleaning-child-number-api",
    ),
    path(
        "events/<int:event_id>/assignments/assign/",
        views.assignment_assign,
        name="happy-cleaning-assignment-assign-api",
    ),
    path(
        "events/<int:event_id>/assignments/<int:child_id>/move/",
        views.assignment_move,
        name="happy-cleaning-assignment-move-api",
    ),
    path(
        "events/<int:event_id>/assignments/<int:child_id>/remove/",
        views.assignment_remove,
        name="happy-cleaning-assignment-remove-api",
    ),
]
