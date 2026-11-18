from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # POST language=<code>: the language switch at the top of every page.
    path("i18n/", include("django.conf.urls.i18n")),
    path("", include("src.urls")),
]
