from django import forms
from django.contrib import admin
from django.core.exceptions import FieldDoesNotExist
from django.core.files.base import ContentFile
from django.db import transaction
from django.template.defaultfilters import filesizeformat
from django.utils.html import format_html

from .first_aid_contract import FIRST_AID_MAX_PHOTOS
from .first_aid_photos import process_first_aid_photos
from .kid_edit_writes import ChildWriteScopeError, versioned_child_write
from .models import (
    Auslagerorte,
    AuslagerorteImage,
    AuslagerorteNotizen,
    Document,
    ErsteHilfeEintrag,
    ErsteHilfeFoto,
    Kinder,
    Meal,
    Notizen,
    NotizFoto,
    Profil,
    SchwerpunktWahl,
    Schwerpunkte,
    Schwerpunktzeit,
    SpezialFamilien,
    Turnus,
)


class KinderAdminForm(forms.ModelForm):
    schwerpunkt_w1 = forms.ModelChoiceField(
        queryset=Schwerpunkte.objects.filter(schwerpunktzeit__woche='w1'),
        required=False,
    )
    schwerpunkt_w2 = forms.ModelChoiceField(
        queryset=Schwerpunkte.objects.filter(schwerpunktzeit__woche='w2'),
        required=False,
    )

    class Meta:
        model = Kinder
        fields = '__all__'
        exclude = ['edit_version', 'schwerpunkte']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_turnus_id = self.instance.turnus_id
        selected_turnus_id = self._original_turnus_id
        if selected_turnus_id is None and self.is_bound:
            selected_turnus_id = self.data.get(
                self.add_prefix('turnus')
            )
        if selected_turnus_id is None:
            selected_turnus_id = self.initial.get('turnus')
        if hasattr(selected_turnus_id, 'pk'):
            selected_turnus_id = selected_turnus_id.pk
        try:
            selected_turnus_id = int(selected_turnus_id)
        except (TypeError, ValueError):
            selected_turnus_id = None
        if selected_turnus_id is not None and selected_turnus_id <= 0:
            selected_turnus_id = None

        for week, field_name in (
            ('w1', 'schwerpunkt_w1'),
            ('w2', 'schwerpunkt_w2'),
        ):
            queryset = Schwerpunkte.objects.none()
            if selected_turnus_id:
                queryset = Schwerpunkte.objects.filter(
                    schwerpunktzeit__turnus_id=selected_turnus_id,
                    schwerpunktzeit__woche=week,
                )
            self.fields[field_name].queryset = queryset

        if self.instance.pk:
            self.fields['schwerpunkt_w1'].initial = self.instance.schwerpunkte.filter(
                schwerpunktzeit__turnus_id=self._original_turnus_id,
                schwerpunktzeit__woche='w1',
            ).first()
            self.fields['schwerpunkt_w2'].initial = self.instance.schwerpunkte.filter(
                schwerpunktzeit__turnus_id=self._original_turnus_id,
                schwerpunktzeit__woche='w2',
            ).first()

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            if instance.pk:
                self.save_versioned()
            else:
                instance.save()
                self.save_new_swp_links()
        return instance

    def save_new_swp_links(self):
        selected_ids = [
            focus.id
            for focus in (
                self.cleaned_data.get('schwerpunkt_w1'),
                self.cleaned_data.get('schwerpunkt_w2'),
            )
            if focus is not None
        ]
        if selected_ids:
            self.instance.schwerpunkte.add(*selected_ids)

    def save_versioned(self):
        submitted = self.instance
        period_ids_by_week = dict(
            Schwerpunktzeit.objects.filter(
                turnus_id=self._original_turnus_id,
                woche__in=('w1', 'w2'),
            ).values_list('woche', 'id')
        )
        model_update_fields = []
        for field_name in self.changed_data:
            try:
                field = Kinder._meta.get_field(field_name)
            except FieldDoesNotExist:
                continue
            if (
                field.many_to_many
                or field.primary_key
                or field.name in {'edit_version', 'turnus'}
            ):
                continue
            model_update_fields.append(field.name)

        with versioned_child_write(
            turnus_id=self._original_turnus_id,
            child_id=submitted.pk,
        ) as write:
            for field_name in model_update_fields:
                field = Kinder._meta.get_field(field_name)
                setattr(
                    write.child,
                    field.attname,
                    getattr(submitted, field.attname),
                )
            if model_update_fields:
                write.save_child(update_fields=model_update_fields)

            for week, form_field in (
                ('w1', 'schwerpunkt_w1'),
                ('w2', 'schwerpunkt_w2'),
            ):
                if form_field not in self.changed_data:
                    continue
                selected = self.cleaned_data.get(form_field)
                write.set_swp_links(
                    period_id=period_ids_by_week[week],
                    focus_ids=() if selected is None else (selected.id,),
                )

        submitted.edit_version = write.child.edit_version
        submitted.turnus_id = self._original_turnus_id


