"""WS4GEEServerManager URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from Model import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('test/', views.test),
    path('generate',views.generate_dynamic_service),
    path('ows/<str:dataset>/<str:type>',views.get_coverage_service),
    path('ws4gee/wps',views.get_process_service),
    path('status/<str:uuid>',views.check_coverage_status),
    path('ws4gee/wps/RetrieveResults',views.check_execute_status),
    path('ws4gee/WCSService',views.get_WCS_List),
    path('ws4gee/WPSService',views.get_WPS_List),
    path('ws4gee/xml/list',views.get_xmlTemplate_list),
    path('ws4gee/xml/context',views.get_xmlTemplate),
    path('ws4gee/boundaryFiles/',views.get_boundary_files),
    path('ws4gee/files/',views.get_files),
    path('ws4gee/register',views.register_wps),
    path('ws4gee/test',views.test_service),
    path('ws4gee/setGroupName',views.set_group_name),
    path('ws4gee/generateCoverageRequest',views.generate_coverage_request),
    path('ws4gee/tutorial',views.get_file),
    path('ws4gee/experimentalData',views.get_zip_file)
]
