from django.contrib import admin

from . import models

model_list = ['Company', 'Language']
for model in model_list:
    if hasattr(models, model):
        admin.site.register(getattr(models, model))


class DocumentAdmin(admin.ModelAdmin):

    list_display = ('service_name', 'name')

    def service_name(self, model):
        return model.service_id.name
    service_name.short_description = 'service'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related()


class DocumentsLanguagesAdmin(admin.ModelAdmin):

    list_display = ('service_name', 'document_name', 'language_name')

    def document_name(self, model):
        return model.document_id.name
    document_name.short_description = 'document'

    def language_name(self, model):
        return model.language_id.name
    language_name.short_description = 'language'

    def service_name(self, model):
        return model.document_id.service_id.name
    service_name.short_description = 'service'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related()


class ServiceAdmin(admin.ModelAdmin):

    list_display = ('company_name', 'name')

    def company_name(self, model):
        return model.company_id.name
    company_name.short_description = 'company'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related()


class SnapshotAdmin(admin.ModelAdmin):

    list_display = ('service_name', 'document_name', 'language_name',
        'date_iso', 'time_iso')

    def date_iso(self, model):
        return model.date.isoformat()
    date_iso.short_description = 'date'

    def document_name(self, model):
        return model.documents_languages_id.document_id.name
    document_name.short_description = 'document'

    def language_name(self, model):
        return model.documents_languages_id.language_id.name
    language_name.short_description = 'language'

    def service_name(self, model):
        return model.documents_languages_id.document_id.service_id.name
    service_name.short_description = 'service'

    def time_iso(self, model):
        return model.time.isoformat()
    time_iso.short_description = 'time'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related()


admin.site.register(models.Document, DocumentAdmin)
admin.site.register(models.DocumentsLanguages, DocumentsLanguagesAdmin)
admin.site.register(models.Service, ServiceAdmin)
admin.site.register(models.Snapshot, SnapshotAdmin)