class KinderAdmin(admin.ModelAdmin):
    list_display = ("__str__", "turnus")
    form = KinderAdminForm
    list_select_related = ('turnus', 'spezial_familien')
    readonly_fields = ('edit_version',)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('turnus', 'spezial_familien')

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if obj is not None:
            readonly_fields.append('turnus')
        return tuple(readonly_fields)

    def save_model(self, request, obj, form, change):
        if change:
            form.save_versioned()
        else:
            super().save_model(request, obj, form, change)
            form.save_new_swp_links()


class KinderInline(admin.TabularInline):
    model = Kinder.schwerpunkte.through
    extra = 1
    verbose_name = "Kind"
    verbose_name_plural = "Kinder"

    def kid_name(self, obj):
        kid = obj.kinder
        return f"{kid.kid_vorname} {kid.kid_nachname}"


class NotizenAdmin(admin.ModelAdmin):
    list_display = ("notiz", "kids_name", "added_by", "date_added")
    readonly_fields = ('date_added',)


class AuslagerorteNotizenAdmin(admin.ModelAdmin):
    list_display = ("notiz", "auslagerort", "added_by", "date_added")
    readonly_fields = ('date_added',)


class AuslagerorteImageAdmin(admin.ModelAdmin):
    list_display = ("image", "auslagerort", "file_size")

    def file_size(self, obj):
        if obj.image and hasattr(obj.image, 'size'):
            return filesizeformat(obj.image.size)
        return "N/A"
    file_size.short_description = "File Size"


class AuslagerorteNotizenInline(admin.TabularInline):
    model = AuslagerorteNotizen
    extra = 1


class AuslagerorteImageInline(admin.TabularInline):
    model = AuslagerorteImage
    extra = 1
    readonly_fields = ['image_preview']

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 150px; max-width: 150px;" />', obj.image.url)
        return "No Image"
    image_preview.short_description = 'Image Preview'


class AuslagerorteAdmin(admin.ModelAdmin):
    list_display = ("__str__", "get_notizen_count", "get_images_count")
    inlines = [AuslagerorteNotizenInline, AuslagerorteImageInline]

    def get_notizen_count(self, obj):
        return obj.auslagernotizen.count()
    get_notizen_count.short_description = 'Notizen'

    def get_images_count(self, obj):
        return obj.images.count()
    get_images_count.short_description = 'Bilder'


class TurnusAdmin(admin.ModelAdmin):
    list_display = ("__str__", "turnus_beginn", "get_turnus_ende", "id")
    readonly_fields = ('dateTimeOfUpload', "get_turnus_ende")
# Register your models here.


class ProfilAdmin(admin.ModelAdmin):
    list_display = (
        "__str__", 'rolle', 'get_food', 'budo_family', 'allergien', 'turnus',
    )


class MealInline(admin.TabularInline):
    model = Meal
    extra = 0  # Number of extra forms to display


class SwpInline(admin.TabularInline):
    model = Schwerpunkte
    extra = 0


class SchwerpunkteAdmin(admin.ModelAdmin):
    list_display = ("__str__", "ort", "display_betreuende",
                    "schwerpunktzeit", "get_turnus", "auslagern", "get_kids_count")
    inlines = [KinderInline, MealInline]
    list_select_related = ('ort', 'schwerpunktzeit')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('ort', 'schwerpunktzeit').prefetch_related('betreuende', 'swp_kinder')

    def save_formset(self, request, form, formset, change):
        if formset.model is not Kinder.schwerpunkte.through:
            return super().save_formset(request, form, formset, change)

        focus = formset.instance
        through = Kinder.schwerpunkte.through
        existing_child_ids = set(
            through.objects.filter(
                schwerpunkte_id=focus.id,
            ).values_list('kinder_id', flat=True)
        )
        desired_child_ids = {
            inline_form.cleaned_data['kinder'].id
            for inline_form in formset.forms
            if (
                inline_form.cleaned_data
                and not inline_form.cleaned_data.get('DELETE')
                and inline_form.cleaned_data.get('kinder') is not None
            )
        }
        operations = {
            child_id: False
            for child_id in existing_child_ids - desired_child_ids
        }
        operations.update({
            child_id: True
            for child_id in desired_child_ids - existing_child_ids
        })
        period_id = focus.schwerpunktzeit_id
        turnus_id = (
            focus.schwerpunktzeit.turnus_id
            if focus.schwerpunktzeit_id is not None
            else None
        )
        child_turnus_ids = dict(
            Kinder.objects.filter(
                id__in=operations,
            ).values_list('id', 'turnus_id')
        )
        invalid_additions = [
            child_id
            for child_id, present in operations.items()
            if (
                present
                and turnus_id is not None
                and child_turnus_ids.get(child_id) != turnus_id
            )
        ]
        if invalid_additions:
            raise ChildWriteScopeError(
                "The child is unavailable in the active Turnus."
            )

        with transaction.atomic():
            for child_id in sorted(operations):
                present = operations[child_id]
                if (
                    turnus_id is None
                    or child_turnus_ids.get(child_id) != turnus_id
                ):
                    link = through.objects.filter(
                        kinder_id=child_id,
                        schwerpunkte_id=focus.id,
                    )
                    if present:
                        through.objects.get_or_create(
                            kinder_id=child_id,
                            schwerpunkte_id=focus.id,
                        )
                    else:
                        link.delete()
                    continue

                with versioned_child_write(
                    turnus_id=turnus_id,
                    child_id=child_id,
                ) as write:
                    write.set_swp_link(
                        period_id=period_id,
                        focus_id=focus.id,
                        present=present,
                    )

    def display_betreuende(self, obj):
        return ", ".join([str(betreuer) for betreuer in obj.betreuende.all()])
    display_betreuende.short_description = 'Betreuende'

    def get_turnus(self, obj):
        return obj.get_turnus()
    get_turnus.short_description = 'Turnus'

    def get_kids_count(self, obj):
        return obj.swp_kinder.count()
    get_kids_count.short_description = 'Kinder'


class KinderInlineForSpezialFamilien(admin.TabularInline):
    model = Kinder
    extra = 0
    verbose_name = "Kind"
    verbose_name_plural = "Kinder"
    readonly_fields = ('kid_vorname', 'kid_nachname')
    fields = ('kid_vorname', 'kid_nachname')

    def kid_name(self, obj):
        return f"{obj.kid_vorname} {obj.kid_nachname}"


class SpezialFamilienAdmin(admin.ModelAdmin):
    list_display = ("__str__", "turnus", "get_kids_count")
    inlines = [KinderInlineForSpezialFamilien]

    def get_kids_count(self, obj):
        return obj.kinder.count()
    get_kids_count.short_description = 'Kinder'


class SchwerpunktzeitAdmin(admin.ModelAdmin):
    list_display = ("__str__", "display_swps")

    def display_swps(self, obj):
        return ", ".join([str(swp) for swp in obj.swp.all()])
    display_swps.short_description = 'Schwerpunkte'


class AttachmentAdminForm(forms.ModelForm):
    """Turn an admin upload into the same optimized WebP used by the frontend."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["datei"].required = False

    def _get_validation_exclusions(self):
        exclusions = set(super()._get_validation_exclusions())
        exclusions.update(("datei", "position", "width", "height", "checksum"))
        return exclusions

    def clean(self):
        cleaned = super().clean()
        upload = self.files.get(self.add_prefix("datei"))
        self.processed_photo = (
            process_first_aid_photos([upload])[0] if upload is not None else None
        )
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        processed = self.processed_photo
        if processed is not None:
            storage = instance._meta.get_field("datei").storage
            old_name = instance.datei.name if instance.pk and instance.datei else None
            saved_name = storage.save(processed.storage_key, ContentFile(processed.content))
            instance.datei = saved_name
            instance.width = processed.width
            instance.height = processed.height
            instance.checksum = processed.checksum
            if old_name and old_name != saved_name:
                transaction.on_commit(lambda: storage.delete(old_name))
        if commit:
            instance.save()
        return instance


class NotizFotoAdminForm(AttachmentAdminForm):
    class Meta:
        model = NotizFoto
        fields = ("position", "datei")
        widgets = {"datei": forms.FileInput()}


class ErsteHilfeFotoAdminForm(AttachmentAdminForm):
    class Meta:
        model = ErsteHilfeFoto
        fields = ("position", "datei")
        widgets = {"datei": forms.FileInput()}


class AttachmentInline(admin.TabularInline):
    fields = ("position", "datei", "width", "height")
    readonly_fields = ("width", "height")
    extra = 1
    max_num = FIRST_AID_MAX_PHOTOS
    validate_max = True

    def has_view_permission(self, request, obj=None):
        return request.user.is_staff

    def has_add_permission(self, request, obj=None):
        return request.user.is_staff

    def has_change_permission(self, request, obj=None):
        return request.user.is_staff

    def has_delete_permission(self, request, obj=None):
        return request.user.is_staff


class NotizFotoInline(AttachmentInline):
    model = NotizFoto
    form = NotizFotoAdminForm


class ErsteHilfeFotoInline(AttachmentInline):
    model = ErsteHilfeFoto
    form = ErsteHilfeFotoAdminForm


class TurnusEntryAdmin(admin.ModelAdmin):
    readonly_fields = ("date_added", "added_by")
    ordering = ("-date_added", "-id")

    def has_module_permission(self, request):
        return request.user.is_staff and getattr(
            getattr(request.user, "profil", None), "turnus_id", None
        ) is not None

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        turnus_id = getattr(getattr(request.user, "profil", None), "turnus_id", None)
        return queryset.filter(kinder__turnus_id=turnus_id) if turnus_id else queryset.none()

    def has_add_permission(self, request):
        return False

    def has_view_permission(self, request, obj=None):
        return request.user.is_staff and self._same_turnus(request, obj)

    def has_change_permission(self, request, obj=None):
        return request.user.is_staff and self._same_turnus(request, obj)

    def has_delete_permission(self, request, obj=None):
        return request.user.is_staff and self._same_turnus(request, obj)

    @staticmethod
    def _same_turnus(request, obj):
        if obj is None:
            return True
        return obj.kinder.turnus_id == getattr(
            getattr(request.user, "profil", None), "turnus_id", None
        )


class NotizenAdmin(TurnusEntryAdmin):
    list_display = ("notiz", "kids_name", "added_by", "date_added")
    inlines = (NotizFotoInline,)


class FirstAidEntryAdmin(TurnusEntryAdmin):
    list_display = ("beschreibung", "kinder", "added_by", "date_added")
    list_select_related = ("kinder", "added_by")
    inlines = (ErsteHilfeFotoInline,)


admin.site.register(Kinder, KinderAdmin)
admin.site.register(Turnus, TurnusAdmin)
admin.site.register(Auslagerorte, AuslagerorteAdmin)
admin.site.register(AuslagerorteImage, AuslagerorteImageAdmin)
admin.site.register(AuslagerorteNotizen, AuslagerorteNotizenAdmin)
admin.site.register(Notizen, NotizenAdmin)
admin.site.register(Document)
admin.site.register(Profil, ProfilAdmin)
admin.site.register(Schwerpunkte, SchwerpunkteAdmin)
admin.site.register(Meal)
admin.site.register(Schwerpunktzeit, SchwerpunktzeitAdmin)
admin.site.register(SchwerpunktWahl)
admin.site.register(SpezialFamilien, SpezialFamilienAdmin)
admin.site.register(ErsteHilfeEintrag, FirstAidEntryAdmin)
